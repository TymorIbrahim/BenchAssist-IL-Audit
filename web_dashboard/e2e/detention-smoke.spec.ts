import { test, expect } from "@playwright/test";

test("detention dashboard home loads", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
  await expect(page.getByText(/BenchAssist-IL/i).first()).toBeVisible();
});

test("audit metrics tab loads successfully", async ({ page }) => {
  await page.goto("/?tab=audit-metrics");
  await expect(page.getByText(/Loading/i)).toBeHidden({ timeout: 60_000 });
  await expect(page.getByText(/Audit Metrics/i).first()).toBeVisible({ timeout: 30_000 });
});
