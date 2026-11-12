"""Fast, traceable warehouse-pickup screening for customer-owned vehicles."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd


def norm(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def normalize_code(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return str(int(float(text))).zfill(3)
    compact = re.sub(r"[^A-Z0-9]", "", text.upper())
    if compact.isdigit() and len(compact) <= 3:
        return compact.zfill(3)
    return compact


def parse_code_sequence(value: Any) -> set[str]:
    """Parse concatenated 3-digit warehouse codes, preserving leading zeroes."""
    text = clean(value)
    if not text:
        return set()
    if isinstance(value, (int, float)) and not pd.isna(value):
        text = str(int(value))
    elif re.fullmatch(r"\d+\.0+", text):
        text = str(int(float(text)))
    digits = re.sub(r"\D", "", text)
    if not digits:
        return set()
    digits = digits.zfill(((len(digits) + 2) // 3) * 3)
    if len(digits) % 3:
        return set()
    return {digits[i:i + 3] for i in range(0, len(digits), 3)}


def classify_customer_vehicle(value: Any) -> bool:
    text = norm(value)
    return "xe khach hang" in text or text in {"xe khach", "khach hang"}


def extract_province(address: Any, matrix_keys: set[str]) -> str:
    """Resolve the most specific known address segment against the matrix."""
    parts = [norm(x) for x in re.split(r"[,;|]", clean(address)) if norm(x)]
    prefixes = ("tinh ", "thanh pho ", "tp ", "tp.")
    for part in reversed(parts):
        candidate = part
        for prefix in prefixes:
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix):].strip()
                break
        if candidate in matrix_keys:
            return candidate
    for part in reversed(parts):
        if part in matrix_keys:
            return part
    # Address cells sometimes contain the province but omit the administrative prefix.
    for part in reversed(parts):
        for key in matrix_keys:
            if part.endswith(" " + key) or part.startswith(key + " "):
                return key
    return ""


def build_warehouse_matrix(reference: pd.DataFrame) -> dict[str, set[str]]:
    if reference is None or reference.empty:
        return {}
    columns = {norm(c): c for c in reference.columns}
    province_col = columns.get("khu vuc tinh thanh")
    codes_col = columns.get("ma kho")
    if not province_col or not codes_col:
        raise ValueError("Sheet kho lấy hàng phải có cột 'Khu vực/Tỉnh thành' và 'Mã kho'.")
    matrix: dict[str, set[str]] = {}
    for province, code_value in zip(reference[province_col], reference[codes_col]):
        province_key = norm(province)
        if province_key:
            matrix.setdefault(province_key, set()).update(parse_code_sequence(code_value))
    return matrix


def analyze_customer_pickups(
    transactions: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    address_col: str = "Địa chỉ",
    warehouse_code_col: str = "Mã kho2",
    document_col: str = "Số chứng từ",
    method_col: str = "Shipping method",
    warehouse_name_col: str = "Kho lấy hàng",
    plate_col: str = "Số xe",
    customer_id_col: str = "Mã khách hàng",
    customer_name_col: str = "Tên khách hàng",
    date_col: str = "Ngày chứng từ",
    order_type_col: str = "Loại đơn hàng",
    note_col: str = "Ghi chú2",
    revenue_col: str = "Thành tiền bán",
    quantity_col: str = "Số lượng",
    weight_col: str = "Khối lượng",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return event-level detail, customer summary and province/warehouse summary.

    Only customer-owned vehicles are assessed. Calculations are vectorized where
    possible; multi-item invoice lines are consolidated to one event.
    """
    required = [address_col, warehouse_code_col, document_col, method_col]
    missing = [c for c in required if c not in transactions.columns]
    if missing:
        raise ValueError("Thiếu cột phân tích: " + ", ".join(missing))

    matrix = build_warehouse_matrix(reference)
    matrix_keys = set(matrix)
    vehicle_mask = transactions[method_col].map(classify_customer_vehicle)
    source = transactions.loc[vehicle_mask].copy()
    if source.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    source["_address"] = source[address_col].map(clean)
    source["_province"] = source["_address"].map(lambda x: extract_province(x, matrix_keys))
    source["_actual_code"] = source[warehouse_code_col].map(normalize_code)
    missing_code = source["_actual_code"].eq("")
    document_codes = source[document_col].fillna("").astype(str).str.extract(
        r"^\s*(\d{3})(?=\.|/|-|\s|$)", expand=False
    ).fillna("")
    source.loc[missing_code, "_actual_code"] = document_codes.loc[missing_code]

    source["_allowed_codes"] = source["_province"].map(
        lambda p: ", ".join(sorted(matrix.get(p, set())))
    )
    source["_is_allowed"] = [
        code in matrix.get(province, set()) if re.fullmatch(r"\d{3}", code or "") else False
        for province, code in zip(source["_province"], source["_actual_code"])
    ]

    statuses = np.select(
        [
            source["_province"].eq(""),
            source["_actual_code"].eq(""),
            ~source["_actual_code"].str.fullmatch(r"\d{3}", na=False),
            source["_is_allowed"],
        ],
        [
            "Chưa xác định tỉnh/thành từ địa chỉ",
            "Thiếu mã kho thực tế",
            "Mã kho đặc biệt/chưa có quy tắc - cần xác minh",
            "Phù hợp danh mục kho",
        ],
        default="Ngoài danh mục kho hợp lý",
    )
    source["_status"] = statuses

    if note_col in source.columns:
        notes = source[note_col].map(clean)
        note_norm = notes.map(norm)
        matrix_outside_but_note_fit = (
            source["_status"].eq("Ngoài danh mục kho hợp lý")
            & note_norm.str.contains(r"\bhop ly\b", regex=True)
            & ~note_norm.str.contains(r"khong hop ly", regex=False)
        )
        matrix_fit_but_note_outside = (
            source["_status"].eq("Phù hợp danh mục kho")
            & note_norm.str.contains("khong hop ly", regex=False)
        )
        source.loc[matrix_outside_but_note_fit, "_status"] = (
            "Mâu thuẫn: ma trận ngoài danh mục nhưng Ghi chú2 ghi Hợp lý"
        )
        source.loc[matrix_fit_but_note_outside, "_status"] = (
            "Mâu thuẫn: ma trận phù hợp nhưng Ghi chú2 ghi Không hợp lý"
        )
    else:
        notes = pd.Series("", index=source.index)

    customer_ids = source[customer_id_col].map(clean) if customer_id_col in source.columns else pd.Series("", index=source.index)
    customer_names = source[customer_name_col].map(clean) if customer_name_col in source.columns else pd.Series("", index=source.index)
    source["_customer_id"] = customer_ids
    source["_customer_name"] = customer_names
    source["_customer_key"] = customer_ids.where(customer_ids.ne(""), customer_names.map(norm))
    source["_document"] = source[document_col].map(clean)
    source["_event_key"] = source["_customer_key"] + "|" + source["_document"]
    blank_doc = source["_document"].eq("")
    source.loc[blank_doc, "_event_key"] = "ROW|" + source.index[blank_doc].astype(str)

    output = pd.DataFrame(index=source.index)
    output["_source_index"] = source.index
    output["_event_key"] = source["_event_key"]
    output["Ngày chứng từ"] = source[date_col] if date_col in source.columns else ""
    output["Số chứng từ"] = source["_document"]
    output["Loại đơn hàng"] = source[order_type_col] if order_type_col in source.columns else ""
    output["Mã khách hàng"] = source["_customer_id"]
    output["Tên khách hàng"] = source["_customer_name"]
    output["Địa chỉ khách hàng"] = source["_address"]
    output["Tỉnh/thành nhận diện"] = source["_province"]
    output["Hình thức lấy hàng"] = source[method_col].map(clean)
    output["Biển số xe"] = source[plate_col].map(clean) if plate_col in source.columns else ""
    output["Mã kho thực tế"] = source["_actual_code"]
    output["Tên kho thực tế"] = source[warehouse_name_col].map(clean) if warehouse_name_col in source.columns else ""
    output["Mã kho được phép"] = source["_allowed_codes"]
    output["Kết quả đối chiếu"] = source["_status"]
    output["Ghi chú gốc"] = notes
    output["Doanh thu"] = pd.to_numeric(source[revenue_col], errors="coerce") if revenue_col in source.columns else np.nan
    output["Số lượng"] = pd.to_numeric(source[quantity_col], errors="coerce") if quantity_col in source.columns else np.nan
    output["Khối lượng"] = pd.to_numeric(source[weight_col], errors="coerce") if weight_col in source.columns else np.nan

    # Consolidate item rows to a single customer/document event.
    event_records = []
    for event_key, group in output.groupby("_event_key", sort=False, dropna=False):
        first = group.iloc[0].to_dict()
        first["_event_key"] = event_key
        first["Số dòng hàng"] = len(group)
        statuses_in_event = set(group["Kết quả đối chiếu"].dropna().astype(str))
        if len(statuses_in_event) > 1:
            first["Kết quả đối chiếu"] = "Mâu thuẫn dữ liệu giữa các dòng cùng chứng từ"
        first["Doanh thu"] = group["Doanh thu"].sum(min_count=1)
        first["Số lượng"] = group["Số lượng"].sum(min_count=1)
        first["Khối lượng"] = group["Khối lượng"].sum(min_count=1)
        first["Ghi chú gốc"] = " | ".join(sorted(set(x for x in group["Ghi chú gốc"].astype(str) if x.strip())))
        event_records.append(first)
    detail = pd.DataFrame(event_records)
    if detail.empty:
        return detail, pd.DataFrame(), pd.DataFrame()

    exception_statuses = {
        "Ngoài danh mục kho hợp lý",
        "Mâu thuẫn: ma trận ngoài danh mục nhưng Ghi chú2 ghi Hợp lý",
        "Mâu thuẫn: ma trận phù hợp nhưng Ghi chú2 ghi Không hợp lý",
        "Mâu thuẫn dữ liệu giữa các dòng cùng chứng từ",
    }
    incomplete_prefixes = ("Chưa", "Thiếu", "Mã kho")

    grouped = detail.groupby(["Mã khách hàng", "Tên khách hàng"], dropna=False)
    customer_summary = grouped.agg(
        Số_chứng_từ=("Số chứng từ", "nunique"),
        Số_phù_hợp=("Kết quả đối chiếu", lambda s: s.eq("Phù hợp danh mục kho").sum()),
        Số_ngoài_danh_mục=("Kết quả đối chiếu", lambda s: s.isin(exception_statuses).sum()),
        Số_chưa_đủ_dữ_liệu=("Kết quả đối chiếu", lambda s: s.str.startswith(incomplete_prefixes).sum()),
        Số_biển_số=("Biển số xe", lambda s: s[s.astype(str).str.strip().ne("")].nunique()),
        Doanh_thu=("Doanh thu", "sum"),
        Sản_lượng=("Số lượng", "sum"),
        Khối_lượng=("Khối lượng", "sum"),
    ).reset_index()
    denominator = customer_summary["Số_phù_hợp"] + customer_summary["Số_ngoài_danh_mục"]
    customer_summary["Tỷ lệ phù hợp (%)"] = customer_summary["Số_phù_hợp"] / denominator.where(denominator.ne(0)) * 100
    customer_summary["Mức ưu tiên"] = np.select(
        [customer_summary["Số_ngoài_danh_mục"].gt(0), customer_summary["Số_chưa_đủ_dữ_liệu"].gt(0)],
        ["Cần xác minh", "Thiếu dữ liệu"],
        default="Chưa thấy lệch theo ma trận",
    )
    province_summary = (
        detail.groupby(["Tỉnh/thành nhận diện", "Tên kho thực tế", "Kết quả đối chiếu"], dropna=False)
        .size().reset_index(name="Số chứng từ")
    )
    return detail, customer_summary, province_summary
