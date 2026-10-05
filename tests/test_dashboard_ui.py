import unittest

from voltra_local.dashboard import DASHBOARD


class DashboardUIV018Tests(unittest.TestCase):
    def test_mobile_home_surface_is_present(self):
        for marker in (
            "VOLTRA LIVE",
            "My strips",
            "Total power right now",
            "Consumption",
            "Schedules",
            "Power automation",
            "Search strips and outlets",
            "Turn all on",
            "Turn all off",
            "Add strip",
        ):
            self.assertIn(marker, DASHBOARD)

    def test_dashboard_keeps_existing_admin_pages(self):
        for page in (
            'id="page-discover"',
            'id="page-mapping"',
            'id="page-network"',
            'id="page-automation"',
            'id="page-energy"',
            'id="page-advanced"',
        ):
            self.assertIn(page, DASHBOARD)


if __name__ == "__main__":
    unittest.main()
