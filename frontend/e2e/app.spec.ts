import { expect, test } from "@playwright/test";

test("dashboard is responsive and has no horizontal overflow", async ({ page }, testInfo) => {
  await page.goto("/voltra/");
  await expect(page.getByRole("heading", { name: "My strips" })).toBeVisible();
  await expect(page.getByText("Total power right now")).toBeVisible();
  await expect(page.getByPlaceholder("Search strips and outlets")).toBeVisible();

  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(1);

  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
    animations: "disabled",
  });
});

test("main navigation surfaces remain reachable", async ({ page }) => {
  await page.goto("/voltra/");
  await page.getByRole("button", { name: /Schedules/i }).click();
  await expect(page.locator("h1", { hasText: "Automation" })).toBeVisible();
  await page.getByRole("button", { name: /Consumption/i }).click();
  await expect(page.locator("h1", { hasText: "Consumption" })).toBeVisible();
});
