"""Business-scope filtering for NPP transaction workbooks."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd


ALLOWED_ORDER_TYPES = {
    "don hang noi dia",
    "don hang noi dia dlpp",
    "tra hang huy hd",
    "tra hang khong huy hd",
}
ERP_PREFIXES = ("hbmc", "hsn", "hsg")


def normalize_text(value) -> str:
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    return re.sub(r"\\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def strip_erp_prefix(value: str) -> str:
    """Remove known ERP company prefixes separated by punctuation or spaces."""
    text = normalize_text(value)
    for prefix in ERP_PREFIXES:
        if text == prefix:
            return ""
        if text.startswith(prefix + " "):
            return text[len(prefix):].strip()
    return text


def normalize_order_type(value) -> str:
    """Canonicalize labels such as HBMC.DON HANG NOI DIA-DLPP."""
    text = strip_erp_prefix(value)
    for allowed in ALLOWED_ORDER_TYPES:
        if text == allowed or text.endswith(" " + allowed):
            return allowed
    return text


def is_goods_sent_to_warehouse(document_number) -> bool:
    """Treat PN as the leading business prefix, including after known ERP prefixes."""
    text = strip_erp_prefix(document_number)
    return text.startswith("pn")


def apply_business_scope_filter(
    frame: pd.DataFrame,
    *,
    document_col: str,
    order_type_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (in_scope, excluded) without mutating the input.

    PN documents are excluded regardless of order type. Only the four approved
    domestic/return order types are retained. The original values are preserved.
    """
    if document_col not in frame.columns:
        raise ValueError(f"Không tìm thấy cột số chứng từ: {document_col}")
    if order_type_col not in frame.columns:
        raise ValueError(f"Không tìm thấy cột loại đơn hàng: {order_type_col}")

    work = frame.copy()
    pn_mask = work[document_col].map(is_goods_sent_to_warehouse)
    order_types = work[order_type_col].map(normalize_order_type)
    allowed_mask = order_types.isin(ALLOWED_ORDER_TYPES)
    keep_mask = (~pn_mask) & allowed_mask

    work["_loai_don_hang_chuan_hoa"] = order_types
    work["_ly_do_ngoai_pham_vi"] = ""
    work.loc[pn_mask, "_ly_do_ngoai_pham_vi"] = (
        "Số chứng từ bắt đầu bằng PN (kể cả tiền tố ERP) - hàng gửi kho"
    )
    work.loc[(~pn_mask) & (~allowed_mask), "_ly_do_ngoai_pham_vi"] = (
        "Loại đơn hàng ngoài phạm vi phân tích"
    )
    return work.loc[keep_mask].copy(), work.loc[~keep_mask].copy()
