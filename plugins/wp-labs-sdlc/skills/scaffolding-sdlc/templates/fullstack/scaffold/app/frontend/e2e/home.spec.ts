import { expect, test } from "@playwright/test";

test("home page loads", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /welcome/i })).toBeVisible();
});

test("can navigate to widgets", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Widgets" }).click();
  await expect(page.getByRole("heading", { name: /widgets/i })).toBeVisible();
});
