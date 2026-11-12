import unittest

import pandas as pd

from modules.pickup_analysis import analyze_customer_pickups


class EmptyPickupSchemaTests(unittest.TestCase):
    def test_no_customer_vehicle_result_supports_dashboard_join(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 1, Phường 1, Tỉnh Đồng Nai",
            "Mã kho2": "281",
            "Số chứng từ": "281.00001",
            "Shipping method": "Xe nhà máy",
        }])
        matrix = pd.DataFrame(columns=["Khu vực/Tỉnh thành", "Mã kho"])
        detail, customers, provinces = analyze_customer_pickups(transactions, matrix)

        self.assertTrue(detail.empty)
        self.assertTrue(customers.empty)
        self.assertTrue(provinces.empty)
        self.assertIn("_event_key", detail.columns)
        self.assertIn("Kết quả đối chiếu", detail.columns)
        self.assertIn("Mã kho được phép", detail.columns)
        self.assertTrue(detail.set_index("_event_key")["Kết quả đối chiếu"].empty)
        self.assertTrue(detail.set_index("_event_key")["Mã kho được phép"].empty)


if __name__ == "__main__":
    unittest.main()
