# BenchAssist-IL Audit — Project Overview

## 1. Project title

**BenchAssist-IL Audit**

## 2. Course concept

**Concept 1: Bias in Language Models** (Responsible AI algorithmic audit)

## 3. System being audited

**BenchAssist-IL** is a toy **judge-facing**, **non-binding** Israeli judicial bench-memo assistant. Given a short case summary (usually in Hebrew), it produces a structured memo with urgency, recommended procedural action, remedy strength, evidence burden, credibility framing, rights orientation, and procedural posture. The memo is intended to support clerks and judges—not to replace them.

## 4. Legal domain

Israeli **housing** disputes: landlord–tenant relations, repairs, deposits, eviction threats, unsafe conditions, and related civil remedies.

## 5. Core audit question

> When only **demographic**, **language-access**, **intersectional**, or **narrative-framing** cues change—but the underlying legal facts are intended to stay equivalent—does the model change **legal framing** (urgency, remedy, evidence burden, credibility, rights emphasis, procedure, or recommended action type)?

## 6. Why this matters

- **Judge-facing AI is high-stakes** even when labeled non-binding; draft language can shape how humans frame disputes.
- **Non-binding** does not mean harmless: recommendations can influence evidence requests, urgency, and sympathy toward a party.
- **Bias in language models** may appear in generated reasoning and structured fields, not only in a single yes/no label.
- **Access to justice** includes language proficiency, legal literacy, and intersectional vulnerability—cues that must not drive unjustified differences in treatment when facts are the same.

## 7. Main components

| Component | Purpose |
|-----------|---------|
| Synthetic **base cases** | Canonical Hebrew housing scenarios with expected urgency/direction |
| **Counterfactual variants** | Demographic, language-access, intersectional, and narrative-framing perturbations |
| **V2 structured schema** | Categorical legal-framing fields for comparable audit metrics |
| **Legal-framing metrics** | Pairwise comparison vs `neutral_he` baseline per case |
| **Counterfactual validity audit** | Heuristic fact-preservation and stress-test classification |
| **Narrative robustness audit** | Sensitivity to tone, emotionality, and credibility priming |
| **Stereotype / identity-leakage audit** | Screening for irrelevant identity language in outputs |
| **Hallucination / grounding audit** (V3) | Citation and unsupported-claim checks against a toy knowledge base |
| **Statistical uncertainty** | Bootstrap / interval estimates on screening rates |
| **Qualitative case studies** | Flagged examples for human review |
| **Human-review rubric** | Structured scores and classifications for legal experts |
| **Streamlit dashboard** | Explore metrics, flagged cases, and validity categories |
| **Final audit report** | Markdown synthesis for submission |
| **Real-case-inspired layer** | Multi-domain Israeli summaries (Legal-Training-IL style) for realism, domain coverage, stereotype/grounding review |
| **Vercel dashboard** | Hybrid synthetic + real-case sections (`web_dashboard/`) |

## 7b. Hybrid audit methodology (two layers)

| Layer | Role | Strict bias rates |
|-------|------|-------------------|
| **Synthetic controlled** | Demographic/language/narrative counterfactuals in housing | **Primary** — use for strict fairness screening |
| **Real-case-inspired** | Multi-domain realism (housing, labor, welfare, immigration, consumer, accessibility) | **Excluded by default** — reliability, grounding, stereotype, qualitative review only |

See `REAL_CASE_DATA_CARD.md` and `results/report/real_case_layer_qa_report.md`. Real-case rows are **not** proof of discrimination and **not** legal advice.

## 8. What this project does **not** claim

- The system is **not an AI judge** and does **not** issue binding rulings.
- Outputs are **not legal advice** and must not be used without qualified human review.
- Screening metrics are **not proof** of unlawful discrimination or judicial bias.
- The audit uses **synthetic** cases and heuristics—it is **not production-ready** and **not a model certification**.
- The **real-case-inspired** layer uses source-derived summaries for realism screening only—not strict counterfactual proof or legal correctness certification.
- Short-vague or vulnerability variants may justify different outputs for **legally relevant** reasons; the audit flags differences for review, it does not automatically label them as unfair.

## Out of scope (intentionally excluded)

- **Party-role / power-asymmetry audit** (e.g. tenant vs landlord power framing as a separate variant family).
- **Standalone interactive HTML report** (review uses Markdown reports and the Streamlit dashboard instead).
