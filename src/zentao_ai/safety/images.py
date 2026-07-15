from __future__ import annotations
import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAGIC = {".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".webp": (b"RIFF",)}
REPARSE_POINT = 0x400


class CurrentTurnAuthorization(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    paths: tuple[Path, ...] = ()
    source: str = "user"
    authorizationTurnId: str | None = None
    currentTurnId: str | None = None


class ImageValidationResult(BaseModel):
    valid: bool
    reasons: list[str] = Field(default_factory=list)
    path: str


def validate_user_image(path: Path, authorization: CurrentTurnAuthorization) -> ImageValidationResult:
    reasons: list[str] = []
    if not path.is_absolute():
        return ImageValidationResult(valid=False, reasons=["ABSOLUTE_PATH_REQUIRED"], path=str(path))
    if not authorization.authorizationTurnId or authorization.authorizationTurnId != authorization.currentTurnId:
        reasons.append("CURRENT_TURN_AUTHORIZATION_REQUIRED")
    normalized = Path(os.path.normcase(str(path.resolve(strict=False))))
    normalized_values = [Path(os.path.normcase(str(item.resolve(strict=False)))) for item in authorization.paths if item.is_absolute()]
    approved = set(normalized_values)
    if len(normalized_values) != len(approved):
        reasons.append("AUTHORIZATION_PATH_CONFLICT")
    if authorization.source != "user" or normalized not in approved:
        reasons.append("CURRENT_TURN_USER_PATH_REQUIRED")
    current = Path(path.anchor)
    try:
        for part in path.parts[1:]:
            current /= part
            stat = current.lstat()
            if current.is_symlink() or getattr(stat, "st_file_attributes", 0) & REPARSE_POINT:
                reasons.append("SYMLINK_OR_REPARSE_COMPONENT")
                break
    except OSError:
        pass
    suffix = path.suffix.casefold()
    if suffix not in MAGIC:
        reasons.append("UNSUPPORTED_IMAGE_EXTENSION")
    try:
        if path.is_symlink() or not path.is_file():
            reasons.append("REGULAR_FILE_REQUIRED")
        elif path.stat().st_size > MAX_IMAGE_BYTES:
            reasons.append("IMAGE_TOO_LARGE")
        elif suffix in MAGIC:
            with path.open("rb") as stream:
                header = stream.read(12)
            valid_magic = any(header.startswith(prefix) for prefix in MAGIC[suffix])
            if suffix == ".webp":
                valid_magic = header.startswith(b"RIFF") and header[8:12] == b"WEBP"
            if not valid_magic:
                reasons.append("IMAGE_MAGIC_MISMATCH")
    except OSError:
        reasons.append("IMAGE_READ_FAILED")
    return ImageValidationResult(valid=not reasons, reasons=list(dict.fromkeys(reasons)), path=str(normalized))
