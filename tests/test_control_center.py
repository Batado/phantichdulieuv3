import unittest

import pandas as pd

from modules.control_center import _make_findings


class FindingGenerationTests(unittest.TestCase):
    def test_builds_findings_for_all_major_npp_signals(self):
        risk = pd.DataFrame([{
            "Mã khách hàng": "NPP001",
            "NPP": "Nhà phân phối A",
            "Điểm sàng lọc": 72,
            "Mức độ": "Rất cao",
            "Độ phủ dữ liệu": 1.0,
            "Dòng kho ngoài danh sách": 1,
            "Dòng xe dùng chung cùng ngày": 1,
            "Dòng xe dùng chung nhiều ngày": 1,
            "Dòng địa chỉ trùng": 1,
            "Mẫu hình doanh thu/sản lượng": "Giảm mạnh so với kỳ trước",
            "Biến động kinh doanh cần kiểm tra": True,
            "Liên quan dịch chuyển mặt hàng": True,
            "Số tháng biến động đột ngột": 1,
        }])

        data = {
            "risk_summary": risk,
            "warehouse_evidence": pd.DataFrame([{
                "_customer_key": "NPP001",
                "_chung_tu": "263.18067094",
                "_ma_kho": "263",
                "_ten_kho": "TK ĐN",
                "_vung": "Miền Bắc",
                "_dia_chi": "Hà Nội",
                "_doi_chieu_kho_tong_hop": "Ngoài danh sách kho hợp lý",
            }]),
            "customer_vehicle": pd.DataFrame([{
                "_customer_key": "NPP001",
                "_bien_so": "510A12345",
                "_bien_so_hop_le": True,
                "_ngay_only": "2026-06-01",
                "_bien_so_goc": "51A-123.45",
                "_chung_tu": "263.18067094",
                "_ma_kho": "263",
            }]),
            "vehicle_day_shared": pd.DataFrame([{
                "_bien_so": "510A12345",
                "_ngay_only": "2026-06-01",
                "So_NPP": 2,
            }]),
            "vehicle_period_shared": pd.DataFrame([{
                "_bien_so": "510A12345",
                "So_NPP": 2,
                "So_ngay_hoat_dong": 3,
            }]),
            "address_pairs": pd.DataFrame([{
                "_customer_key": "NPP001",
                "_dia_chi": "Số 1 đường A",
                "_dia_chi_norm": "so 1 duong a",
            }]),
            "address_shared": pd.DataFrame([{
                "_dia_chi_norm": "so 1 duong a",
                "So_NPP": 2,
                "Danh_sach_NPP": "Nhà phân phối A | Nhà phân phối B",
            }]),
            "customer_monthly_review": pd.DataFrame([{
                "_customer_key": "NPP001",
                "Mẫu hình": "Giảm mạnh so với kỳ trước",
                "Doanh thu kỳ trước": 1000,
                "Doanh thu kỳ sau": 200,
                "Sản lượng kỳ trước": 100,
                "Sản lượng kỳ sau": 20,
                "Biến động sản lượng %": -80,
            }]),
            "monthly_anomalies": pd.DataFrame([{
                "_customer_key": "NPP001",
                "Tháng bất thường": "2026-06",
                "Loại bất thường": "Sản lượng giảm đột ngột",
                "Sản lượng tháng": 10,
                "Doanh thu tháng": 100,
            }]),
            "product_shift_review": pd.DataFrame([{
                "_customer_key_A": "NPP001",
                "_customer_key_B": "NPP002",
                "Mã hàng": "A001",
                "Vùng": "Miền Bắc",
                "NPP giảm": "Nhà phân phối A",
                "NPP tăng": "Nhà phân phối B",
                "Mức bù trừ tương đối %": 80,
            }]),
        }

        findings = _make_findings(data)
        codes = {item["finding_code"] for item in findings}

        expected = {
            "NPP-WH-01",
            "NPP-VEH-01",
            "NPP-VEH-02",
            "NPP-ADDR-01",
            "NPP-SALES-01",
            "NPP-SHIFT-01",
            "NPP-SALES-02",
        }
        self.assertTrue(expected.issubset(codes), f"Missing codes: {expected - codes}")
        self.assertEqual(len(expected), len(codes))
        self.assertTrue(all(item["customer_key"] == "NPP001" for item in findings))

    def test_data_quality_finding_when_npp_has_no_other_signal(self):
        risk = pd.DataFrame([{
            "Mã khách hàng": "NPP002",
            "NPP": "Nhà phân phối B",
            "Điểm sàng lọc": 0,
            "Mức độ": "Chưa đủ dữ liệu",
            "Độ phủ dữ liệu": 0.25,
            "Dòng kho ngoài danh sách": 0,
            "Dòng xe dùng chung cùng ngày": 0,
            "Dòng xe dùng chung nhiều ngày": 0,
            "Dòng địa chỉ trùng": 0,
            "Biến động kinh doanh cần kiểm tra": False,
            "Liên quan dịch chuyển mặt hàng": False,
            "Số tháng biến động đột ngột": 0,
        }])
        findings = _make_findings({"risk_summary": risk})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["finding_code"], "NPP-DATA-01")
        self.assertEqual(findings[0]["risk_level"], "Chưa đủ dữ liệu")


if __name__ == "__main__":
    unittest.main()
