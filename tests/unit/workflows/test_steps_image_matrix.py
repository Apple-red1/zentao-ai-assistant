from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from zentao_ai.config.models import AppConfig
from zentao_ai.safety.actions import AuthorizationRecord
from zentao_ai.workflows.models import RunContext
from zentao_ai.workflows.steps import (
    ReproductionStep,
    replace_steps,
    replace_steps_with_image,
)
from zentao_ai.zentao.models import StepUpdateResult


PNG = b"\x89PNG\r\n\x1a\n" + b"proof"
STEPS = (
    ReproductionStep("Open the edit form", "The current bug is displayed"),
    ReproductionStep("Select Save", "A confirmation message appears"),
)


class RecordingProvider:
    def __init__(self, result: StepUpdateResult | None = None) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.result = result or StepUpdateResult(
            updated=True, bugId=7, version="v2", status="UPDATED"
        )

    def update_bug_steps(self, *args: object) -> StepUpdateResult:
        self.calls.append(("steps", *args))
        return self.result

    def update_bug_steps_with_image(self, *args: object) -> StepUpdateResult:
        self.calls.append(("image", *args))
        return self.result


class ExplodingProvider(RecordingProvider):
    def update_bug_steps(self, *args: object) -> StepUpdateResult:
        raise KeyboardInterrupt

    def update_bug_steps_with_image(self, *args: object) -> StepUpdateResult:
        raise KeyboardInterrupt


def context(provider: RecordingProvider, **changes: object) -> RunContext:
    config = AppConfig.model_validate(
        {
            "personal": {"scopeNames": ["mine"]},
            "team": {"scopeNames": ["team"], "members": ["alice"]},
            "permissions": {"stepUpdateEnabled": True},
            "repositories": {},
        }
    )
    params = {"steps": [step.__dict__ for step in STEPS]}
    base = RunContext(
        config,
        provider,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        lambda: datetime(2026, 7, 15, 9),
        "owner",
        currentTurnId="turn",
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn",
                source="user",
                action="update_steps",
                bugId="7",
                parameters=params,
            ),
        ),
    )
    return replace(base, **changes)


def authorize_image(ctx: RunContext, image: Path) -> RunContext:
    try:
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
    except OSError:
        digest = "0" * 64
    params = {
        "steps": [step.__dict__ for step in STEPS],
        "imageSha256": digest,
        "filename": image.name,
    }
    return replace(
        ctx,
        authorizedImagePaths=(image,),
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn",
                source="user",
                action="update_steps_with_image",
                bugId="7",
                parameters=params,
            ),
        ),
    )


def test_complete_ordered_steps_are_the_only_provider_fields() -> None:
    provider = RecordingProvider()
    result = replace_steps(context(provider), 7, STEPS)
    assert result.updated
    assert provider.calls == [
        (
            "steps",
            7,
            '[{"action":"Open the edit form","expected":"The current bug is displayed"},'
            '{"action":"Select Save","expected":"A confirmation message appears"}]',
            True,
        )
    ]
    assert not any(
        name in str(provider.calls)
        for name in ("status", "assignee", "priority")
    )


@pytest.mark.parametrize(
    "steps",
    [
        (),
        (ReproductionStep("", "expected result"),),
        (ReproductionStep("x", "expected result"),),
        (ReproductionStep("perform action", ""),),
        "perform action then expect result",
        ({"action": "perform action"},),
        [ReproductionStep("perform action", "expected result")],
    ],
)
def test_blank_short_prose_incomplete_and_unordered_steps_are_rejected(
    steps: object,
) -> None:
    provider = RecordingProvider()
    with pytest.raises((TypeError, ValueError)):
        replace_steps(context(provider), 7, steps)  # type: ignore[arg-type]
    assert provider.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scheduled", True),
        ("team", True),
        ("readonly", True),
        ("dryRun", True),
    ],
)
def test_all_runtime_write_gates_fail_before_provider(field: str, value: bool) -> None:
    provider = RecordingProvider()
    with pytest.raises(PermissionError):
        replace_steps(context(provider, **{field: value}), 7, STEPS)
    assert provider.calls == []


def test_disabled_permission_and_every_inexact_authorization_are_rejected() -> None:
    provider = RecordingProvider()
    base = context(provider)
    disabled = replace(
        base,
        config=base.config.model_copy(
            update={"permissions": base.config.permissions.model_copy(update={"stepUpdateEnabled": False})}
        ),
    )
    record = base.authorizationRecords[0]
    bad_records = (
        record.model_copy(update={"turnId": "old"}),
        record.model_copy(update={"source": "bug"}),
        record.model_copy(update={"action": "update_steps_with_image"}),
        record.model_copy(update={"bugId": "8"}),
        record.model_copy(update={"parameters": {"steps": []}}),
    )
    for ctx in (disabled, *(replace(base, authorizationRecords=(record,)) for record in bad_records)):
        with pytest.raises(PermissionError):
            replace_steps(ctx, 7, STEPS)
    assert provider.calls == []


