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


def classify_vehicle_type(value: Any) -> str:
    """Map common ERP labels to the three separate pickup modes."""
    text = norm(value)
    if not text:
        return "Chưa xác định"
    if any(token in text for token in (
        "xe nha may thue ngoai", "nha may thue ngoai", "xe thue ngoai",
        "thue ngoai", "outsourced", "external carrier",
    )):
        return "Xe nhà máy thuê ngoài"
    if any(token in text for token in (
        "xe nha may", "nha may", "xe cong ty", "xe hs", "factory",
    )):
        return "Xe nhà máy"
    if any(token in text for token in (
        "xe khach hang", "xe kh", "xe khach tu lay", "khach hang tu lay",
        "khach tu lay", "khach hang den lay", "khach hang tu den lay",
        "npp tu lay", "customer vehicle", "customer pickup",
    )):
        return "Xe khách hàng"
    return "Chưa xác định"


def classify_customer_vehicle(value: Any) -> bool:
    return classify_vehicle_type(value) == "Xe khách hàng"


def _address_parts(address: Any) -> list[str]:
    return [norm(part) for part in re.split(r"[,;|]", clean(address)) if norm(part)]


def extract_province(address: Any, matrix_keys: set[str]) -> str:
    """Return the explicit province/city in the address before using locality aliases.

    Never report a ward/commune name as the province merely because that ward
    happens to exist in the warehouse matrix. This matters for addresses such
    as 'Phường Tam Thanh, Tỉnh Lạng Sơn'.
    """
    parts = _address_parts(address)
    for part in reversed(parts):
        if part.startswith("tinh "):
            return part[len("tinh "):].strip()
        if part.startswith("thanh pho "):
            return part[len("thanh pho "):].strip()
        if part.startswith("tp "):
            return part[len("tp "):].strip()
    # Older source addresses may omit administrative prefixes.
    for part in reversed(parts):
        if part in matrix_keys:
            return part
    return ""


