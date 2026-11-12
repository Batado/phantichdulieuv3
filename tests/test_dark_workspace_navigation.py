import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DarkWorkspaceNavigationTests(unittest.TestCase):
    def test_main_dashboard_has_grouped_left_navigation(self):
        source = (ROOT / "app_v3.py").read_text(encoding="utf-8")
        self.assertIn("TỔNG QUAN", source)
        self.assertIn("PHÂN TÍCH", source)
        self.assertIn("KIỂM SOÁT", source)
        self.assertIn("def _business_nav_button", source)
        self.assertIn('st.switch_page("pages/02_Phan_tich_lay_hang.py")', source)

    def test_pickup_page_has_grouped_vehicle_sections(self):
        source = (ROOT / "pages" / "02_Phan_tich_lay_hang.py").read_text(encoding="utf-8")
        self.assertIn("def _pickup_nav_button", source)
        self.assertIn("Xe khách hàng", source)
        self.assertIn("Xe nhà máy", source)
        self.assertIn("Xe nhà máy thuê ngoài", source)
        self.assertIn("background:#0b0d11", source)


if __name__ == "__main__":
    unittest.main()
