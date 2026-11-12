import unittest

import pandas as pd

from modules.pickup_analysis import (
    analyze_customer_pickups,
    build_warehouse_matrix,
    extract_province,
    parse_code_sequence,
    classify_vehicle_type,
    resolve_matrix_location,
)


class PickupAnalysisTests(unittest.TestCase):
    def test_concatenated_codes_restore_leading_zero(self):
        self.assertEqual(
            parse_code_sequence(53054281284),
            {"053", "054", "281", "284"},
        )


    def test_vehicle_types_are_separated(self):
        self.assertEqual(classify_vehicle_type("Xe khách hàng"), "Xe khách hàng")
        self.assertEqual(classify_vehicle_type("Khách hàng tự lấy"), "Xe khách hàng")
        self.assertEqual(classify_vehicle_type("Xe nhà máy"), "Xe nhà máy")
        self.assertEqual(classify_vehicle_type("Xe nhà máy thuê ngoài"), "Xe nhà máy thuê ngoài")

    def test_document_prefix_is_primary_warehouse_code_and_column_mismatch_is_flagged(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 1, Tỉnh Đắk Lắk, Việt Nam",
            "Mã kho2": 251,
            "Số chứng từ": "284.123",
            "Shipping method": "Xe khách hàng",
            "Kho lấy hàng": "TK PT",
            "Số xe": "47H-12345",
            "Mã khách hàng": "KH10",
            "Tên khách hàng": "NPP D",
            "Ngày chứng từ": "2026-10-01",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đắk Lắk",
            "Kho hợp lý": "Tây Nguyên",
            "Mã kho": 251252263,
        }])
        detail, summary, _ = analyze_customer_pickups(transactions, matrix)
        self.assertEqual(detail.iloc[0]["Mã kho thực tế"], "284")
        self.assertEqual(detail.iloc[0]["Mã kho tại cột dữ liệu"], "251")
        self.assertTrue(detail.iloc[0]["Kết quả đối chiếu"].startswith("Mâu thuẫn"))
        self.assertEqual(summary.iloc[0]["Số_ngoài_danh_mục"], 1)


    def test_explicit_province_is_not_replaced_by_ward_alias(self):
        matrix = pd.DataFrame([
            {"Khu vực/Tỉnh thành": "Phường Tam Thanh", "Kho hợp lý": "Hà Nam, Bình Định", "Mã kho": 261291},
        ])
        rules = build_warehouse_matrix(matrix)
        address = "Số 561, Đường Trần Đăng Ninh, Phường Tam Thanh, Tỉnh Lạng Sơn, Việt Nam"
        self.assertEqual(extract_province(address, set(rules)), "lang son")
        province, matrix_key, level = resolve_matrix_location(address, set(rules))
        self.assertEqual(province, "lang son")
        self.assertEqual(matrix_key, "phuong tam thanh")
        self.assertIn("chưa có dòng riêng", level)

    def test_unmapped_province_is_not_silently_scored_as_outside_or_fit(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 561, Phường Tam Thanh, Tỉnh Lạng Sơn, Việt Nam",
            "Mã kho2": 261,
            "Số chứng từ": "261.123",
            "Shipping method": "Xe khách hàng",
            "Mã khách hàng": "KH-LS",
            "Tên khách hàng": "NPP Lạng Sơn",
            "Ghi chú2": "Hợp lý",
        }])
        matrix = pd.DataFrame([
            {"Khu vực/Tỉnh thành": "Phường Tam Thanh", "Kho hợp lý": "Hà Nam, Bình Định", "Mã kho": 261291},
        ])
        detail, summary, _ = analyze_customer_pickups(transactions, matrix)
        self.assertEqual(detail.iloc[0]["Tỉnh/thành nhận diện"], "lang son")
        self.assertEqual(detail.iloc[0]["Đơn vị khớp ma trận"], "phuong tam thanh")
        self.assertTrue(detail.iloc[0]["Kết quả đối chiếu"].startswith("Cần xác minh"))
        self.assertEqual(summary.iloc[0]["Số_chưa_đủ_dữ_liệu"], 1)
        self.assertEqual(summary.iloc[0]["Số_phù_hợp"], 0)


    def test_khu_vuc_city_prefix_matches_address_without_prefix(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 70, Phường Cái Răng, Thành Phố Cần Thơ, Việt Nam",
            "Khu vưc": "Thành Phố Cần Thơ",
            "Miền2": "Miền Tây (ĐBSCL)",
            "Mã kho2": 281,
            "Số chứng từ": "281.123",
            "Shipping method": "Xe khách hàng",
            "Mã khách hàng": "KH-CT",
            "Tên khách hàng": "NPP Cần Thơ",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Cần Thơ",
            "Kho hợp lý": "HCM, Long An, Cần Thơ, Đồng Nai",
            "Mã kho": 53054281284,
        }])
        detail, _, _ = analyze_customer_pickups(transactions, matrix)
        self.assertEqual(detail.iloc[0]["Đối chiếu Khu vực với địa chỉ"], "Khớp thành phần địa chỉ")
        self.assertEqual(detail.iloc[0]["Miền2 theo workbook"], "Miền Tây (ĐBSCL)")

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

    def test_source_note_conflict_is_not_silently_marked_fit(self):
        transactions = pd.DataFrame([{
            "Địa chỉ": "Số 1, Tỉnh Đắk Lắk, Việt Nam",
            "Mã kho2": 284,
            "Số chứng từ": "284.123",
            "Shipping method": "Xe khách hàng",
            "Kho lấy hàng": "TK PT",
            "Số xe": "47H-12345",
            "Mã khách hàng": "KH02",
            "Tên khách hàng": "NPP B",
            "Ngày chứng từ": "2026-10-01",
            "Ghi chú2": "Hợp lý",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đắk Lắk",
            "Kho hợp lý": "Bình Định, Tây Nguyên, Đà Nẵng",
            "Mã kho": 251252263,
        }])
        detail, summary, _ = analyze_customer_pickups(transactions, matrix)
        self.assertTrue(detail.iloc[0]["Kết quả đối chiếu"].startswith("Mâu thuẫn"))
        self.assertEqual(summary.iloc[0]["Số_ngoài_danh_mục"], 1)

    def test_duplicate_item_lines_count_as_one_document_event(self):
        one = pd.DataFrame([{
            "Địa chỉ": "Số 1, Tỉnh Đắk Lắk, Việt Nam",
            "Mã kho2": 252,
            "Số chứng từ": "252.999",
            "Shipping method": "Xe khách hàng",
            "Kho lấy hàng": "TK Đaklak",
            "Số xe": "47H-12345",
            "Mã khách hàng": "KH03",
            "Tên khách hàng": "NPP C",
            "Ngày chứng từ": "2026-10-01",
            "Ghi chú2": "Hợp lý",
        }])
        transactions = pd.concat([one, one], ignore_index=True)
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đắk Lắk",
            "Kho hợp lý": "Tây Nguyên",
            "Mã kho": 251252263,
        }])
        detail, summary, _ = analyze_customer_pickups(transactions, matrix)
        self.assertEqual(len(detail), 1)
        self.assertEqual(detail.iloc[0]["Số dòng hàng"], 2)
        self.assertEqual(summary.iloc[0]["Số_chứng_từ"], 1)
        self.assertEqual(summary.iloc[0]["Số_phù_hợp"], 1)

    def test_uses_the_passed_warehouse_code_column(self):
        transactions = pd.DataFrame([{
            "Địa chỉ NPP": "Số 1, Tỉnh Đắk Lắk, Việt Nam",
            "Mã kho xuất thực tế": 252,
            "Số chứng từ": "252.321",
            "Hình thức": "Xe khách hàng",
            "Kho tên": "TK Đaklak",
            "Biển số": "47H-12345",
            "Mã KH": "KH09",
            "Tên KH": "NPP custom",
            "Ngày": "2026-10-01",
        }])
        matrix = pd.DataFrame([{
            "Khu vực/Tỉnh thành": "Đắk Lắk",
            "Kho hợp lý": "Tây Nguyên",
            "Mã kho": 251252263,
        }])
        detail, summary, _ = analyze_customer_pickups(
            transactions, matrix,
            address_col="Địa chỉ NPP",
            warehouse_code_col="Mã kho xuất thực tế",
            document_col="Số chứng từ",
            method_col="Hình thức",
            warehouse_name_col="Kho tên",
            plate_col="Biển số",
            customer_id_col="Mã KH",
            customer_name_col="Tên KH",
            date_col="Ngày",
        )
        self.assertEqual(detail.iloc[0]["Mã kho thực tế"], "252")
        self.assertEqual(detail.iloc[0]["Kết quả đối chiếu"], "Phù hợp danh mục kho")


if __name__ == "__main__":
    unittest.main()
