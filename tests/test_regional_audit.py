import unittest

# Regression coverage for the source workbook's regional warehouse rules.

import pandas as pd

from modules.pickup_analysis import analyze_customer_pickups


class RegionalAuditTests(unittest.TestCase):
    def test_city_prefix_is_normalized_and_business_region_is_preserved(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 12, Phường Long Bình, Thành phố Đồng Nai, Việt Nam",
            "Khu vưc": "Thành phố Đồng Nai",
            "Miền2": "Miền Nam (Đông Nam Bộ)",
            "Mã kho2": 281,
            "Số chứng từ": "281.12345",
            "Shipping method": "Xe khách hàng",
            "Mã khách hàng": "KH-DN",
            "Tên khách hàng": "NPP Đồng Nai",
            "Ghi chú2": "Hợp lý",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đồng Nai",
            "Kho hợp lý": "Đông Nam Bộ",
            "Mã kho": 53054281284,
        }])

        detail, _, province_summary = analyze_customer_pickups(transactions, matrix)

        self.assertEqual(detail.iloc[0]["Tỉnh/thành nhận diện"], "dong nai")
        self.assertEqual(detail.iloc[0]["Miền2 theo workbook"], "Miền Nam (Đông Nam Bộ)")
        self.assertEqual(detail.iloc[0]["Đối chiếu Khu vực với địa chỉ"], "Khớp thành phần địa chỉ")
        self.assertEqual(detail.iloc[0]["Kết quả đối chiếu"], "Phù hợp danh mục kho")
        self.assertIn("Miền2 theo workbook", province_summary.columns)

    def test_business_region_is_not_reclassified_by_geographic_guess(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 1, Phường Đông Vệ, Tỉnh Thanh Hóa, Việt Nam",
            "Khu vưc": "Tỉnh Thanh Hóa",
            "Miền2": "Miền Trung",
            "Mã kho2": 261,
            "Số chứng từ": "261.12346",
            "Shipping method": "Xe khách hàng",
            "Mã khách hàng": "KH-TH",
            "Tên khách hàng": "NPP Thanh Hóa",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Thanh Hóa",
            "Kho hợp lý": "Miền Bắc",
            "Mã kho": 261291,
        }])

        detail, _, _ = analyze_customer_pickups(transactions, matrix)

        self.assertEqual(detail.iloc[0]["Miền2 theo workbook"], "Miền Trung")
        self.assertEqual(detail.iloc[0]["Kết quả đối chiếu"], "Phù hợp danh mục kho")


if __name__ == "__main__":
    unittest.main()
