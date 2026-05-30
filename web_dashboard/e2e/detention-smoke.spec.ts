import { test, expect } from "@playwright/test";

test("detention dashboard home loads with manifest", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/Loading dashboard/i)).toBeHidden({ timeout: 60_000 });
  await expect(page.getByRole("button", { name: /Home/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Case Review|Audit Results|Research/i }).first()).toBeVisible();
});

test("audit results tab shows executive findings from index", async ({ page }) => {
  await page.goto("/?tab=audit-results");
  await expect(page.getByText(/Loading detention audit dashboard/i)).toBeHidden({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Executive findings" })).toBeVisible({ timeout: 30_000 });
});
