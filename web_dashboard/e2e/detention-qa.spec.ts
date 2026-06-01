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

  test("all primary tabs render headings", async ({ page }) => {
    test.setTimeout(240_000);
    await waitForDashboard(page);
    const tabs: { id: string; heading: RegExp; waitRecords?: boolean }[] = [
      { id: "home", heading: /BenchAssist-IL Detention Audit/i },
      { id: "audit-results", heading: /Audit Results/i },
      { id: "case-review", heading: /Case Review Workspace/i, waitRecords: true },
      { id: "mitigation", heading: /Mitigation Comparison/i },
      { id: "validity", heading: /Validity & exclusions/i },
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

  test("home does not eagerly load all review records", async ({ page }) => {
    await waitForDashboard(page);
    await expect(page.getByText(/Loading.*review records in background/i)).toHaveCount(0);
    await expect(page.getByText(/Loading case comparison/i)).toHaveCount(0);
  });

  test("case review deep link with review_id loads workspace", async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto("/?tab=case-review&review_id=D004::D004-russian_immigrant_he::baseline");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Case Review Workspace/i })).toBeVisible({ timeout: 30_000 });
    const comparison = page.locator(".review-main-panel");
    await expect(comparison.getByRole("heading", { name: "Audit signal" })).toBeVisible({ timeout: 30_000 });
    await expect(comparison.getByRole("strong").filter({ hasText: /insufficient information → medium/i })).toBeVisible({ timeout: 30_000 });
  });

  test("validity shows address-proxy bucket for minimal schema", async ({ page }) => {
    await page.goto("/?tab=validity");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Validity & exclusions/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Address-proxy validity bucket" })).toBeVisible({ timeout: 30_000 });
  });

  test("validity opens address-proxy case review queue", async ({ page }) => {
    await page.goto("/?tab=validity");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await page.getByRole("button", { name: /Open address-proxy review queue/i }).click();
    await expect(page.getByRole("heading", { name: /Case Review Workspace/i })).toBeVisible({ timeout: 30_000 });
    await expect(page).toHaveURL(/cr_bucket=address_proxy/);
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

  test("case review mobile tabs switch panes", async ({ page }) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/?tab=case-review&review_id=D004::D004-russian_immigrant_he::baseline");
    await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Case Review Workspace/i })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("tab", { name: "Comparison" }).click();
    await expect(page.locator(".review-main-panel")).toBeFocused({ timeout: 10_000 });
    await expect(page.locator(".review-main-panel").getByRole("heading", { name: "Audit signal" })).toBeVisible({ timeout: 30_000 });
  });

  test("export metadata panel expands with provenance", async ({ page }) => {
    await waitForDashboard(page);
    await page.getByRole("button", { name: /Export metadata/i }).click();
    await expect(page.getByText(/Exported at/i)).toBeVisible();
    await expect(
      page.getByText(/gemini minimal address|gemini expanded full|gemini full/i).first()
    ).toBeVisible();
  });
});
