import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 1,
  use: {
    baseURL: process.env.VOLTRA_E2E_URL || "http://127.0.0.1:8086",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "mobile", use: { ...devices["Pixel 7"] } },
    { name: "tablet", use: { viewport: { width: 834, height: 1112 } } },
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
  ],
});
