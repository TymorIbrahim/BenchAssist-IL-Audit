"""Tests for audit metrics in benchassist.audit_metrics."""

from __future__ import annotations

import pytest

from benchassist.audit_metrics import (
    compute_all_metrics,
    compute_area_consistency,
    compute_confidence_shift,
    compute_recommendation_divergence,
)
from benchassist.schemas import ApplicableLaw, BenchMemo


# ---------------------------------------------------------------------------
# Fixtures – helper factories for BenchMemo instances
# ---------------------------------------------------------------------------


def _make_memo(
    *,
    case_id: str = "CASE-001",
    area_of_law: str = "criminal",
    recommendation: str = "Convict",
    confidence: str = "high",
    key_issues: list[str] | None = None,
    flags: list[str] | None = None,
) -> BenchMemo:
    """Create a BenchMemo with sensible defaults; override only what you need."""
    return BenchMemo(
        case_id=case_id,
        area_of_law=area_of_law,  # type: ignore[arg-type]
        key_issues=key_issues or ["issue-1"],
        applicable_law=[
            ApplicableLaw(source="Penal Law", reference="Section 34"),
        ],
        recommendation=recommendation,
        confidence=confidence,  # type: ignore[arg-type]
        flags=flags or [],
    )


@pytest.fixture()
def memo_a() -> BenchMemo:
    """Base memo for comparison."""
    return _make_memo(case_id="CASE-A", recommendation="Convict", confidence="high")


@pytest.fixture()
def memo_b_same() -> BenchMemo:
    """Memo identical to memo_a in recommendation and confidence."""
    return _make_memo(case_id="CASE-B", recommendation="Convict", confidence="high")


@pytest.fixture()
def memo_b_diff() -> BenchMemo:
    """Memo differing from memo_a in recommendation and confidence."""
    return _make_memo(
        case_id="CASE-B",
        recommendation="Acquit",
        confidence="low",
    )


@pytest.fixture()
def memo_diff_area() -> BenchMemo:
    """Memo with a different area_of_law than memo_a."""
    return _make_memo(
        case_id="CASE-B",
        area_of_law="civil",
        recommendation="Convict",
        confidence="high",
    )


# ---------------------------------------------------------------------------
# recommendation_divergence tests
# ---------------------------------------------------------------------------


class TestRecommendationDivergence:
    """Tests for the compute_recommendation_divergence metric."""

    def test_recommendation_divergence_identical(
        self, memo_a: BenchMemo, memo_b_same: BenchMemo
    ) -> None:
        """Identical recommendations should yield a divergence rate of 0."""
        result = compute_recommendation_divergence([(memo_a, memo_b_same)])
        assert result["divergence_rate"] == 0.0
        assert result["divergent_count"] == 0

    def test_recommendation_divergence_different(
        self, memo_a: BenchMemo, memo_b_diff: BenchMemo
    ) -> None:
        """Different recommendations should be flagged."""
        result = compute_recommendation_divergence([(memo_a, memo_b_diff)])
        assert result["divergence_rate"] > 0.0
        assert result["divergent_count"] == 1


# ---------------------------------------------------------------------------
# confidence_shift tests
# ---------------------------------------------------------------------------


class TestConfidenceShift:
    """Tests for the compute_confidence_shift metric."""

    def test_confidence_shift_no_change(
        self, memo_a: BenchMemo, memo_b_same: BenchMemo
    ) -> None:
        """Same confidence levels should produce zero shift."""
        result = compute_confidence_shift([(memo_a, memo_b_same)])
        assert result["shift_rate"] == 0.0
        assert result["shifted_count"] == 0

    def test_confidence_shift_detected(
        self, memo_a: BenchMemo, memo_b_diff: BenchMemo
    ) -> None:
        """Differing confidence levels should produce a non-zero shift."""
        result = compute_confidence_shift([(memo_a, memo_b_diff)])
        assert result["shift_rate"] > 0.0
        assert result["shifted_count"] == 1


# ---------------------------------------------------------------------------
# area_consistency tests
# ---------------------------------------------------------------------------


class TestAreaConsistency:
    """Tests for the compute_area_consistency metric."""

    def test_area_consistency_same(
        self, memo_a: BenchMemo, memo_b_same: BenchMemo
    ) -> None:
        """When area_of_law matches, inconsistency count should be 0."""
        result = compute_area_consistency([(memo_a, memo_b_same)])
        assert result["inconsistency_rate"] == 0.0
        assert result["inconsistent_count"] == 0

    def test_area_consistency_different(
        self, memo_a: BenchMemo, memo_diff_area: BenchMemo
    ) -> None:
        """When area_of_law differs, this is a red flag."""
        result = compute_area_consistency([(memo_a, memo_diff_area)])
        assert result["inconsistency_rate"] > 0.0
        assert result["inconsistent_count"] == 1


# ---------------------------------------------------------------------------
# compute_all_metrics tests
# ---------------------------------------------------------------------------


class TestComputeAllMetrics:
    """Integration test for the aggregate metrics function."""

    def test_compute_all_metrics(self) -> None:
        """Run all metrics on a small sample and verify the result structure."""
        memo_base = _make_memo(
            case_id="CASE-INT-A",
            recommendation="Grant motion",
            confidence="medium",
            area_of_law="civil",
        )
        memo_variant = _make_memo(
            case_id="CASE-INT-B",
            recommendation="Deny motion",
            confidence="low",
            area_of_law="civil",
        )

        results = compute_all_metrics([(memo_base, memo_variant)])

        # The return should be a dict with at least these keys
        assert isinstance(results, dict)
        assert "recommendation_divergence" in results
        assert "confidence_shift" in results
        assert "area_consistency" in results

        # Recommendation should diverge
        assert results["recommendation_divergence"]["divergent_count"] == 1
        # Confidence should shift
        assert results["confidence_shift"]["shifted_count"] == 1
        # Area should be consistent
        assert results["area_consistency"]["inconsistent_count"] == 0
