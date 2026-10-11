# Voltra Desktop Dashboard V3

This branch adds a **desktop-only experience** to the existing Voltra web interface. Its base is the unchanged production `main` branch. The existing **mobile/tablet React dashboard** and the **Flutter mobile app** are left intact.

## Responsive behavior

- **Below 1120px:** the original mobile/tablet web UI, including profile, power hero, bottom navigation, outlet tiles and floating Add strip action.
- **1120px and above:** new desktop sidebar, page toolbar, live power summary, KPIs, shortcuts, device search/filter controls and a compact multi-column device grid.
- Both layouts share the same `App` state, API, login, search state and command handlers. Hidden layouts are excluded from the viewport via `display:none`. Device controls are not duplicated on-screen.
- Backend, discovery protocol and the legacy dashboard are not changed.

## Work directly on GitHub

1. In the repository select branch `feature/desktop-dashboard-v3`.
2. Choose **Code → Codespaces → Create codespace on feature/desktop-dashboard-v3**.
3. Start the demo server in its own Docker volume:

   ```bash
   docker compose -f docker-compose.demo.yml up -d --build
   ```
4. In a second terminal run:

   ```bash
   cd frontend
   npm run dev
   ```

5. Open forwarded port 5173 and navigate to `/voltra/`. Vite forwards Voltra API traffic to the Docker demo on 8086. The demo is not the actual physical network, and no production strip state is modified.

## Verify

```bash
cd frontend
npm run build
npx playwright install chromium
npm run test:e2e
```

The repository's GitHub Actions also runs Python tests, frontend builds, Docker smoke tests and Playwright on mobile, tablet and desktop.

Verify both breakpoints, outlet controls, desktop navigation and the no-results search state before merging the pull request. The mobile version is deliberately unchanged; desktop features are maintained in `frontend/src/desktop.tsx` and `frontend/src/desktop.css`. Avoid exposing the device TCP and discovery ports from a public Codespace.