def test_image_provider_receives_exact_validated_immutable_bytes_and_no_path(
    tmp_path: Path,
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    provider = RecordingProvider()
    ctx = authorize_image(context(provider), image)
    result = replace_steps_with_image(ctx, 7, STEPS, image)
    call = provider.calls[0]
    assert call[3] == PNG and isinstance(call[3], bytes)
    assert call[4:] == ("proof.png", "image/png", True)
    assert str(image) not in repr(call)
    assert str(image) not in repr(ctx.authorizationRecords[0].parameters)
    assert str(image) not in repr(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [("scheduled", True), ("team", True), ("readonly", True), ("dryRun", True)],
)
def test_image_runtime_gates_fail_before_provider(
    tmp_path: Path, field: str, value: bool
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    provider = RecordingProvider()
    ctx = authorize_image(context(provider, **{field: value}), image)
    with pytest.raises(PermissionError):
        replace_steps_with_image(ctx, 7, STEPS, image)
    assert provider.calls == []


def test_image_disabled_permission_and_inexact_authorization_fail_closed(
    tmp_path: Path,
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    provider = RecordingProvider()
    base = authorize_image(context(provider), image)
    disabled = replace(
        base,
        config=base.config.model_copy(
            update={
                "permissions": base.config.permissions.model_copy(
                    update={"stepUpdateEnabled": False}
                )
            }
        ),
    )
    record = base.authorizationRecords[0]
    bad_records = (
        record.model_copy(update={"turnId": "old"}),
        record.model_copy(update={"source": "bug"}),
        record.model_copy(update={"action": "update_steps"}),
        record.model_copy(update={"bugId": "8"}),
        record.model_copy(update={"parameters": {"steps": []}}),
    )
    contexts = (disabled, *(replace(base, authorizationRecords=(r,)) for r in bad_records))
    for ctx in contexts:
        with pytest.raises(PermissionError):
            replace_steps_with_image(ctx, 7, STEPS, image)
    assert provider.calls == []


@pytest.mark.parametrize("kind", ["unauthorized", "nonfile", "type", "magic", "oversize"])
def test_invalid_image_matrix_fails_before_provider(tmp_path: Path, kind: str) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    if kind == "nonfile":
        image.unlink()
        image.mkdir()
    elif kind == "type":
        image = (tmp_path / "proof.gif").resolve()
        image.write_bytes(b"GIF89a")
    elif kind == "magic":
        image.write_bytes(b"not-png")
    elif kind == "oversize":
        with image.open("wb") as stream:
            stream.write(PNG)
            stream.seek(10 * 1024 * 1024)
            stream.write(b"x")
    provider = RecordingProvider()
    ctx = context(provider)
    if kind != "unauthorized":
        ctx = authorize_image(ctx, image)
    with pytest.raises(PermissionError):
        replace_steps_with_image(ctx, 7, STEPS, image)
    assert provider.calls == []


def test_provider_classified_failure_is_returned_and_baseexception_is_not_swallowed() -> None:
    failed = StepUpdateResult(updated=False, bugId=7, status="FAILED")
    assert replace_steps(context(RecordingProvider(failed)), 7, STEPS) == failed
    with pytest.raises(KeyboardInterrupt):
        replace_steps(context(ExplodingProvider()), 7, STEPS)


def test_image_classified_failure_is_returned_and_baseexception_is_not_swallowed(
    tmp_path: Path,
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    failed = StepUpdateResult(updated=False, bugId=7, status="FAILED")
    provider = RecordingProvider(failed)
    assert replace_steps_with_image(
        authorize_image(context(provider), image), 7, STEPS, image
    ) == failed
    exploding = ExplodingProvider()
    with pytest.raises(KeyboardInterrupt):
        replace_steps_with_image(
            authorize_image(context(exploding), image), 7, STEPS, image
        )


def test_file_replaced_after_validation_fails_closed_before_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    provider = RecordingProvider()
    ctx = authorize_image(context(provider), image)
    from zentao_ai.workflows import steps as steps_module

    original = steps_module.validate_user_image

    def validate_then_replace(*args: object, **kwargs: object) -> object:
        result = original(*args, **kwargs)  # type: ignore[arg-type]
        image.write_bytes(PNG + b"changed")
        return result

    monkeypatch.setattr(steps_module, "validate_user_image", validate_then_replace)
    with pytest.raises(PermissionError, match="IMAGE_CHANGED_AFTER_VALIDATION"):
        replace_steps_with_image(ctx, 7, STEPS, image)
    assert provider.calls == []


def test_file_replaced_during_permit_fails_closed_before_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(PNG)
    provider = RecordingProvider()
    ctx = authorize_image(context(provider), image)
    from zentao_ai.workflows import steps as steps_module

    original = steps_module._permit

    def permit_then_replace(*args: object, **kwargs: object) -> None:
        original(*args, **kwargs)  # type: ignore[arg-type]
        image.write_bytes(PNG + b"changed-during-permit")

    monkeypatch.setattr(steps_module, "_permit", permit_then_replace)
    with pytest.raises(PermissionError, match="IMAGE_CHANGED_AFTER_VALIDATION"):
        replace_steps_with_image(ctx, 7, STEPS, image)
    assert provider.calls == []


def test_symlink_image_is_rejected_or_explicitly_skipped(tmp_path: Path) -> None:
    target = (tmp_path / "real.png").resolve()
    target.write_bytes(PNG)
    link = (tmp_path / "link.png").resolve()
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    provider = RecordingProvider()
    with pytest.raises(PermissionError):
        replace_steps_with_image(authorize_image(context(provider), link), 7, STEPS, link)
    assert provider.calls == []


def test_windows_junction_image_is_rejected_or_explicitly_skipped(
    tmp_path: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("junctions are Windows-only")
    real = (tmp_path / "real").resolve()
    real.mkdir()
    (real / "proof.png").write_bytes(PNG)
    junction = (tmp_path / "junction").resolve()
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True,
        check=False,
    )
    if created.returncode:
        pytest.skip("junction creation is unavailable")
    image = junction / "proof.png"
    provider = RecordingProvider()
    with pytest.raises(PermissionError):
        replace_steps_with_image(authorize_image(context(provider), image), 7, STEPS, image)
    assert provider.calls == []
