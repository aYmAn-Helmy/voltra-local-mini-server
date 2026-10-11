# Voltra Dashboard V2 — GitHub development

This work lives on the `feature/dashboard-v2` branch until the pull request has passed review and automated tests. The deployed `main` branch is unchanged.

## Open in GitHub Codespaces

1. Open the repository on GitHub and select branch `feature/dashboard-v2`.
2. Choose **Code → Codespaces → Create codespace on feature/dashboard-v2**.
3. After the Codespace setup completes, start the isolated Voltra demo:

   ```bash
   docker compose -f docker-compose.demo.yml up -d --build
   ```

4. Optional hot-reload UI development, in another terminal:

   ```bash
   cd frontend
   npm run dev
   ```

5. Open the forwarded **5173** port for Vite (path `/voltra/`); **8086** serves the complete built Docker demo dashboard.

Vite proxies `/voltra/api` to the local Docker demo API on port 8086. The demo uses a fake MTTL-W01 and a dedicated data volume, never production device state.

Stop the demo with:

```bash
docker compose -f docker-compose.demo.yml down
```

## What V2 changes

- New desktop navigation sidebar and responsive dashboard power overview.
- Three live cards for connected strips, active outlets and schedules.
- Improved device search/add toolbar and per-outlet control accessibility.
- Arabic/English language toggle, RTL layout and remembered language choice.
- Better bulk control feedback if some outlets fail.
- Android provisioning no longer assumes an arbitrary fixed LAN server address. It suggests the connected server's LAN IPv4 address when available over local HTTP; for HTTPS setups users enter their LAN server IP.

The existing REST API, device TCP protocol, automation, telemetry and legacy dashboard are unchanged. The UI translation dictionary is centralized in `frontend/src/i18n.ts`; strings not yet translated retain their English fallback.

## Checks

```bash
cd frontend
npm run build
npm run test:e2e
```

Playwright needs the demo server running and Chromium installed (`npx playwright install chromium`). The `.github/workflows/tests.yml` workflow runs Python, frontend build, Docker smoke checks and responsive Playwright tests on pushes and pull requests.

Never expose the physical device TCP port 10086 or discovery UDP 10087 from a Codespace. These services should remain on the trusted physical LAN.

## Review checklist

- Verify dashboard layout at 320–430px, tablet, and 1440px desktop.
- Verify language switching persists across reload; check RTL and that no screen scrolls horizontally.
- Adopt a fake strip in the demo and test individual/bulk outlet actions.
- Check schedules, rooms, settings, energy, legacy fallback and app HTTPS auth against staging.
- Review the Android app's LAN IP autofill with local IP and remote HTTPS configurations before building a signed APK.
- Merge only after required CI checks and staging review pass.
