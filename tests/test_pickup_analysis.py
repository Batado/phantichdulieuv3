import unittest

import pandas as pd

from modules.pickup_analysis import (
    analyze_customer_pickups,
    build_warehouse_matrix,
    extract_province,
    parse_code_sequence,
)


class PickupAnalysisTests(unittest.TestCase):
    def test_concatenated_codes_restore_leading_zero(self):
        self.assertEqual(
            parse_code_sequence(53054281284),
            {"053", "054", "281", "284"},
        )

    def test_matrix_and_province_match(self):
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đắk Lắk",
            "Kho hợp lý": "Bình Định, Tây Nguyên, Đà Nẵng",
            "Mã kho": 251252263,
        }])
        rules = build_warehouse_matrix(matrix)
        self.assertEqual(rules["dak lak"], {"251", "252", "263"})
        self.assertEqual(
            extract_province("Thôn 5, Xã Ea Ning, Tỉnh Đắk Lắk, Việt Nam", set(rules)),
            "dak lak",
        )

    def test_only_customer_vehicle_is_scored(self):
        transactions = pd.DataFrame([
            {
                "Địa chỉ": "Số 1, Tỉnh Đắk Lắk, Việt Nam",
                "Mã kho2": 252,
                "Số chứng từ": "252.123",
                "Shipping method": "Xe khách hàng",
                "Kho lấy hàng": "TK Đaklak",
                "Số xe": "47H-12345",
                "Mã khách hàng": "KH01",
                "Tên khách hàng": "NPP A",
                "Ngày chứng từ": "2026-10-01",
            },
            {
                "Địa chỉ": "Số 1, Tỉnh Đắk Lắk, Việt Nam",
                "Mã kho2": 252,
                "Số chứng từ": "252.124",
                "Shipping method": "Xe nhà máy",
                "Kho lấy hàng": "TK Đaklak",
                "Số xe": "47H-12345",
                "Mã khách hàng": "KH01",
                "Tên khách hàng": "NPP A",
                "Ngày chứng từ": "2026-10-01",
            },
        ])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đắk Lắk",
            "Kho hợp lý": "Tây Nguyên",
            "Mã kho": 251252263,
        }])
        detail, summary, _ = analyze_customer_pickups(transactions, matrix)
        self.assertEqual(len(detail), 1)
        self.assertEqual(detail.iloc[0]["Kết quả đối chiếu"], "Phù hợp danh mục kho")
        self.assertEqual(summary.iloc[0]["Số_phù_hợp"], 1)


if __name__ == "__main__":
    unittest.main()
