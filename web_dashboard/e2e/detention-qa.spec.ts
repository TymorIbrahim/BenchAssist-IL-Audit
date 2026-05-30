import { test, expect } from "@playwright/test";

const FORBIDDEN = [/bias proven/i, /discriminatory AI/i, /illegal AI judge/i];

async function waitForDashboard(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByText(/Loading dashboard/i)).toBeHidden({ timeout: 60_000 });
  await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
}

test.describe("Detention dashboard QA", () => {
  test("home loads with core sections and export metadata", async ({ page }) => {
    await waitForDashboard(page);
    await expect(page.getByRole("heading", { name: /BenchAssist-IL Detention Audit/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Research question" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Export metadata/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Start expert review/i })).toBeVisible();
  });

  test("all 8 tabs render primary headings", async ({ page }) => {
    test.setTimeout(180_000);
    await waitForDashboard(page);
    const tabs: { id: string; heading: RegExp; waitRecords?: boolean }[] = [
      { id: "home", heading: /BenchAssist-IL Detention Audit/i },
      { id: "audit-results", heading: /Audit Results/i },
      { id: "case-review", heading: /Case Review Workspace/i, waitRecords: true },
      { id: "mitigation", heading: /Mitigation Comparison/i },
      { id: "real-cases", heading: /Real Case Review/i },
      { id: "legal-reliability", heading: /Legal Reliability/i },
      { id: "reports", heading: /Reports/i },
      { id: "methodology", heading: /Methodology/i },
    ];
    for (const tab of tabs) {
      await page.goto(`/?tab=${tab.id}`);
      await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
      if (tab.waitRecords) {
        await expect(page.getByText(/Loading.*review records/i)).toBeHidden({ timeout: 90_000 });
      }
      await expect(page.getByRole("heading", { name: tab.heading }).first()).toBeVisible({ timeout: 30_000 });
    }
  });

  test("audit results shows index-based executive findings", async ({ page }) => {
    await page.goto("/?tab=audit-results");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Executive findings" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Findings by legal issue" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Base-case variant matrix" })).toBeVisible();
  });

  test("mitigation shows cross-prompt heatmap", async ({ page }) => {
    await page.goto("/?tab=mitigation");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Cross-prompt field instability" })).toBeVisible({ timeout: 30_000 });
  });

  test("case review deep link with review_id loads workspace", async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto("/?tab=case-review&review_id=D001::D001-ethiopian_israeli_he::baseline");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByText(/Loading.*review records/i)).toBeHidden({ timeout: 90_000 });
    await expect(page.getByRole("heading", { name: /Case Review Workspace/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("heading", { name: /חשד לתקיפה|D001/i }).first()).toBeVisible({ timeout: 30_000 });
  });

  test("legacy tab URLs redirect to new tabs", async ({ page }) => {
    await page.goto("/?tab=overview");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /BenchAssist-IL Detention Audit/i })).toBeVisible();

    await page.goto("/?tab=findings");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Audit Results/i })).toBeVisible();

    await page.goto("/?tab=expert-workspace");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByText(/Loading.*review records/i)).toBeHidden({ timeout: 90_000 });
    await expect(page.getByRole("heading", { name: /Case Review Workspace/i })).toBeVisible({ timeout: 30_000 });
  });

  test("no forbidden conclusion language on home and audit results", async ({ page }) => {
    for (const tab of ["home", "audit-results"] as const) {
      await page.goto(`/?tab=${tab}`);
      await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
      const text = await page.locator("main, .tab-panel, body").first().innerText();
      for (const pattern of FORBIDDEN) {
        expect(text).not.toMatch(pattern);
      }
    }
  });

  test("export metadata panel expands with provenance", async ({ page }) => {
    await waitForDashboard(page);
    await page.getByRole("button", { name: /Export metadata/i }).click();
    await expect(page.getByText(/Exported at/i)).toBeVisible();
    await expect(page.getByText(/gemini full/i).first()).toBeVisible();
  });
});