def resolve_matrix_location(address: Any, matrix_keys: set[str]) -> tuple[str, str, str]:
    """Return (province, matrix_key, match_level) without silently promoting a ward.

    The province/city is authoritative when explicitly present. If it has no
    dedicated matrix row, a matching ward/commune row is retained as a
    provisional locality reference, not treated as a confirmed province rule.
    """
    parts = _address_parts(address)
    province = extract_province(address, matrix_keys)
    if province:
        if province in matrix_keys:
            return province, province, "Tỉnh/thành có dòng riêng trong ma trận"
        for part in reversed(parts):
            if part in matrix_keys:
                return province, part, "Chỉ khớp đơn vị cấp dưới; tỉnh/thành chưa có dòng riêng"
        return province, "", "Tỉnh/thành chưa có trong ma trận"
    for part in reversed(parts):
        if part in matrix_keys:
            return "", part, "Chỉ nhận diện đơn vị cấp dưới; thiếu tỉnh/thành"
    return "", "", "Không nhận diện được tỉnh/thành/địa bàn trong ma trận"


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
    region_col: str = "Miền2",
    locality_col: str = "Khu vưc",
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
    source["_source_region"] = source[region_col].map(clean) if region_col in source.columns else ""
    source["_source_locality"] = source[locality_col].map(clean) if locality_col in source.columns else ""

    def locality_matches_address(row) -> str:
        locality = norm(row["_source_locality"])
        if not locality:
            return "Thiếu Khu vực"
        parts = _address_parts(row["_address"])
        normalized_parts = []
        for part in parts:
            for prefix in ("tinh ", "thanh pho ", "tp "):
                if part.startswith(prefix):
                    part = part[len(prefix):].strip()
                    break
            normalized_parts.append(part)
        return "Khớp thành phần địa chỉ" if locality in normalized_parts else "Không khớp thành phần địa chỉ - cần xác minh"

    source["_locality_address_check"] = source.apply(locality_matches_address, axis=1)
    resolved_locations = source["_address"].map(lambda x: resolve_matrix_location(x, matrix_keys))
    source["_province"] = resolved_locations.map(lambda item: item[0])
    source["_matrix_key"] = resolved_locations.map(lambda item: item[1])
    source["_matrix_match_level"] = resolved_locations.map(lambda item: item[2])
    # Business rule: the actual warehouse code is the first three digits of
    # the document number (e.g. 263.18067094 -> 263). The separate warehouse
    # column is retained as a cross-check, not used to override the document.
    document_codes = source[document_col].fillna("").astype(str).str.extract(
        r"^\s*(\d{3})(?=\.|/|-|\s|$)", expand=False
    ).fillna("")
    source["_column_code"] = source[warehouse_code_col].map(normalize_code)
    source["_actual_code"] = document_codes.where(
        document_codes.ne(""), source["_column_code"]
    )
    source["_document_code_conflict"] = (
        document_codes.ne("") & source["_column_code"].ne("")
        & document_codes.ne(source["_column_code"])
    )

    source["_allowed_codes"] = source["_matrix_key"].map(
        lambda key: ", ".join(sorted(matrix.get(key, set())))
    )
    source["_is_allowed"] = [
        code in matrix.get(matrix_key, set()) if re.fullmatch(r"\d{3}", code or "") else False
        for matrix_key, code in zip(source["_matrix_key"], source["_actual_code"])
    ]

    statuses = np.select(
        [
            source["_province"].eq(""),
            source["_matrix_key"].eq(""),
            source["_matrix_match_level"].ne("Tỉnh/thành có dòng riêng trong ma trận"),
            source["_actual_code"].eq(""),
            ~source["_actual_code"].str.fullmatch(r"\d{3}", na=False),
            source["_actual_code"].isin({"282", "292"}),
            source["_is_allowed"],
        ],
        [
            "Chưa xác định tỉnh/thành từ địa chỉ",
            "Tỉnh/thành chưa có trong ma trận - cần bổ sung",
            "Cần xác minh: tỉnh/thành chưa có dòng riêng; chỉ khớp địa bàn cấp dưới",
            "Thiếu mã kho thực tế",
            "Mã kho đặc biệt/chưa có quy tắc - cần xác minh",
            "Mã kho HS Home (282/292) - cần xác minh riêng",
            "Phù hợp danh mục kho",
        ],
        default="Ngoài danh mục kho hợp lý",
    )
    source["_status"] = statuses
    source.loc[source["_document_code_conflict"], "_status"] = (
        "Mâu thuẫn: mã kho trích từ chứng từ khác cột mã kho"
    )

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
    output["Miền2 theo workbook"] = source["_source_region"]
    output["Khu vực theo workbook"] = source["_source_locality"]
    output["Đối chiếu Khu vực với địa chỉ"] = source["_locality_address_check"]
    output["Đơn vị khớp ma trận"] = source["_matrix_key"]
    output["Cấp độ khớp ma trận"] = source["_matrix_match_level"]
    output["Hình thức lấy hàng"] = source[method_col].map(clean)
    output["Biển số xe"] = source[plate_col].map(clean) if plate_col in source.columns else ""
    output["Mã kho thực tế"] = source["_actual_code"]
    output["Mã kho tại cột dữ liệu"] = source["_column_code"]
    output["Tên kho thực tế"] = source[warehouse_name_col].map(clean) if warehouse_name_col in source.columns else ""
    output["Mã kho được phép"] = source["_allowed_codes"]
    output["Kết quả đối chiếu"] = source["_status"]
    output["Ghi chú gốc"] = notes
    output["Doanh thu"] = pd.to_numeric(source[revenue_col], errors="coerce") if revenue_col in source.columns else np.nan
    output["Số lượng"] = pd.to_numeric(source[quantity_col], errors="coerce") if quantity_col in source.columns else np.nan
    output["Khối lượng"] = pd.to_numeric(source[weight_col], errors="coerce") if weight_col in source.columns else np.nan

    # Consolidate item rows to one customer/document event using groupby
    # reductions rather than a Python loop over every invoice.
    grouped = output.groupby("_event_key", sort=False, dropna=False)
    detail = grouped.first()
    detail["Số dòng hàng"] = grouped.size()
    for metric in ("Doanh thu", "Số lượng", "Khối lượng"):
        detail[metric] = grouped[metric].sum(min_count=1)
    detail["Ghi chú gốc"] = grouped["Ghi chú gốc"].agg(
        lambda values: " | ".join(sorted(set(x for x in values.astype(str) if x.strip())))
    )
    status_count = grouped["Kết quả đối chiếu"].nunique(dropna=True)
    code_count = grouped["Mã kho thực tế"].nunique(dropna=True)
    province_count = grouped["Tỉnh/thành nhận diện"].nunique(dropna=True)
    has_internal_conflict = status_count.gt(1) | code_count.gt(1) | province_count.gt(1)
    detail.loc[has_internal_conflict, "Kết quả đối chiếu"] = (
        "Mâu thuẫn dữ liệu giữa các dòng cùng chứng từ"
    )
    detail = detail.reset_index(drop=True)
    if detail.empty:
        return detail, pd.DataFrame(), pd.DataFrame()

    exception_statuses = {
        "Ngoài danh mục kho hợp lý",
        "Mâu thuẫn: ma trận ngoài danh mục nhưng Ghi chú2 ghi Hợp lý",
        "Mâu thuẫn: ma trận phù hợp nhưng Ghi chú2 ghi Không hợp lý",
        "Mâu thuẫn dữ liệu giữa các dòng cùng chứng từ",
        "Mâu thuẫn: mã kho trích từ chứng từ khác cột mã kho",
    }
    incomplete_prefixes = ("Chưa", "Thiếu", "Mã kho", "Tỉnh/thành", "Cần xác minh")

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
        detail.groupby(["Tỉnh/thành nhận diện", "Miền2 theo workbook", "Tên kho thực tế", "Kết quả đối chiếu"], dropna=False)
        .size().reset_index(name="Số chứng từ")
    )
    return detail, customer_summary, province_summary
