import unittest

from voltra_local.dashboard import DASHBOARD


class DashboardUIV019Tests(unittest.TestCase):
    def test_desktop_dashboard_surface_is_present(self):
        for marker in (
            "Dashboard",
            "Smart strips",
            "Total strips",
            "Outlets on",
            "Outlets off",
            "Quick actions",
            "Turn all off",
            "Rooms",
            "Energy",
            "Account",
        ):
            self.assertIn(marker, DASHBOARD)

    def test_light_and_dark_theme_controls_are_present(self):
        self.assertIn("voltra_dashboard_theme", DASHBOARD)
        self.assertIn('data-theme', DASHBOARD)
        self.assertIn("toggleTheme()", DASHBOARD)
        self.assertIn('Light / dark mode', DASHBOARD)

    def test_existing_core_api_routes_are_used(self):
        for route in (
            "/voltra/api/overview",
            "/voltra/api/automation",
            "/voltra/api/energy",
            "/voltra/api/schedules",
            "/voltra/api/provision",
        ):
            self.assertIn(route, DASHBOARD)


if __name__ == "__main__":
    unittest.main()
