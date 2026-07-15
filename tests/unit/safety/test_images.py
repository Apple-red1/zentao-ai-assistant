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
