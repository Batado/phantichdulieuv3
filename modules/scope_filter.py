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


def normalize_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def apply_business_scope_filter(
    frame: pd.DataFrame,
    *,
    document_col: str,
    order_type_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (in_scope, excluded) without mutating the input.

    PN documents are excluded first as warehouse-transfer / warehouse-send
    records, regardless of their order-type label. Remaining rows are kept
    only when their normalized order type is in the four approved categories.
    """
    if document_col not in frame.columns:
        raise ValueError(f"Không tìm thấy cột số chứng từ: {document_col}")
    if order_type_col not in frame.columns:
        raise ValueError(f"Không tìm thấy cột loại đơn hàng: {order_type_col}")

    work = frame.copy()
    documents = work[document_col].fillna("").astype(str).str.strip().str.upper()
    order_types = work[order_type_col].map(normalize_text)

    pn_mask = documents.str.startswith("PN")
    allowed_mask = order_types.isin(ALLOWED_ORDER_TYPES)
    keep_mask = (~pn_mask) & allowed_mask

    work["_loai_don_hang_chuan_hoa"] = order_types
    work["_ly_do_ngoai_pham_vi"] = ""
    work.loc[pn_mask, "_ly_do_ngoai_pham_vi"] = "Số chứng từ bắt đầu bằng PN - hàng gửi kho"
    work.loc[(~pn_mask) & (~allowed_mask), "_ly_do_ngoai_pham_vi"] = (
        "Loại đơn hàng ngoài phạm vi phân tích"
    )

    included = work.loc[keep_mask].copy()
    excluded = work.loc[~keep_mask].copy()
    return included, excluded
