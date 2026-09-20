"""The deliverable's own smoke: true at emission, true after implement.

Model-free and finished in seconds. This is not the evaluation -- the
harness is -- it is the floor beneath it: the contract exists, the fence
holds, and the exam refuses to be empty. A project failing any of these
is broken in a way no implementation round fixes, so it gates every push
whether or not a model is reachable.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_the_code_is_lint_clean():
    """The deliverable is code a client's staff engineer reads. An
    implementation round once left a zip() without strict= behind a green
    exam; lint is part of the floor, wherever ruff is installed."""
    pytest.importorskip("ruff")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated", "--select", "F,E,W,I,B,UP",
         "--line-length", "100", str(ROOT)],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout[-1500:]


def test_forbidden_input_has_a_name():
    from app.contract import RefusedInput

    assert issubclass(RefusedInput, ValueError)


def test_the_fence_holds_at_import():
    # boundary.py asserts placement at import when this build carries a
    # boundary; a build without sensitive data has no boundary module,
    # and that absence is correct rather than a failure.
    if (ROOT / "app" / "boundary.py").exists():
        import app.boundary  # noqa: F401


def test_the_exam_refuses_to_be_empty():
    # An empty exam graded green is how CI stays green on a system nobody
    # measured. Empty must equal red, permanently.
    with tempfile.NamedTemporaryFile(suffix=".jsonl") as empty:
        result = subprocess.run(
            [sys.executable, "evals/harness.py", "--cases", empty.name],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
    assert result.returncode != 0, "the harness accepted an empty exam"
    assert "no cases" in result.stderr or "nothing was measured" in result.stderr, (
        "red for the wrong reason: " + result.stderr[-300:])

