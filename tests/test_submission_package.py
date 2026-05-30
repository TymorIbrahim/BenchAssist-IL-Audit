"""Tests for submission package builder."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from benchassist.config import get_settings
from benchassist.pipeline import pipeline_status
from benchassist.submission_package import _should_exclude, build_submission_package, main


@pytest.fixture()
def mini_project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    results = root / "results"
    data = root / "data"
    for sub in ("report", "tables", "outputs", "charts"):
        (results / sub).mkdir(parents=True)
    (data / "processed").mkdir(parents=True)
    (data / "audit").mkdir(parents=True)

    (root / "README.md").write_text("# Test\n", encoding="utf-8")
    (root / "PROJECT_OVERVIEW.md").write_text("# Overview\n", encoding="utf-8")
    (results / "report" / "final_audit_report.md").write_text("# Report\n", encoding="utf-8")
    (results / "tables" / "v2_group_summary_test.csv").write_text("a\n", encoding="utf-8")
    (root / ".env").write_text("GEMINI_API_KEY=secret\n", encoding="utf-8")

    monkeypatch.chdir(root)
    monkeypatch.setenv("RESULTS_DIR", str(results))
    monkeypatch.setenv("DATA_DIR", str(data))
    get_settings.cache_clear()
    return root, results


class TestSubmissionPackageHelpers:
    def test_should_exclude_env(self) -> None:
        assert _should_exclude(Path(".env")) is True
        assert _should_exclude(Path("__pycache__")) is True
        assert _should_exclude(Path("report.md")) is False


class TestSubmissionPackageBuild:
    def test_creates_output_directory(self, mini_project) -> None:
        root, results = mini_project
        out = results / "submission_package"
        result = build_submission_package(
            output_dir=out,
            project_root=root,
            create_zip=False,
        )
        assert result["output_dir"].is_dir()
        assert (out / "docs" / "README.md").exists()

    def test_creates_manifest(self, mini_project) -> None:
        root, results = mini_project
        out = results / "submission_package"
        result = build_submission_package(
            output_dir=out,
            project_root=root,
            create_zip=False,
        )
        manifest = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
        assert "included_files" in manifest
        assert "missing_expected_files" in manifest
        assert manifest["total_file_count"] >= 1
        assert "party-role" in manifest["out_of_scope"][0]

    def test_excludes_env_from_package(self, mini_project) -> None:
        root, results = mini_project
        out = results / "submission_package"
        build_submission_package(output_dir=out, project_root=root, create_zip=True)
        zip_path = results / "submission_package.zip"
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
        assert not any(".env" in n for n in names)

    def test_creates_readme_for_reviewers(self, mini_project) -> None:
        root, results = mini_project
        out = results / "submission_package"
        build_submission_package(output_dir=out, project_root=root, create_zip=False)
        readme = (out / "README_FOR_REVIEWERS.md").read_text(encoding="utf-8")
        assert "not legal advice" in readme.lower()
        assert "streamlit" in readme.lower()

    def test_creates_zip(self, mini_project) -> None:
        root, results = mini_project
        out = results / "submission_package"
        build_submission_package(output_dir=out, project_root=root, create_zip=True)
        assert (results / "submission_package.zip").is_file()

    def test_handles_missing_optional_files(self, mini_project) -> None:
        root, results = mini_project
        out = results / "submission_package"
        result = build_submission_package(
            output_dir=out,
            project_root=root,
            create_zip=False,
        )
        missing = result["manifest"]["missing_expected_files"]
        assert isinstance(missing, list)
        assert len(missing) > 0


class TestPipelineStatusSubmission:
    def test_status_mentions_submission_files(self, mini_project) -> None:
        root, _ = mini_project
        status = pipeline_status(project_root=root)
        assert "SUBMISSION_PACKAGE.md" in status["checks"]
        assert "submission_package/" in status["checks"]


class TestSubmissionPackageMain:
    def test_module_runs_with_minimal_files(self, mini_project, monkeypatch) -> None:
        root, results = mini_project
        monkeypatch.chdir(root)
        assert main(["--auto", "--no-zip"]) == 0
        assert (results / "submission_package" / "MANIFEST.json").exists()


class TestReadmeMentionsSubmission:
    def test_readme_mentions_submission_package_command(self) -> None:
        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(
            encoding="utf-8"
        )
        assert "benchassist.submission_package" in readme
        assert "submission_package.zip" in readme
