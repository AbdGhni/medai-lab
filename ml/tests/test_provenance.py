import subprocess
from pathlib import Path

from medai_ml.provenance import git_state


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)  # noqa: S603, S607


def test_dirty_ignore_reports_and_artifacts_but_not_code(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.org")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "code.py").write_text("x = 1\n")
    _git(tmp_path, "add", "code.py")
    _git(tmp_path, "commit", "-q", "-m", "init")
    assert git_state(tmp_path)["dirty"] is False

    (tmp_path / "reports" / "run1").mkdir(parents=True)
    (tmp_path / "reports" / "run1" / "report.json").write_text("{}")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "w.pt").write_text("w")
    assert git_state(tmp_path)["dirty"] is False

    (tmp_path / "code.py").write_text("x = 2\n")
    assert git_state(tmp_path)["dirty"] is True
