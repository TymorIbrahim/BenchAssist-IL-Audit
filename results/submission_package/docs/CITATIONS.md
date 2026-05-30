# Citations

References used or mentioned in this project. Full bibliographic details should match your course bibliography style; entries below are pointers only.

## Accountability and audit methodology

- **Goodman, E., & Tréhu, L.** — *AI Audit-Washing and Accountability* (cited in `final_report.py` and README for the Why / Who / What-When / How audit structure and audit-washing risks).

## Fairness, bias, and evaluation of language models

- **Fairness and Machine Learning** — conceptual background on fairness definitions and limitations of automated fairness metrics (general RAI framing; see course materials).
- **Hugging Face — LLM bias evaluation** — methodology inspiration for structured comparison of model outputs across perturbed inputs (see HF ecosystem docs on evaluation practices).

## Perturbation / counterfactual testing

- **PANDA / perturbation augmentation** — inspiration for counterfactual and paraphrase-style robustness testing (as discussed in course readings on perturbation-based NLP evaluation).

## Israeli legal NLP resources (optional / background)

- **[BrainboxAI/legal-training-il](https://huggingface.co/datasets/BrainboxAI/legal-training-il)** — optional Hugging Face dataset for exploration via `benchassist.israeli_data`; **not** used as adjudicative ground truth in this audit. Check dataset license before reuse.
- **Legal-Training-IL** — same dataset family; inspection-only in this repository.

## Civil society / rights information (toy grounding corpus)

- **Kol-Zchut** — referenced only if corresponding toy entries exist in `data/knowledge/israeli_housing_knowledge.jsonl` with explicit `caution` fields; the bundled knowledge base is **educational toy text**, not live Kol-Zchut content.

## Regulatory background (comparative)

- **EU Artificial Intelligence Act** — comparative background on high-risk AI and documentation expectations (background reading only; this project is not a conformity assessment).

## Software

- **Python**, **pandas**, **pydantic**, **pytest**, **matplotlib**, **Streamlit**, **plotly** (optional dashboard) — see `pyproject.toml` for versions.
- **Google Gemini API** (optional) — only when running `--provider gemini`; not required for mock demo.

---

**Note:** Do not cite this audit’s **screening metrics** as legal findings. All outputs require **human judicial review**.
