"""Customer-owned vehicle pickup analysis against the workbook's own warehouse matrix."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


def norm(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def normalize_code(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return str(int(float(text))).zfill(3)
    digits = re.sub(r"[^0-9]", "", text)
    return digits.zfill(3) if digits and len(digits) <= 3 else digits


def parse_code_sequence(value: Any) -> set[str]:
    """Parse the concatenated 3-digit codes in the reference sheet.

    Excel stores the reference Mã kho as a number, so a leading zero can be
    removed (e.g. 053054281284 becomes 53054281284). Left-pad to a multiple
    of three before splitting; do not split arbitrary transaction strings.
    """
    text = clean(value)
    if not text:
        return set()
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
    """Read the province/city segment from the end of a Vietnamese address."""
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
    # Some legacy addresses omit the administrative prefix.
    for part in reversed(parts):
        if part in matrix_keys:
            return part
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
    for _, row in reference.iterrows():
        province = norm(row.get(province_col))
        if not province:
            continue
        matrix.setdefault(province, set()).update(parse_code_sequence(row.get(codes_col)))
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
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (detail, customer summary, province summary).

    Only customer-owned vehicles are assessed. Factory and outsourced vehicles
    are deliberately excluded from this first release.
    """
    matrix = build_warehouse_matrix(reference)
    keys = set(matrix)
    rows = []
    for index, row in transactions.iterrows():
        method = clean(row.get(method_col))
        if not classify_customer_vehicle(method):
            continue
        address = clean(row.get(address_col))
        province = extract_province(address, keys)
        actual_code = normalize_code(row.get(warehouse_code_col))
        if not actual_code:
            doc = clean(row.get(document_col))
            match = re.match(r"^(\d{3})(?=\.|/|-|\s|$)", doc)
            actual_code = match.group(1) if match else ""
        allowed = matrix.get(province, set())
        if not province:
            status = "Chưa xác định tỉnh/thành từ địa chỉ"
        elif not actual_code:
            status = "Thiếu mã kho thực tế"
        elif actual_code in allowed:
            status = "Phù hợp danh mục kho"
        else:
            status = "Ngoài danh mục kho hợp lý"
        rows.append({
            "_source_index": index,
            "Ngày chứng từ": row.get("Ngày chứng từ"),
            "Số chứng từ": clean(row.get(document_col)),
            "Mã khách hàng": clean(row.get("Mã khách hàng")),
            "Tên khách hàng": clean(row.get("Tên khách hàng")),
            "Địa chỉ khách hàng": address,
            "Tỉnh/thành nhận diện": province,
            "Hình thức lấy hàng": method,
            "Biển số xe": clean(row.get(plate_col)),
            "Mã kho thực tế": actual_code,
            "Tên kho thực tế": clean(row.get(warehouse_name_col)),
            "Mã kho được phép": ", ".join(sorted(allowed)),
            "Kết quả đối chiếu": status,
            "Ghi chú gốc": clean(row.get("Ghi chú2")),
        })
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, pd.DataFrame(), pd.DataFrame()

    customer_summary = (
        detail.groupby(["Mã khách hàng", "Tên khách hàng"], dropna=False)
        .agg(
            Số_chứng_từ=("Số chứng từ", "nunique"),
            Số_phù_hợp=("Kết quả đối chiếu", lambda s: (s == "Phù hợp danh mục kho").sum()),
            Số_ngoài_danh_mục=("Kết quả đối chiếu", lambda s: (s == "Ngoài danh mục kho hợp lý").sum()),
            Số_chưa_đủ_dữ_liệu=("Kết quả đối chiếu", lambda s: s.str.startswith(("Chưa", "Thiếu")).sum()),
            Số_biển_số=("Biển số xe", lambda s: s.replace("", pd.NA).nunique()),
        )
        .reset_index()
    )
    customer_summary["Tỷ lệ phù hợp (%)"] = (
        customer_summary["Số_phù_hợp"]
        / (customer_summary["Số_phù_hợp"] + customer_summary["Số_ngoài_danh_mục"]).replace(0, pd.NA)
        * 100
    )
    customer_summary["Mức ưu tiên"] = customer_summary.apply(
        lambda r: "Cần xác minh" if r["Số_ngoài_danh_mục"] else (
            "Thiếu dữ liệu" if r["Số_chưa_đủ_dữ_liệu"] else "Chưa thấy lệch theo ma trận"
        ), axis=1
    )
    province_summary = (
        detail.groupby(["Tỉnh/thành nhận diện", "Tên kho thực tế", "Kết quả đối chiếu"], dropna=False)
        .size().reset_index(name="Số chứng từ")
    )
    return detail, customer_summary, province_summary
