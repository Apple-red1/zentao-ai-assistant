from pathlib import Path
import os
import subprocess
import pytest
from zentao_ai.safety import CurrentTurnAuthorization, validate_user_image


PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 8


def auth(paths=(), source="user"):
    return CurrentTurnAuthorization(paths=paths, source=source, authorizationTurnId="t", currentTurnId="t")


def test_current_turn_absolute_regular_image_is_valid(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    assert validate_user_image(image, auth((image,))).valid


def test_prior_turn_image_authorization_is_rejected(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    result = validate_user_image(image, CurrentTurnAuthorization(paths=(image,), authorizationTurnId="old", currentTurnId="now"))
    assert "CURRENT_TURN_AUTHORIZATION_REQUIRED" in result.reasons


def test_rejects_relative_unapproved_source_extension_magic_and_size(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    assert not validate_user_image(Path("x.png"), auth((image,))).valid
    assert not validate_user_image(image, auth(source="bug")).valid
    bad = tmp_path / "x.gif"
    bad.write_bytes(b"GIF89a")
    assert not validate_user_image(bad, auth((bad,))).valid
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not png")
    assert not validate_user_image(fake, auth((fake,))).valid
    huge = tmp_path / "huge.png"
    with huge.open("wb") as stream:
        stream.write(PNG)
        stream.seek(10 * 1024 * 1024)
        stream.write(b"x")
    assert not validate_user_image(huge, auth((huge,))).valid


def test_exactly_ten_mib_is_allowed_and_webp_jpeg_magic_checked(tmp_path):
    exact = tmp_path / "exact.jpg"
    exact.write_bytes(b"\xff\xd8\xff" + b"x" * (10 * 1024 * 1024 - 3))
    assert validate_user_image(exact, auth((exact,))).valid
    for name, data in (("bad.jpg", b"bad"), ("bad.webp", b"RIFF1234NOPE")):
        image = tmp_path / name
        image.write_bytes(data)
        assert "IMAGE_MAGIC_MISMATCH" in validate_user_image(image, auth((image,))).reasons


def test_authorization_normalization_collision_fails_closed(tmp_path):
    image = tmp_path / "x.png"
    image.write_bytes(PNG)
    authorization = auth((image, Path(str(image).upper())))
    assert "AUTHORIZATION_PATH_CONFLICT" in validate_user_image(image, authorization).reasons


def test_symlink_component_is_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    image = real / "x.png"
    image.write_bytes(PNG)
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation requires Windows privilege")
    through_link = link / "x.png"
    assert "SYMLINK_OR_REPARSE_COMPONENT" in validate_user_image(through_link, auth((through_link,))).reasons


def test_windows_junction_component_is_rejected(tmp_path):
    if os.name != "nt":
        pytest.skip("junctions are Windows-only")
    real = tmp_path / "real-junction"
    real.mkdir()
    image = real / "x.png"
    image.write_bytes(PNG)
    junction = tmp_path / "junction"
    created = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(real)], capture_output=True)
    if created.returncode != 0:
        pytest.skip("junction creation is unavailable")
    through_junction = junction / "x.png"
    assert "SYMLINK_OR_REPARSE_COMPONENT" in validate_user_image(through_junction, auth((through_junction,))).reasons
