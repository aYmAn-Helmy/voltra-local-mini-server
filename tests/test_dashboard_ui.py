from pathlib import Path
import inspect
import unittest

from voltra_local import __version__
from voltra_local.dashboard import DASHBOARD
from voltra_local.http_api import APIHandler


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class ProfessionalFrontendV020Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(__version__, "0.20.0")

    def test_react_frontend_sources_exist(self):
        for path in (
            FRONTEND / "package.json",
            FRONTEND / "src" / "App.tsx",
            FRONTEND / "src" / "views.tsx",
            FRONTEND / "src" / "styles.css",
            FRONTEND / "e2e" / "app.spec.ts",
        ):
            self.assertTrue(path.is_file(), path)

    def test_reference_home_surface_is_in_react_ui(self):
        source = "\n".join(
            (FRONTEND / "src" / name).read_text(encoding="utf-8")
            for name in ("views.tsx", "ui.tsx")
        )
        for marker in (
            "Total power right now",
            "Consumption",
            "Schedules",
            "Power automation",
            "Search results",
            "Turn all on",
            "Turn all off",
        ):
            self.assertIn(marker, source)

    def test_legacy_dashboard_remains_available_as_fallback(self):
        self.assertIn("Dashboard", DASHBOARD)
        source = inspect.getsource(APIHandler.do_GET)
        self.assertIn("/voltra/legacy", source)
        self.assertIn("_serve_frontend", source)


if __name__ == "__main__":
    unittest.main()
