import unittest

import pandas as pd

from modules.pickup_analysis import analyze_customer_pickups


class CurrentMainRegionalAuditTests(unittest.TestCase):
    def test_province_and_business_region_are_kept_separate(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 12, Phường Long Bình, Thành phố Đồng Nai, Việt Nam",
            "Khu vưc": "Thành phố Đồng Nai",
            "Miền2": "Miền Nam (Đông Nam Bộ)",
            "Mã kho2": 281,
            "Số chứng từ": "281.12345",
            "Shipping method": "Xe khách hàng",
            "Mã khách hàng": "KH-DN",
            "Tên khách hàng": "NPP Đồng Nai",
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
        self.assertIn("_event_key", detail.columns)
        self.assertEqual(detail.iloc[0]["_event_key"], "KH-DN|281.12345")
        self.assertIn("Miền2 theo workbook", province_summary.columns)

    def test_luong_son_is_not_silently_relabelled_as_phuong_tam_thanh(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 561, Phường Tam Thanh, Tỉnh Lạng Sơn, Việt Nam",
            "Khu vưc": "Phường Tam Thanh",
            "Miền2": "Miền Bắc",
            "Mã kho2": 261,
            "Số chứng từ": "261.12346",
            "Shipping method": "Xe khách hàng",
            "Mã khách hàng": "KH-LS",
            "Tên khách hàng": "NPP Lạng Sơn",
            "Ghi chú2": "Hợp lý",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Phường Tam Thanh",
            "Kho hợp lý": "Khu vực tham chiếu",
            "Mã kho": 261291,
        }])
        detail, summary, _ = analyze_customer_pickups(transactions, matrix)
        self.assertEqual(detail.iloc[0]["Tỉnh/thành nhận diện"], "lang son")
        self.assertEqual(detail.iloc[0]["Đơn vị khớp ma trận"], "phuong tam thanh")
        self.assertTrue(detail.iloc[0]["Kết quả đối chiếu"].startswith("Cần xác minh"))
        self.assertEqual(summary.iloc[0]["Số_chưa_đủ_dữ_liệu"], 1)
        self.assertIn("_event_key", detail.columns)
        self.assertEqual(detail.iloc[0]["_event_key"], "KH-LS|261.12346")


    def test_factory_vehicle_returns_empty_detail_without_raising(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 1, Phường 1, Tỉnh Đồng Nai",
            "Khu vưc": "Đồng Nai",
            "Miền2": "Miền Nam",
            "Mã kho2": 281,
            "Số chứng từ": "281.99999",
            "Shipping method": "Xe nhà máy",
            "Mã khách hàng": "KH-F",
            "Tên khách hàng": "NPP Factory",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đồng Nai",
            "Kho hợp lý": "Đông Nam Bộ",
            "Mã kho": "281",
        }])
        detail, customer_summary, province_summary = analyze_customer_pickups(transactions, matrix)
        self.assertTrue(detail.empty)
        self.assertTrue(customer_summary.empty)
        self.assertTrue(province_summary.empty)

    def test_empty_input_returns_empty_frames(self):
        transactions = pd.DataFrame(columns=[
            "Địa chỉ", "Mã kho2", "Số chứng từ", "Shipping method"
        ])
        matrix = pd.DataFrame(columns=["Khu vực/Tỉnh thành", "Kho hợp lý", "Mã kho"])
        detail, customer_summary, province_summary = analyze_customer_pickups(transactions, matrix)
        self.assertTrue(detail.empty)
        self.assertTrue(customer_summary.empty)
        self.assertTrue(province_summary.empty)


if __name__ == "__main__":
    unittest.main()
