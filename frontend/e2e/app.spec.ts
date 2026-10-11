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

test("mobile and tablet keep the original dashboard layout", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "desktop", "Original layout is for narrow viewports");
  await page.goto("/voltra/");

  await expect(page.locator(".mobile-dashboard")).toBeVisible();
  await expect(page.locator(".profile-card")).toBeVisible();
  await expect(page.locator(".power-hero")).toBeVisible();
  await expect(page.locator(".bottom-nav")).toBeVisible();
  await expect(page.locator(".fab")).toBeVisible();
  await expect(page.locator(".dw-sidebar")).toBeHidden();
  await expect(page.locator(".desktop-dashboard")).toBeHidden();
});

test("desktop has independent navigation, power summary and compact device grid", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Desktop-specific layout");
  await page.goto("/voltra/");

  await expect(page.locator(".dw-sidebar")).toBeVisible();
  await expect(page.locator(".dw-topbar")).toBeVisible();
  await expect(page.locator(".dw-overview")).toBeVisible();
  await expect(page.locator(".dw-device-grid")).toBeVisible();
  await expect(page.locator(".mobile-dashboard")).toBeHidden();
  await expect(page.locator(".bottom-nav")).toBeHidden();
  await expect(page.locator(".fab")).toBeHidden();

  await page.getByRole("group", { name: "Filter devices by connection" }).getByRole("button", { name: "Online" }).click();
  await expect(page.getByRole("button", { name: "Online", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("group", { name: "Filter devices by connection" }).getByRole("button", { name: "All devices" }).click();
  await page.getByPlaceholder("Search strips and outlets").fill("no-strip-has-this-name");
  await expect(page.getByText("No matching devices")).toBeVisible();
  await page.getByPlaceholder("Search strips and outlets").clear();

  await page.getByRole("navigation", { name: "Workspace pages" }).getByRole("button", { name: "Consumption" }).click();
  await expect(page.locator(".dw-topbar h1")).toHaveText("Consumption");
  await page.getByRole("navigation", { name: "Workspace pages" }).getByRole("button", { name: "Dashboard" }).click();
  await expect(page.locator(".dw-topbar h1")).toHaveText("My strips");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("Arabic interface toggles direction without changing the active layout", async ({ page }, testInfo) => {
  await page.goto("/voltra/");
  await page.getByRole("button", { name: "Change language" }).click();
  await expect(page.locator(".app-shell")).toHaveAttribute("lang", "ar");
  await expect(page.locator(".app-shell")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "أجهزتي" })).toBeVisible();
  await expect(page.getByPlaceholder("ابحث عن مشترك أو مخرج")).toBeVisible();
  if (testInfo.project.name === "desktop") {
    await expect(page.locator(".dw-sidebar")).toBeVisible();
  } else {
    await expect(page.locator(".bottom-nav")).toBeVisible();
  }

  await page.reload();
  await expect(page.locator(".app-shell")).toHaveAttribute("dir", "rtl");
  await page.getByRole("button", { name: "تغيير اللغة" }).click();
  await expect(page.locator(".app-shell")).toHaveAttribute("dir", "ltr");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
