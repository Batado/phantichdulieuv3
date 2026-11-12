import unittest

import pandas as pd

from modules.scope_filter import apply_business_scope_filter


class ScopeFilterTests(unittest.TestCase):
    def test_excludes_pn_even_when_order_type_is_allowed(self):
        frame = pd.DataFrame([
            {"Số chứng từ": "PN00001", "Loại đơn hàng": "Đơn hàng nội địa"},
            {"Số chứng từ": "  pn00002", "Loại đơn hàng": "Trả hàng hủy HĐ"},
            {"Số chứng từ": "263.00003", "Loại đơn hàng": "Đơn hàng nội địa"},
        ])
        included, excluded = apply_business_scope_filter(
            frame, document_col="Số chứng từ", order_type_col="Loại đơn hàng"
        )
        self.assertEqual(included["Số chứng từ"].tolist(), ["263.00003"])
        self.assertEqual(len(excluded), 2)
        self.assertTrue(excluded["_ly_do_ngoai_pham_vi"].str.startswith("Số chứng từ bắt đầu bằng PN").all())

    def test_keeps_only_four_approved_order_types_normalized(self):
        frame = pd.DataFrame([
            {"Số chứng từ": "263.1", "Loại đơn hàng": "Đơn hàng nội địa"},
            {"Số chứng từ": "263.2", "Loại đơn hàng": "ĐƠN HÀNG NỘI ĐỊA DLPP"},
            {"Số chứng từ": "263.3", "Loại đơn hàng": "Trả hàng hủy HĐ"},
            {"Số chứng từ": "263.4", "Loại đơn hàng": "Trả hàng không hủy HĐ"},
            {"Số chứng từ": "263.5", "Loại đơn hàng": "Đơn hàng xuất khẩu"},
        ])
        included, excluded = apply_business_scope_filter(
            frame, document_col="Số chứng từ", order_type_col="Loại đơn hàng"
        )
        self.assertEqual(len(included), 4)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(
            set(included["_loai_don_hang_chuan_hoa"]),
            {"don hang noi dia", "don hang noi dia dlpp", "tra hang huy hd", "tra hang khong huy hd"},
        )

    def test_missing_required_column_fails_closed(self):
        frame = pd.DataFrame([{"Số chứng từ": "263.1"}])
        with self.assertRaises(ValueError):
            apply_business_scope_filter(frame, document_col="Số chứng từ", order_type_col="Loại đơn hàng")


if __name__ == "__main__":
    unittest.main()
