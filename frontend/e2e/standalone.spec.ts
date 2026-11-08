import { expect, test } from "@playwright/test";

test("native firmware console controls relay and saves device-owned scheduler", async ({ page }) => {
  const mac = "ABCDEF123456";
  const rule = () => ({ minute: 0, mode: 0, day: 0, channel: 0, on: 0 });
  const schedule = { timezone: 120, rules: Array.from({ length: 8 }, rule) };
  const config = {
    device: "MTTL Test", channels: ["SW 1", "SW 2", "SW 3", "SW 4"], language: 1,
    broker: "", port: 1883, user: "", topic: "mttl", enabled: false, mqtt_password_set: false,
    persistent: true, protection: { enabled: 7, temperature: 90, current: 16000, power: 3000 },
    timer_minutes: [0, 0, 0, 0], button_lock: 0, schedule, revision: "fake-rev",
  };
  const device = {
    name: "MTTL Test", hardware_ready: true,
    channels: ["SW 1", "SW 2", "SW 3", "SW 4"].map(name => ({
      name, on: false, locked: false, power_mw: 0, meter_wh: 0, current_ma: 0, temp_dc: 240,
    })),
    power_mw: 0, meter_wh: 0, voltage_dv: 2321, current_ma: 0,
    timer_running: 0, timer_end: [0, 0, 0, 0], mqtt_state: 0,
  };
  const status = {
    mac: "ab:cd:ef:12:34:56", state: 5, ip: 3232235870,
    uptime_ms: 130000, hardware_ready: true, ssid_hex: "", rssi: -45,
    unix_ms: 1800000000000, storage: [1, 1, 0, 0],
  };
  let postedSchedule: any = null;
  const strip = {
    mac, name: "MTTL Test", online: true, managed: true, enabled: true, state: "active",
    device_type: "standalone_http", model: "MTTL-W01", firmware_version: "Standalone 2.1.1",
    last_ip: "192.168.1.88", outlets: device.channels.map((c, i) => ({
      channel: i + 1, name: c.name, relay: false, power_w: 0,
    })),
    total_power_w: 0, health: { score: 100, status: "healthy", reasons: [] },
  };

  await page.route("**/voltra/api/overview", async route => {
    const upstream = await route.fetch();
    const data = await upstream.json();
    data.strips = [strip, ...data.strips];
    data.summary.online_strips += 1;
    await route.fulfill({ status: 200, json: data });
  });
  await page.route("**/voltra/api/standalone/*/details", async route => {
    await route.fulfill({ status: 200, json: { device, status, config, memory: {}, energy: {}, firmware: null } });
  });
  await page.route("**/voltra/api/standalone/*/live", async route => {
    await route.fulfill({ status: 200, json: { device, status } });
  });
  await page.route("**/voltra/api/standalone/*/control", async route => {
    const body = route.request().postDataJSON();
    if (body.channel < 4) device.channels[body.channel].on = body.on;
    else device.channels.forEach(channel => { channel.on = body.on; });
    await route.fulfill({ status: 200, json: { online: true, outlets: device.channels.map((c, i) => ({
      channel: i + 1, relay: c.on,
    })) } });
  });
  await page.route("**/voltra/api/standalone/*/config", async route => {
    const body = route.request().postDataJSON();
    postedSchedule = body.schedule;
    config.schedule = postedSchedule;
    await route.fulfill({ status: 200, json: { ...config } });
  });

  await page.goto("/voltra/");
  await expect(page.getByText("MTTL Test").first()).toBeVisible();
  await page.getByRole("button", { name: /Open native controls/i }).click();
  await expect(page.getByRole("tab", { name: "Scheduler" })).toBeVisible();
  await page.getByRole("tab", { name: "Scheduler" }).click();
  await page.getByRole("button", { name: "Add rule" }).click();
  await expect(page.getByText("Rule 1")).toBeVisible();
  await page.getByRole("button", { name: "Save schedule to device" }).click();
  await expect.poll(() => postedSchedule?.rules?.[0]?.mode).toBe(129);
  expect(postedSchedule.rules).toHaveLength(8);
  await page.getByRole("tab", { name: "Power strip" }).click();
  await page.getByRole("button", { name: /^SW 1/i }).click();
  expect(device.channels[0].on).toBeTruthy();
});
