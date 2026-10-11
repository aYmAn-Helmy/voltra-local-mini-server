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

test("Arabic mode changes direction, labels, and persists after reload", async ({ page }) => {
  await page.goto("/voltra/");
  await page.getByRole("button", { name: "Change language" }).click();
  await expect(page.locator(".app-shell")).toHaveAttribute("lang", "ar");
  await expect(page.locator(".app-shell")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "أجهزتي" })).toBeVisible();
  await expect(page.getByPlaceholder("ابحث عن مشترك أو مخرج")).toBeVisible();

  await page.reload();
  await expect(page.locator(".app-shell")).toHaveAttribute("dir", "rtl");
  await page.getByRole("button", { name: "تغيير اللغة" }).click();
  await expect(page.locator(".app-shell")).toHaveAttribute("dir", "ltr");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("desktop navigation uses the dedicated sidebar", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Sidebar is desktop-only");
  await page.goto("/voltra/");
  const sidebar = page.locator(".desktop-sidebar");
  await expect(sidebar).toBeVisible();
  await expect(page.locator(".bottom-nav")).toBeHidden();
  await sidebar.getByRole("button", { name: "Consumption" }).click();
  await expect(page.getByRole("heading", { name: "Consumption" }).last()).toBeVisible();
  await sidebar.getByRole("button", { name: "My strips" }).click();
  await expect(page.getByText("Total power right now")).toBeVisible();
});
