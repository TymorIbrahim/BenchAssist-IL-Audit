"""Static checks for the Vercel Next.js dashboard scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web_dashboard"


@pytest.fixture
def web_root() -> Path:
    return WEB


def test_package_json_exists(web_root: Path) -> None:
    assert (web_root / "package.json").exists()


def test_app_page_exists(web_root: Path) -> None:
    assert (web_root / "app" / "page.tsx").exists()
    assert (web_root / "app" / "layout.tsx").exists()


def test_core_components_exist(web_root: Path) -> None:
    required = [
        "components/DisclaimerBanner.tsx",
        "components/MetricCard.tsx",
        "components/DataTable.tsx",
        "components/CaseComparison.tsx",
        "components/MarkdownReportViewer.tsx",
        "components/Glossary.tsx",
        "components/FilterPanel.tsx",
        "components/SectionGuide.tsx",
        "components/RunSummary.tsx",
        "components/StatusPill.tsx",
        "components/DownloadButton.tsx",
        "components/ReviewerQuestions.tsx",
        "components/ExecutiveLanding.tsx",
        "components/AudienceGuide.tsx",
        "components/ExploreByConcern.tsx",
        "components/MainFindingsStory.tsx",
        "components/MethodologyContent.tsx",
        "components/PresentationPanel.tsx",
        "components/DataTransparency.tsx",
        "lib/data.ts",
        "lib/types.ts",
        "lib/derive.ts",
        "lib/sectionGuides.ts",
        "lib/metricDefinitions.ts",
        "lib/navigation.ts",
        "lib/navigationGroups.ts",
        "lib/urlState.ts",
        "lib/insights.ts",
        "lib/caseContext.ts",
        "lib/reviewPriority.ts",
        "lib/reviewerPacket.ts",
        "lib/diffSummary.ts",
        "lib/crossPromptComparison.ts",
        "lib/reportCategories.ts",
        "components/GlossaryDrawer.tsx",
        "components/GuidedReviewPanel.tsx",
        "components/InsightCards.tsx",
        "components/RealCaseAuditSection.tsx",
        "components/WhatChangedPanel.tsx",
    ]
    for rel in required:
        assert (web_root / rel).exists(), f"missing {rel}"


def test_no_api_keys_in_dashboard_source(web_root: Path) -> None:
    if not web_root.exists():
        pytest.skip("web_dashboard not created yet")
    patterns = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "sk-proj-", "apiKey:")
    for path in web_root.rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".json"}:
            continue
        if "node_modules" in path.parts or "public/data" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            assert pat not in text, f"{pat} found in {path}"


def test_no_party_power_sections(web_root: Path) -> None:
    if not web_root.exists():
        pytest.skip("web_dashboard not created yet")
    for path in web_root.rglob("*.tsx"):
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "party_power" not in text
        assert "power_asymmetry" not in text


def test_no_standalone_html_report_route(web_root: Path) -> None:
    if not web_root.exists():
        pytest.skip("web_dashboard not created yet")
    html_routes = list(web_root.glob("app/**/report.html/**"))
    assert html_routes == []


def test_url_state_helpers_exist(web_root: Path) -> None:
    text = (web_root / "lib" / "urlState.ts").read_text(encoding="utf-8")
    assert "parseUrlState" in text
    assert "serializeUrlState" in text
    assert "buildShareUrl" in text


def test_insight_generation_handles_missing_data(web_root: Path) -> None:
    text = (web_root / "lib" / "insights.ts").read_text(encoding="utf-8")
    assert "generateKeyTakeaways" in text
    assert "not available" in text.lower() or "Insight cards are not available" in text


def test_key_takeaways_function_exported(web_root: Path) -> None:
    text = (web_root / "lib" / "insights.ts").read_text(encoding="utf-8")
    assert "export function generateKeyTakeaways" in text
    assert "not proof of unlawful discrimination" in text.lower()


def test_issue_tag_filtering(web_root: Path) -> None:
    filters = (web_root / "lib" / "filters.ts").read_text(encoding="utf-8")
    assert "issueTag" in filters
    assert "rowMatchesIssueTag" in filters
    derive = (web_root / "lib" / "caseContext.ts").read_text(encoding="utf-8")
    assert "issueTagsFromRow" in derive


def test_review_priority_reason_generated(web_root: Path) -> None:
    text = (web_root / "lib" / "reviewPriority.ts").read_text(encoding="utf-8")
    assert "reviewPriorityReason" in text


def test_executive_landing_reviewer_path(web_root: Path) -> None:
    text = (web_root / "components" / "ExecutiveLanding.tsx").read_text(encoding="utf-8")
    assert "Open reviewer path" in text
    assert "Not legal advice" in text
    assert "View main findings" in text


def test_explore_by_concern_panel(web_root: Path) -> None:
    text = (web_root / "components" / "ExploreByConcern.tsx").read_text(encoding="utf-8")
    assert "Explore by concern" in text
    assert "View related cases" in text


def test_case_explorer_reviewer_guidance(web_root: Path) -> None:
    text = (web_root / "components" / "CaseComparison.tsx").read_text(encoding="utf-8")
    assert "legally justified" in text.lower()


def test_qa_checklist_exists() -> None:
    assert (ROOT / "WEB_DASHBOARD_QA_CHECKLIST.md").exists()
    text = (ROOT / "WEB_DASHBOARD_QA_CHECKLIST.md").read_text(encoding="utf-8")
    assert "Core experience" in text or "First screen" in text
    assert "Case Review" in text


def test_metric_definitions_cover_main_metrics(web_root: Path) -> None:
    text = (web_root / "lib" / "metricDefinitions.ts").read_text(encoding="utf-8")
    for key in (
        "legal_framing_bias_flag_rate",
        "action_type_flip_rate",
        "remedy_weaker_rate",
        "evidence_burden_higher_rate",
        "credibility_more_skeptical_rate",
        "rights_orientation_weaker_rate",
    ):
        assert key in text


def test_reviewer_packet_generator(web_root: Path) -> None:
    text = (web_root / "lib" / "reviewerPacket.ts").read_text(encoding="utf-8")
    assert "generateReviewerPacket" in text
    assert "Not legal advice" in text


def test_case_context_joining(web_root: Path) -> None:
    text = (web_root / "lib" / "caseContext.ts").read_text(encoding="utf-8")
    assert "getCaseContext" in text
    assert "getCaseBadges" in text


def test_cross_prompt_loader_exists(web_root: Path) -> None:
    data_ts = (web_root / "lib" / "data.ts").read_text(encoding="utf-8")
    assert "cross_prompt_comparisons.json" in data_ts
    assert "crossPromptComparisons" in data_ts


def test_case_explorer_cross_prompt_labels(web_root: Path) -> None:
    text = (web_root / "lib" / "crossPromptComparison.ts").read_text(encoding="utf-8")
    assert "Baseline vs fairness-aware prompt" in text
    case_cmp = (web_root / "components" / "CaseComparison.tsx").read_text(encoding="utf-8")
    assert "crossPromptComparisons" in case_cmp


def test_cross_prompt_empty_state_copy(web_root: Path) -> None:
    text = (web_root / "lib" / "crossPromptComparison.ts").read_text(encoding="utf-8")
    assert "Cross-prompt comparison is not available" in text


def test_url_sync_no_scroll_spy(web_root: Path) -> None:
    hook = (web_root / "lib" / "useDashboardUrlState.ts").read_text(encoding="utf-8")
    assert "activeSection" not in hook
    dashboard = (web_root / "components" / "Dashboard.tsx").read_text(encoding="utf-8")
    assert "activeSection" not in dashboard.split("syncUrl")[1][:400]


def test_flagged_table_actions_column(web_root: Path) -> None:
    text = (web_root / "components" / "Dashboard.tsx").read_text(encoding="utf-8")
    assert 'label: "Actions"' in text
    assert "Inspect in Case Explorer" in text


def test_copy_json_off_by_default(web_root: Path) -> None:
    table = (web_root / "components" / "DataTable.tsx").read_text(encoding="utf-8")
    assert "showCopyJsonAction" in table
    assert "showRowActions = false" in table or "showCopyJsonAction ?? showRowActions" in table
