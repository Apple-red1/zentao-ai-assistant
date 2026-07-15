from pathlib import Path
from zentao_ai.safety import CurrentTurnAuthorization, validate_user_image


PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 8


def test_current_turn_absolute_regular_image_is_valid(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    assert validate_user_image(image, CurrentTurnAuthorization(paths=(image,))).valid


def test_rejects_relative_unapproved_source_extension_magic_and_size(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    assert not validate_user_image(Path("x.png"), CurrentTurnAuthorization(paths=(image,))).valid
    assert not validate_user_image(image, CurrentTurnAuthorization(paths=(), source="bug")).valid
    bad = tmp_path / "x.gif"
    bad.write_bytes(b"GIF89a")
    assert not validate_user_image(bad, CurrentTurnAuthorization(paths=(bad,))).valid
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not png")
    assert not validate_user_image(fake, CurrentTurnAuthorization(paths=(fake,))).valid
    huge = tmp_path / "huge.png"
    with huge.open("wb") as stream:
        stream.write(PNG)
        stream.seek(10 * 1024 * 1024)
        stream.write(b"x")
    assert not validate_user_image(huge, CurrentTurnAuthorization(paths=(huge,))).valid


def test_exactly_ten_mib_is_allowed_and_webp_jpeg_magic_checked(tmp_path):
    exact = tmp_path / "exact.jpg"
    exact.write_bytes(b"\xff\xd8\xff" + b"x" * (10 * 1024 * 1024 - 3))
    assert validate_user_image(exact, CurrentTurnAuthorization(paths=(exact,))).valid
    for name, data in (("bad.jpg", b"bad"), ("bad.webp", b"RIFF1234NOPE")):
        image = tmp_path / name
        image.write_bytes(data)
        assert "IMAGE_MAGIC_MISMATCH" in validate_user_image(image, CurrentTurnAuthorization(paths=(image,))).reasons


def test_authorization_normalization_collision_fails_closed(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    auth = CurrentTurnAuthorization(paths=(image, Path(str(image).upper())))
    assert "AUTHORIZATION_PATH_CONFLICT" in validate_user_image(image, auth).reasons


def test_symlink_component_is_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    image = real / "x.png"
    image.write_bytes(PNG)
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        return
    through_link = link / "x.png"
    assert "SYMLINK_OR_REPARSE_COMPONENT" in validate_user_image(through_link, CurrentTurnAuthorization(paths=(through_link,))).reasons
