from __future__ import annotations
import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAGIC = {".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".webp": (b"RIFF",)}


class CurrentTurnAuthorization(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    paths: tuple[Path, ...] = ()
    source: str = "user"


class ImageValidationResult(BaseModel):
    valid: bool
    reasons: list[str] = Field(default_factory=list)
    path: str


def validate_user_image(path: Path, authorization: CurrentTurnAuthorization) -> ImageValidationResult:
    reasons: list[str] = []
    if not path.is_absolute():
        return ImageValidationResult(valid=False, reasons=["ABSOLUTE_PATH_REQUIRED"], path=str(path))
    normalized = Path(os.path.normcase(str(path.resolve(strict=False))))
    approved = {Path(os.path.normcase(str(item.resolve(strict=False)))) for item in authorization.paths if item.is_absolute()}
    if authorization.source != "user" or normalized not in approved:
        reasons.append("CURRENT_TURN_USER_PATH_REQUIRED")
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
