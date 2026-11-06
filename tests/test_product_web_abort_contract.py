from pathlib import Path

COMPONENT = Path("web/components/recovery-console.tsx")


def test_strict_mode_abort_is_not_reported_as_api_offline():
    source = COMPONENT.read_text(encoding="utf-8")
    assert "if (controller.signal.aborted)" in source
    assert 'err.name === "AbortError"' in source
    assert "setError(err instanceof Error ? err.message" in source
