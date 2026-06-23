# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: detention-qa.spec.ts >> Detention dashboard QA >> case review deep link with review_id loads workspace
- Location: e2e/detention-qa.spec.ts:24:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/D001/i).first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 30000ms
  - waiting for getByText(/D001/i).first()

```

```yaml
- banner: BA BenchAssist-IL Audit Detention / Remand Decision-Support Audit · gemini_full detention_full_v1 gemini-2.5-flash-lite
- text: Not legal advice. Not an AI judge. Metrics are audit signals, not proof of unlawful discrimination. Human legal review required.
- navigation "Dashboard sections":
  - tab "◎ Overview Executive summary"
  - tab "◈ Fairness Screening Demographic & proxy analysis"
  - tab "◐ Prompt Mitigation Mode comparison"
  - tab "◉ Bias Analysis Deep-dive findings"
  - tab "◆ Audit Metrics CCR · DIR · Masking"
  - tab "◫ Case Explorer Side-by-side review" [selected]
  - tab "🤖 Agent Audit Agentic RAG results"
  - tab "◇ Run Metadata Data quality"
- main:
  - heading "Case Explorer" [level=1]
  - paragraph: Review individual cases — neutral baseline vs counterfactual variant
  - status:
    - text: ∅
    - heading "No case review records" [level=3]
    - paragraph: The case review index is empty. Run the pipeline to generate case-level review records.
- contentinfo:
  - paragraph: BenchAssist-IL Audit Dashboard · Research tool for AI fairness review · Not legal advice
  - list:
    - listitem: ·Not legal advice.
    - listitem: ·Not an AI judge.
    - listitem: ·Metrics are audit signals, not proof of unlawful discrimination.
    - listitem: ·Human legal review required.
- alert
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | 
  3  | async function waitForDashboard(page: import("@playwright/test").Page) {
  4  |   await page.goto("/");
  5  |   await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
  6  | }
  7  | 
  8  | test.describe("Detention dashboard QA", () => {
  9  |   test("home loads with core sections", async ({ page }) => {
  10 |     await waitForDashboard(page);
  11 |     await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible();
  12 |   });
  13 | 
  14 |   test("all primary tabs render", async ({ page }) => {
  15 |     test.setTimeout(240_000);
  16 |     const tabs = ["overview", "fairness", "mitigation", "audit-metrics", "case-explorer", "run-metadata"];
  17 |     for (const tab of tabs) {
  18 |       await page.goto(`/?tab=${tab}`);
  19 |       await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
  20 |       await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible({ timeout: 30_000 });
  21 |     }
  22 |   });
  23 | 
  24 |   test("case review deep link with review_id loads workspace", async ({ page }) => {
  25 |     test.setTimeout(120_000);
  26 |     await page.goto("/?tab=case-explorer&review_id=D001::D001-arab_name_he::baseline");
  27 |     await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
> 28 |     await expect(page.getByText(/D001/i).first()).toBeVisible({ timeout: 30_000 });
     |                                                   ^ Error: expect(locator).toBeVisible() failed
  29 |   });
  30 | 
  31 |   test("legacy tab URLs redirect or load safely", async ({ page }) => {
  32 |     await page.goto("/?tab=overview");
  33 |     await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
  34 |     await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible();
  35 |   });
  36 | });
  37 | 
```