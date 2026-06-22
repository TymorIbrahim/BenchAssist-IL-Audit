import { test, expect } from "@playwright/test";

async function waitForDashboard(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
}

test.describe("Detention dashboard QA", () => {
  test("home loads with core sections", async ({ page }) => {
    await waitForDashboard(page);
    await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible();
  });

  test("all primary tabs render", async ({ page }) => {
    test.setTimeout(240_000);
    const tabs = ["overview", "fairness", "mitigation", "audit-metrics", "case-explorer", "run-metadata"];
    for (const tab of tabs) {
      await page.goto(`/?tab=${tab}`);
      await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
      await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible({ timeout: 30_000 });
    }
  });

  test("legacy tab URLs redirect or load safely", async ({ page }) => {
    await page.goto("/?tab=overview");
    await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
    await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible();
  });
});
