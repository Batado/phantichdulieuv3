import io
import re
import unicodedata
from itertools import combinations
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# HOA SEN GROUP - NPP RISK ANALYTICS REBUILD
# Purpose: operational risk screening for distributors (NPP)
# Does NOT analyze selling price, cost price or profit.
# ============================================================

st.set_page_config(
    page_title="NPP Risk Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------- UI -----------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Be Vietnam Pro',sans-serif;}
[data-testid="stAppViewContainer"] {background:#07111e;}
[data-testid="stHeader"] {background:transparent;}
section[data-testid="stSidebar"] {background:#091626;}
section[data-testid="stSidebar"] * {color:#d4e2f2;}
.main-title {font-size:27px;font-weight:800;color:#e4efff;}
.sub-title {font-size:12px;color:#829ab5;margin-bottom:18px;}
.section-title {
 color:#70aaff;font-size:14px;font-weight:800;
 margin:20px 0 10px;border-left:3px solid #388bfd;padding-left:9px;
}
.risk-green,.risk-yellow,.risk-orange,.risk-red,.risk-gray {
 padding:12px;border-radius:6px;margin:5px 0;
}
.risk-green {background:#102d22;color:#a7f3d0;border-left:4px solid #22c55e;}
.risk-yellow {background:#39320f;color:#fff0a8;border-left:4px solid #eab308;}
.risk-orange {background:#3b2814;color:#ffd199;border-left:4px solid #f97316;}
.risk-red {background:#39191c;color:#ffb5b5;border-left:4px solid #ef4444;}
.risk-gray {background:#182536;color:#cbd5e1;border-left:4px solid #94a3b8;}
</style>
""", unsafe_allow_html=True)

# ----------------------- Business rules ---------------------

DEFAULT_WAREHOUSES = {
    "Miền Nam và Tây Nam Bộ": ["053", "281", "284", "054"],
    "Miền Trung và Tây Nguyên": ["053", "252", "251", "261", "263", "284", "291"],
    "Miền Bắc": ["291", "261"]
}

DEFAULT_REGIONS = {
    "Miền Nam và Tây Nam Bộ": """
Hồ Chí Minh; Thành phố Hồ Chí Minh; TP.HCM; TP HCM; TPHCM; HCMC; Ho Chi Minh City; Sài Gòn; Bình Dương; Bà Rịa Vũng Tàu;
Vũng Tàu; Đồng Nai; Bình Phước; Tây Ninh; Long An; Tiền Giang;
Bến Tre; Trà Vinh; Vĩnh Long; Đồng Tháp; An Giang; Kiên Giang;
Cần Thơ; Hậu Giang; Sóc Trăng; Bạc Liêu; Cà Mau
""",
    "Miền Trung và Tây Nguyên": """
Thanh Hóa; Nghệ An; Hà Tĩnh; Quảng Bình; Quảng Trị; Thừa Thiên Huế;
Huế; Đà Nẵng; Quảng Nam; Quảng Ngãi; Kon Tum; Bình Định; Gia Lai;
Phú Yên; Đắk Lắk; Đắk Nông; Khánh Hòa; Ninh Thuận; Bình Thuận; Lâm Đồng
""",
    "Miền Bắc": """
Hà Nội; Cao Bằng; Tuyên Quang; Hà Giang; Điện Biên; Lai Châu;
Sơn La; Lào Cai; Yên Bái; Thái Nguyên; Bắc Kạn; Lạng Sơn;
Quảng Ninh; Bắc Ninh; Bắc Giang; Phú Thọ; Vĩnh Phúc; Hòa Bình;
Hải Phòng; Hải Dương; Hưng Yên; Thái Bình; Ninh Bình; Hà Nam; Nam Định
"""
}

METHOD_TYPES = ["Xe khách hàng", "Xe nhà máy", "Thuê ngoài", "Khác / Chưa xác định"]
RISK_COLORS = {
    "Thấp": "#22c55e",
    "Theo dõi": "#eab308",
    "Cao": "#f97316",
    "Rất cao": "#ef4444",
    "Chưa đủ dữ liệu": "#94a3b8"
}
RISK_ORDER = ["Thấp", "Theo dõi", "Cao", "Rất cao", "Chưa đủ dữ liệu"]

ALIASES = {
    "customer": ["Tên khách hàng", "Tên KH", "Khách hàng", "Customer", "Customer Name"],
    "customer_id": ["Mã khách hàng", "Mã KH", "Customer Code", "Customer ID"],
    "group": ["Tên nhóm KH", "Mã nhóm KH", "Nhóm khách hàng", "Loại khách hàng", "Loại KH", "Customer Group"],
    "date": ["Ngày chứng từ", "Ngày xuất", "Ngày lấy hàng", "Ngày giao hàng", "Document Date", "Posting Date"],
    "time": ["Giờ chứng từ", "Giờ xuất", "Giờ lấy hàng", "Thời gian xuất", "Time"],
    "document": ["Số chứng từ", "Số CT", "Số phiếu", "Document No", "Invoice No"],
    "revenue": ["Thành tiền bán", "Doanh thu", "Thành tiền", "Sales Amount"],
    "quantity": ["Số lượng", "SL", "Quantity"],
    "weight": ["Khối lượng", "KL", "Trọng lượng", "Weight"],
    "item_code": ["Mã hàng", "Mã SP", "Mã sản phẩm", "Item Code", "SKU"],
    "item_name": ["Tên hàng", "Tên sản phẩm", "Item Name", "Product Name"],
    "address": ["Địa điểm", "Địa điểm khách hàng", "Địa điểm giao hàng", "Địa chỉ khách hàng", "Địa chỉ", "Địa chỉ KH"],
    "warehouse": ["Mã kho", "Mã kho xuất", "Kho xuất", "Kho lấy hàng", "Địa điểm xuất", "Warehouse", "Plant"],
    "method": ["Shipping method", "Hình thức vận chuyển", "Phương thức vận chuyển", "Loại vận chuyển"],
    "vehicle": ["Biển số xe", "Số xe", "Biển kiểm soát", "Vehicle No", "License Plate"],
    "note": ["Ghi chú", "Diễn giải", "Remark", "Notes"],
    "order_type": ["Loại đơn hàng", "Loại giao dịch", "Transaction Type"]
}


# ============================================================
# HELPERS
# ============================================================

def norm(value):
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none", "null") else text


def clean_plate(value):
    text = clean(value).upper()
    text = re.sub(r"[^A-Z0-9]", "", text)
    return "" if text in ("NAN", "NONE", "NULL") else text


def clean_wh(value):
    text = clean(value)
    if not text:
        return ""
    # Numeric Excel values such as 53.0 must become 053.
    m = re.search(r"(?<!\d)(\d{1,3})(?:\.0+)?(?!\d)", text)
    return m.group(1).zfill(3) if m else ""


def parse_num(value):
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        tail = text.split(",")[-1]
        text = text.replace(",", ".") if len(tail) <= 2 else text.replace(",", "")
    try:
        return float(text)
    except Exception:
        return 0.0


def parse_dates(series):
    """Handle Excel serial dates, text serials, Python dates and Vietnamese dates."""
    nums = pd.to_numeric(series, errors="coerce")
    serial_mask = nums.between(20000, 80000)
    out = pd.to_datetime(series, errors="coerce", dayfirst=True)
    if serial_mask.any():
        serial_dates = pd.to_datetime(
            nums.loc[serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce"
        )
        out.loc[serial_mask] = serial_dates
    return out


def split_values(value):
    return [x.strip() for x in re.split(r"[,;\n]+", str(value)) if x.strip()]


def unique_join(series):
    return "; ".join(sorted({clean(x) for x in series if clean(x)}))


def risk_level(score, coverage):
    if coverage < 0.60:
        return "Chưa đủ dữ liệu"
    if score >= 65:
        return "Rất cao"
    if score >= 45:
        return "Cao"
    if score >= 25:
        return "Theo dõi"
    return "Thấp"


def risk_css(level):
    return {
        "Thấp": "risk-green",
        "Theo dõi": "risk-yellow",
        "Cao": "risk-orange",
        "Rất cao": "risk-red",
        "Chưa đủ dữ liệu": "risk-gray"
    }.get(level, "risk-gray")


def detect_col(columns, aliases):
    normalized = {norm(c): c for c in columns}
    for alias in aliases:
        if norm(alias) in normalized:
            return normalized[norm(alias)]
    for alias in aliases:
        key = norm(alias)
        for ncol, original in normalized.items():
            if key and (key == ncol or key in ncol):
                return original
    return None


def make_unique_columns(columns):
    seen, output = {}, []
    for value in columns:
        name = str(value).strip().replace("\n", " ")
        if not name or name.lower() == "nan":
            name = "Column"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        output.append(name)
    return output


# ============================================================
# EXCEL INGESTION: READ ALL SHEETS WITH A VALID HEADER
# ============================================================

def header_score(values):
    normalized = [norm(v) for v in values]
    score = 0
    for key in ("customer", "date", "address", "warehouse", "method"):
        aliases = ALIASES[key]
        if any(
            norm(alias) and any(norm(alias) == v or norm(alias) in v for v in normalized)
            for alias in aliases
        ):
            score += 1
    return score


def read_workbooks(files):
    frames, logs = [], []
    for uploaded in files:
        raw_bytes = uploaded.getvalue()
        try:
            xls = pd.ExcelFile(io.BytesIO(raw_bytes), engine="openpyxl")
        except Exception as exc:
            logs.append(f"{uploaded.name}: Không mở được workbook: {exc}")
            continue

        accepted = 0
        for sheet in xls.sheet_names:
            try:
                preview = pd.read_excel(
                    io.BytesIO(raw_bytes),
                    sheet_name=sheet,
                    header=None,
                    nrows=50,
                    engine="openpyxl"
                )
                if preview.empty:
                    continue

                best_row, best_score = 0, -1
                for i in range(len(preview)):
                    score = header_score(preview.iloc[i].tolist())
                    if score > best_score:
                        best_row, best_score = i, score

                # Require enough column evidence; do not silently load a summary sheet.
                if best_score < 2:
                    logs.append(
                        f"{uploaded.name} / {sheet}: bỏ qua, không nhận diện chắc chắn dòng tiêu đề (điểm {best_score}/5)."
                    )
                    continue

                data = pd.read_excel(
                    io.BytesIO(raw_bytes),
                    sheet_name=sheet,
                    header=best_row,
                    engine="openpyxl"
                )
                data.columns = make_unique_columns(data.columns)
                data = data.dropna(how="all")

                if data.empty:
                    continue

                data["_source_file"] = uploaded.name
                data["_source_sheet"] = sheet
                data["_source_row"] = np.arange(len(data)) + best_row + 2
                frames.append(data)
                accepted += 1

                logs.append(
                    f"{uploaded.name} / {sheet}: đọc {len(data):,} dòng, tiêu đề ở dòng {best_row + 1}, điểm nhận diện {best_score}/5."
                )

            except Exception as exc:
                logs.append(f"{uploaded.name} / {sheet}: lỗi đọc sheet: {exc}")

        if accepted == 0:
            logs.append(f"{uploaded.name}: không có sheet nào đạt điều kiện nhận diện.")

    if not frames:
        return pd.DataFrame(), logs

    # Keep only common columns from selected data sheets.
    return pd.concat(frames, ignore_index=True, sort=False), logs


# ============================================================
# REGION / WAREHOUSE RULES
# ============================================================

def build_region_aliases(region_text):
    result = {}
    for region, text in region_text.items():
        values = {norm(x) for x in split_values(text) if norm(x)}
        result[region] = sorted(values, key=len, reverse=True)
    return result


def detect_region(address, aliases):
    address_norm = norm(address)
    if not address_norm:
        return "Thiếu địa điểm"
    padded = f" {address_norm} "
    matches = []
    for region, names in aliases.items():
        for name in names:
            if f" {name} " in padded:
                matches.append((len(name), region))
    if not matches:
        return "Chưa xác định vùng"
    matches.sort(reverse=True)
    return matches[0][1]


def classify_method(value):
    text = norm(value)
    if any(x in text for x in ("thue ngoai", "xe thue", "outsourced", "nha thau van chuyen")):
        return "Thuê ngoài"
    if any(x in text for x in ("xe nha may", "nha may", "factory")):
        return "Xe nhà máy"
    if any(x in text for x in ("xe khach hang", "khach hang", "khach tu lay", "xe kh", "customer")):
        return "Xe khách hàng"
    return "Khác / Chưa xác định"


def warehouse_status(row, allowed):
    code = row["_warehouse_code"]
    region = row["_region"]
    if not code:
        return "Thiếu mã kho"
    if region == "Thiếu địa điểm":
        return "Thiếu địa điểm"
    if region == "Chưa xác định vùng":
        return "Chưa xác định vùng"
    permitted = allowed.get(region, set())
    if not permitted:
        return "Chưa cấu hình kho"
    return "Trong danh sách" if code in permitted else "Ngoài danh sách"


# ============================================================
# RISK EVIDENCE TABLES
# ============================================================

def build_address_groups(df):
    pairs = df.loc[
        df["_address_norm"].ne(""),
        ["_customer_key", "_customer_name", "_address", "_address_norm"]
    ].drop_duplicates(["_customer_key", "_address_norm"])

    if pairs.empty:
        return pd.DataFrame(), pairs, pd.Series(dtype=float)

    groups = (
        pairs.groupby("_address_norm")
        .agg(
            Dia_diem=("_address", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_join)
        )
        .reset_index()
    )
    groups = groups[groups["So_NPP"] >= 2].sort_values(
        ["So_NPP", "Dia_diem"], ascending=[False, True]
    )

    address_map = groups.set_index("_address_norm")["So_NPP"]
    pairs["_npp_count"] = pairs["_address_norm"].map(address_map).fillna(1)
    customer_map = pairs.groupby("_customer_key")["_npp_count"].max()
    return groups, pairs, customer_map


def build_fuzzy_address_pairs(address_pairs, min_similarity=0.92, max_addresses=1200):
    """Suggest similar but non-identical addresses; never auto-merge them."""
    if address_pairs.empty:
        return pd.DataFrame()

    distinct = (
        address_pairs[["_address_norm", "_address"]]
        .drop_duplicates("_address_norm")
        .reset_index(drop=True)
    )

    if len(distinct) > max_addresses:
        distinct = distinct.head(max_addresses)

    rows = []
    for i in range(len(distinct)):
        a = distinct.loc[i, "_address_norm"]
        if len(a) < 8:
            continue
        for j in range(i + 1, len(distinct)):
            b = distinct.loc[j, "_address_norm"]
            if len(b) < 8:
                continue
            similarity = SequenceMatcher(None, a, b).ratio()
            if similarity >= min_similarity:
                rows.append({
                    "Dia_diem_1": distinct.loc[i, "_address"],
                    "Dia_diem_2": distinct.loc[j, "_address"],
                    "Do_tuong_dong": round(similarity * 100, 1)
                })

    return pd.DataFrame(rows).sort_values(
        "Do_tuong_dong", ascending=False
    ) if rows else pd.DataFrame()


def build_vehicle_tables(car):
    valid = car[car["_plate"].ne("")].copy()
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=float), pd.Series(dtype=float)

    day = (
        valid.groupby(["_plate", "_date_only"])
        .agg(
            Bien_so=("_plate_raw", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_join),
            Danh_sach_chung_tu=("_document", unique_join),
            Danh_sach_kho=("_warehouse_code", unique_join),
            Danh_sach_dia_diem=("_address", unique_join),
            So_dia_diem=("_address_norm", "nunique"),
            So_kho=("_warehouse_code", "nunique"),
            So_giao_dich=("_transaction_key", "nunique"),
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum")
        )
        .reset_index()
    )
    day_shared = day[day["So_NPP"] >= 2].copy()

    period = (
        valid.groupby("_plate")
        .agg(
            Bien_so=("_plate_raw", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_join),
            So_ngay_hoat_dong=("_date_only", "nunique"),
            So_giao_dich=("_transaction_key", "nunique"),
            Danh_sach_dia_diem=("_address", unique_join),
            Danh_sach_kho=("_warehouse_code", unique_join),
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum")
        )
        .reset_index()
    )

    shared_days = (
        day_shared.groupby("_plate")
        .agg(
            So_ngay_dung_chung=("_date_only", "nunique"),
            So_NPP_cao_nhat=("So_NPP", "max")
        )
        .reset_index()
    )

    period = period.merge(shared_days, on="_plate", how="left")
    period["So_ngay_dung_chung"] = period["So_ngay_dung_chung"].fillna(0)
    # Nhóm nhiều ngày: cùng một biển số liên quan từ 2 NPP trở lên
    # và có phát sinh hoạt động trên ít nhất 2 ngày khác nhau.
    period = period[
        (period["So_NPP"] >= 2) &
        (period["So_ngay_hoat_dong"] >= 2)
    ].sort_values(
        ["So_NPP", "So_ngay_hoat_dong"], ascending=False
    )

    day_customer = valid.merge(
        day[["_plate", "_date_only", "So_NPP"]],
        on=["_plate", "_date_only"],
        how="left"
    )
    customer_day_max = day_customer.groupby("_customer_key")["So_NPP"].max()

    repeated_shared_vehicles = period[
        period["So_ngay_dung_chung"].fillna(0) >= 2
    ].copy()
    period_customer = valid.merge(
        repeated_shared_vehicles[["_plate", "So_NPP", "So_ngay_dung_chung"]],
        on="_plate",
        how="inner"
    )
    customer_period_max = period_customer.groupby("_customer_key")["So_NPP"].max()

    return day, day_shared, period, customer_day_max, customer_period_max


def build_link_pairs(address_groups, vehicle_data):
    """Create NPP-to-NPP links supported by shared address or shared plate."""
    links = {}

    def add_link(a, b, reason, evidence):
        if not a or not b or a == b:
            return
        left, right = sorted([a, b])
        key = (left, right)
        links.setdefault(key, {"NPP_1": left, "NPP_2": right, "Dau_hieu": set(), "Bang_chung": []})
        links[key]["Dau_hieu"].add(reason)
        links[key]["Bang_chung"].append(evidence)

    # Address links
    if not address_groups.empty:
        for _, row in address_groups.iterrows():
            names = [x.strip() for x in str(row["Danh_sach_NPP"]).split(";") if x.strip()]
            for a, b in combinations(sorted(set(names)), 2):
                add_link(a, b, "Trùng địa điểm", row["Dia_diem"])

    # Vehicle links: pair actual customer IDs/names for each plate.
    if not vehicle_data.empty:
        for plate, group in vehicle_data.groupby("_plate"):
            names = sorted(group["_customer_name"].dropna().unique().tolist())
            for a, b in combinations(names, 2):
                days = sorted(
                    str(x) for x in group["_date_only"].dropna().unique()
                )
                add_link(
                    a, b, "Dùng chung xe khách hàng",
                    f"Biển số {plate}; ngày có giao dịch: {', '.join(days[:20])}"
                )

    rows = []
    for item in links.values():
        rows.append({
            "NPP_1": item["NPP_1"],
            "NPP_2": item["NPP_2"],
            "Dau_hieu_lien_ket": "; ".join(sorted(item["Dau_hieu"])),
            "Bang_chung": " | ".join(item["Bang_chung"][:10])
        })

    return pd.DataFrame(rows)


# ============================================================
# PAGE START
# ============================================================

st.markdown("""
<div class="main-title">NPP BUSINESS RISK ANALYTICS</div>
<div class="sub-title">HOA SEN GROUP | PHÂN TÍCH HÀNH VI VÀ DẤU HIỆU RỦI RO NHÀ PHÂN PHỐI</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 1. DỮ LIỆU")
    files = st.file_uploader(
        "Tải báo cáo Excel (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True
    )

if not files:
    st.info("Tải báo cáo bán hàng NPP để bắt đầu.")
    st.stop()

RAW, logs = read_workbooks(files)

with st.expander("Nhật ký đọc file và sheet", expanded=True):
    for line in logs:
        st.write(line)

if RAW.empty:
    st.error("Không tìm thấy sheet nào có cấu trúc dữ liệu phù hợp.")
    st.stop()

COLUMNS = RAW.columns.tolist()

# ----------------------- Column mapping ---------------------

def choose_column(label, key, required=False):
    detected = detect_col(COLUMNS, ALIASES[key])
    options = ["-- Không chọn --"] + COLUMNS
    index = options.index(detected) if detected in options else 0
    selected = st.selectbox(
        label, options, index=index, key=f"map_{key}"
    )
    if selected == "-- Không chọn --":
        return None
    return selected


with st.sidebar:
    st.markdown("---")
    st.markdown("## 2. ÁNH XẠ CỘT")

    customer_col = choose_column("Tên khách hàng", "customer", True)
    customer_id_col = choose_column("Mã khách hàng", "customer_id")
    group_col = choose_column("Nhóm khách hàng", "group")
    date_col = choose_column("Ngày chứng từ", "date", True)
    time_col = choose_column("Giờ lấy hàng (nếu có)", "time")
    document_col = choose_column("Số chứng từ", "document")
    address_col = choose_column("Địa điểm (địa chỉ NPP)", "address", True)
    warehouse_col = choose_column("Mã kho / kho xuất", "warehouse", True)
    method_col = choose_column("Hình thức vận chuyển", "method", True)
    vehicle_col = choose_column("Biển số xe", "vehicle")
    revenue_col = choose_column("Doanh thu", "revenue")
    quantity_col = choose_column("Số lượng", "quantity")
    weight_col = choose_column("Khối lượng", "weight")
    item_code_col = choose_column("Mã hàng", "item_code")
    item_name_col = choose_column("Tên hàng", "item_name")
    note_col = choose_column("Ghi chú", "note")
    order_type_col = choose_column("Loại giao dịch", "order_type")

required = [customer_col, date_col, address_col, warehouse_col, method_col]
if any(x is None for x in required):
    st.error("Chọn tối thiểu Tên khách hàng, Ngày chứng từ, Địa điểm, Mã kho và Hình thức vận chuyển.")
    st.stop()

# ----------------------- Filter NPP -------------------------

BASE = RAW.copy()

if group_col:
    group_values = sorted(
        BASE[group_col].dropna().astype(str).str.strip().unique().tolist()
    )
    suggested = [
        x for x in group_values
        if "npp" in norm(x) or "nha phan phoi" in norm(x)
    ]

    with st.sidebar:
        st.markdown("---")
        st.markdown("## 3. PHẠM VI NPP")
        st.caption(f"Cột nhóm đang dùng: {group_col}")
        selected_groups = st.multiselect(
            "Chọn giá trị nhóm khách hàng là NPP",
            options=group_values,
            default=suggested,
            help="Chọn đúng mã/nhóm NPP theo danh mục khách hàng của công ty."
        )
        confirm_all_npp = st.checkbox(
            "File này đã được lọc chỉ còn khách hàng NPP",
            value=False,
            help="Chỉ tích nếu bạn chắc chắn toàn bộ dòng trong file đều là NPP."
        )

    if selected_groups:
        BASE = BASE[
            BASE[group_col].astype(str).str.strip().isin(selected_groups)
        ].copy()
    elif confirm_all_npp:
        # Explicit user confirmation; do not silently classify every customer as NPP.
        BASE = BASE.copy()
        st.info(
            f"Đã xác nhận file chỉ gồm NPP. Hệ thống phân tích {len(BASE):,} dòng "
            f"theo cột nhóm '{group_col}'."
        )
    else:
        st.warning(
            "Chưa xác định phạm vi NPP. Ở thanh bên trái, hãy chọn giá trị nhóm NPP "
            "hoặc tích xác nhận file chỉ chứa NPP. Hệ thống chưa chạy phân tích để "
            "tránh đưa khách hàng khác loại vào kết quả."
        )
        st.dataframe(
            pd.DataFrame({
                "Giá trị nhóm tìm thấy trong file": group_values
            }),
            use_container_width=True,
            hide_index=True
        )
        st.stop()
else:
    with st.sidebar:
        only_npp = st.checkbox(
            "Xác nhận file chỉ có khách hàng NPP",
            value=False,
            help="Tích nếu báo cáo Excel đã được lọc riêng khách hàng Nhà phân phối."
        )
    if not only_npp:
        st.warning(
            "Không ánh xạ được cột nhóm khách hàng. Hãy ánh xạ đúng cột nhóm "
            "hoặc xác nhận file chỉ chứa NPP."
        )
        st.stop()

if BASE.empty:
    st.warning("Không còn dòng dữ liệu thuộc nhóm NPP đã chọn.")
    st.stop()

# ----------------------- Exclusions -------------------------

removed_z = 0
removed_discount = 0
removed_return = 0

if item_code_col:
    code = BASE[item_code_col].fillna("").astype(str).str.strip()
    mask = code.str.upper().str.startswith("Z", na=False)
    removed_z = int(mask.sum())
    BASE = BASE[~mask].copy()

if item_name_col:
    mask = BASE[item_name_col].apply(norm).str.contains("chiet khau", na=False)
    removed_discount = int(mask.sum())
    BASE = BASE[~mask].copy()

note_norm = BASE[note_col].apply(norm) if note_col else pd.Series("", index=BASE.index)
type_norm = BASE[order_type_col].apply(norm) if order_type_col else pd.Series("", index=BASE.index)

return_mask = (
    note_norm.str.contains(r"nhap tra|tra hang|huy hoa don", regex=True, na=False)
    | type_norm.str.contains(r"tra hang|huy hd|nhap tra", regex=True, na=False)
)
if revenue_col:
    return_mask |= BASE[revenue_col].apply(parse_num) < 0
if quantity_col:
    return_mask |= BASE[quantity_col].apply(parse_num) < 0

with st.sidebar:
    exclude_returns = st.checkbox("Loại dòng trả hàng / hủy / số âm", value=True)

if exclude_returns:
    removed_return = int(return_mask.sum())
    BASE = BASE[~return_mask].copy()

if BASE.empty:
    st.error("Không còn dữ liệu sau khi loại mã hàng Z, chiết khấu và giao dịch trả/hủy.")
    st.stop()

# ----------------------- Normalize -------------------------

DF = BASE.copy()
DF["_customer_name"] = DF[customer_col].apply(clean)

if customer_id_col:
    DF["_customer_id"] = DF[customer_id_col].apply(clean)
    DF["_customer_key"] = np.where(
        DF["_customer_id"].ne(""),
        "ID:" + DF["_customer_id"],
        "NAME:" + DF["_customer_name"].apply(norm)
    )
else:
    DF["_customer_key"] = "NAME:" + DF["_customer_name"].apply(norm)

DF["_date"] = parse_dates(DF[date_col])
DF = DF[DF["_date"].notna() & DF["_customer_name"].ne("")].copy()

if DF.empty:
    st.error("Không đọc được ngày chứng từ hợp lệ. Kiểm tra kiểu ngày và cột ngày.")
    st.stop()

DF["_date_only"] = DF["_date"].dt.date
DF["_month"] = DF["_date"].dt.to_period("M").astype(str)

DF["_address"] = DF[address_col].apply(clean)
DF["_address_norm"] = DF["_address"].apply(norm)
DF["_warehouse_raw"] = DF[warehouse_col].apply(clean)
DF["_warehouse_code"] = DF["_warehouse_raw"].apply(clean_wh)
DF["_method"] = DF[method_col].apply(clean)
DF["_plate_raw"] = DF[vehicle_col].apply(clean) if vehicle_col else ""
DF["_plate"] = DF["_plate_raw"].apply(clean_plate) if vehicle_col else ""

DF["_revenue"] = DF[revenue_col].apply(parse_num) if revenue_col else 0.0
DF["_quantity"] = DF[quantity_col].apply(parse_num) if quantity_col else 0.0
DF["_weight"] = DF[weight_col].apply(parse_num) if weight_col else 0.0
DF["_document"] = DF[document_col].apply(clean) if document_col else ""
DF["_row_id"] = np.arange(len(DF))
DF["_transaction_key"] = np.where(
    DF["_document"].ne(""),
    DF["_customer_key"].astype(str) + "|" + DF["_document"].astype(str),
    "ROW:" + DF["_row_id"].astype(str)
)

# Optional pickup time supports same-day sequencing only if the column exists.
if time_col:
    DF["_time"] = DF[time_col].apply(clean)
else:
    DF["_time"] = ""

# ----------------------- Vehicle method classification -----

methods = sorted(DF["_method"].dropna().unique())

method_cfg = pd.DataFrame({
    "Hình thức vận chuyển": methods,
    "Phân loại": [
        classify_method(x) for x in methods
    ]
})

st.markdown('<div class="section-title">4. KIỂM TRA PHÂN LOẠI XE</div>', unsafe_allow_html=True)
st.caption("Chỉ dòng được phân loại là Xe khách hàng mới tham gia phân tích xe và kho.")
method_cfg = st.data_editor(
    method_cfg,
    use_container_width=True,
    hide_index=True,
    disabled=["Hình thức vận chuyển"],
    column_config={
        "Phân loại": st.column_config.SelectboxColumn(
            "Phân loại", options=METHOD_TYPES, required=True
        )
    },
    key="method_classification"
)

method_map = dict(zip(method_cfg["Hình thức vận chuyển"], method_cfg["Phân loại"]))
DF["_vehicle_type"] = DF["_method"].map(method_map).fillna("Khác / Chưa xác định")

CUSTOMER_CAR_ALL = DF[DF["_vehicle_type"] == "Xe khách hàng"].copy()
FACTORY_ROWS = DF[DF["_vehicle_type"] == "Xe nhà máy"].copy()
OUTSOURCE_ROWS = DF[DF["_vehicle_type"] == "Thuê ngoài"].copy()
UNKNOWN_METHOD_ROWS = DF[DF["_vehicle_type"] == "Khác / Chưa xác định"].copy()

# ----------------------- Region and warehouse setup ---------

with st.sidebar:
    st.markdown("---")
    st.markdown("## 5. CẤU HÌNH VÙNG VÀ KHO")
    region_text = {}
    for region, default in DEFAULT_REGIONS.items():
        region_text[region] = st.text_area(
            f"Tỉnh/thành thuộc {region}",
            value=default.strip(),
            height=95,
            key=f"regions_{region}"
        )

    warehouse_text = {}
    for region, codes in DEFAULT_WAREHOUSES.items():
        warehouse_text[region] = st.text_input(
            f"Mã kho cho {region}",
            value=", ".join(codes),
            key=f"warehouses_{region}"
        )

region_aliases = build_region_aliases(region_text)
allowed_warehouses = {
    region: {clean_wh(x) for x in split_values(value) if clean_wh(x)}
    for region, value in warehouse_text.items()
}

DF["_region"] = DF["_address"].apply(lambda x: detect_region(x, region_aliases))
CUSTOMER_CAR_ALL["_region"] = CUSTOMER_CAR_ALL["_address"].apply(
    lambda x: detect_region(x, region_aliases)
)
CUSTOMER_CAR_ALL["_warehouse_status"] = CUSTOMER_CAR_ALL.apply(
    lambda row: warehouse_status(row, allowed_warehouses),
    axis=1
)

# ----------------------- Date filters -----------------------

with st.sidebar:
    st.markdown("---")
    st.markdown("## 6. BỘ LỌC")
    min_date = DF["_date"].min().date()
    max_date = DF["_date"].max().date()
    date_range = st.date_input("Khoảng thời gian", value=(min_date, max_date))
    min_daily_docs = st.number_input(
        "Số chứng từ/ngày cần chú ý",
        min_value=2, max_value=100, value=5
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

DF = DF[
    (DF["_date"].dt.date >= start_date)
    & (DF["_date"].dt.date <= end_date)
].copy()

CUSTOMER_CAR = CUSTOMER_CAR_ALL[
    (CUSTOMER_CAR_ALL["_date"].dt.date >= start_date)
    & (CUSTOMER_CAR_ALL["_date"].dt.date <= end_date)
].copy()

if DF.empty:
    st.warning("Không có giao dịch trong khoảng thời gian đã chọn.")
    st.stop()

# ----------------------- Address checks ----------------------

ADDRESS_GROUP, ADDRESS_PAIRS, ADDRESS_MAP = build_address_groups(DF)
FUZZY_ADDRESS = build_fuzzy_address_pairs(ADDRESS_PAIRS)

# ----------------------- Vehicle checks ----------------------

VEHICLE_DATA = CUSTOMER_CAR[CUSTOMER_CAR["_plate"].ne("")].copy()
VEHICLE_DAY_ALL, VEHICLE_DAY_SHARED, VEHICLE_PERIOD, VEHICLE_DAY_MAP, VEHICLE_PERIOD_MAP = build_vehicle_tables(VEHICLE_DATA)

# Missing plates are tracked separately, not silently discarded.
MISSING_PLATE = CUSTOMER_CAR[CUSTOMER_CAR["_plate"].eq("")].copy()

# ----------------------- Warehouse evidence ------------------

WH_STATUS_COUNTS = (
    CUSTOMER_CAR["_warehouse_status"].value_counts().rename_axis("Trang_thai").reset_index(name="So_giao_dich")
    if not CUSTOMER_CAR.empty else pd.DataFrame(columns=["Trang_thai", "So_giao_dich"])
)

WH_EVIDENCE = CUSTOMER_CAR[
    CUSTOMER_CAR["_warehouse_status"] == "Ngoài danh sách"
].copy()

WH_UNKNOWN = CUSTOMER_CAR[
    CUSTOMER_CAR["_warehouse_status"].isin([
        "Thiếu mã kho", "Thiếu địa điểm",
        "Chưa xác định vùng", "Chưa cấu hình kho"
    ])
].copy()

# ----------------------- Multiple warehouses same day --------

if not CUSTOMER_CAR.empty:
    MULTI_WH = (
        CUSTOMER_CAR[CUSTOMER_CAR["_warehouse_code"].ne("")]
        .groupby(["_customer_key", "_date_only"])
        .agg(
            NPP=("_customer_name", "first"),
            So_kho=("_warehouse_code", "nunique"),
            Danh_sach_kho=("_warehouse_code", unique_join),
            Danh_sach_bien_so=("_plate_raw", unique_join),
            So_chung_tu=("_document", "nunique"),
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum")
        )
        .reset_index()
    )
    MULTI_WH = MULTI_WH[MULTI_WH["So_kho"] >= 2].copy()
else:
    MULTI_WH = pd.DataFrame()

# ----------------------- Daily frequency ---------------------

if not CUSTOMER_CAR.empty:
    if document_col:
        DAILY = (
            CUSTOMER_CAR.groupby(["_customer_key", "_customer_name", "_date_only"])
            ["_transaction_key"].nunique().reset_index(name="So_chung_tu")
        )
    else:
        DAILY = (
            CUSTOMER_CAR.groupby(["_customer_key", "_customer_name", "_date_only"])
            .size().reset_index(name="So_chung_tu")
        )
else:
    DAILY = pd.DataFrame()

# ----------------------- Duplicate records -------------------

duplicate_keys = ["_customer_key", "_date_only"]
if document_col:
    duplicate_keys.append("_document")
if item_code_col:
    duplicate_keys.append(item_code_col)
if quantity_col:
    duplicate_keys.append("_quantity")
duplicate_keys += ["_warehouse_code", "_plate"]

if len(duplicate_keys) >= 3:
    DUPLICATE_ROWS = DF[
        DF.duplicated(subset=duplicate_keys, keep=False)
    ].copy()
else:
    DUPLICATE_ROWS = DF.iloc[0:0].copy()

# ----------------------- Monthly volume anomaly ---------------

MONTHLY = (
    DF.groupby(["_customer_key", "_month"])
    .agg(
        Doanh_thu=("_revenue", "sum"),
        San_luong=("_quantity", "sum"),
        Khoi_luong=("_weight", "sum"),
        So_giao_dich=("_customer_name", "size")
    )
    .reset_index()
)

SPIKE_ROWS = []
SPIKE_KEYS = set()

for key, group in MONTHLY.groupby("_customer_key"):
    group = group.sort_values("_month").reset_index(drop=True)
    if len(group) < 4:
        continue
    for i in range(3, len(group)):
        history = group.loc[max(0, i - 6):i - 1, "San_luong"]
        baseline = history.median()
        current = group.loc[i, "San_luong"]
        if baseline > 0 and current >= 3 * baseline:
            SPIKE_KEYS.add(key)
            SPIKE_ROWS.append({
                "Ma_NPP": key,
                "Thang": group.loc[i, "_month"],
                "San_luong_thang": current,
                "Trung_vi_6_thang_truoc": baseline,
                "So_lan_tang": round(current / baseline, 2)
            })

SPIKE_TABLE = pd.DataFrame(SPIKE_ROWS)

# ----------------------- Per-customer summary -----------------

CUSTOMER = (
    DF.groupby("_customer_key")
    .agg(
        NPP=("_customer_name", "first"),
        Doanh_thu=("_revenue", "sum"),
        San_luong=("_quantity", "sum"),
        Khoi_luong=("_weight", "sum"),
        So_giao_dich=("_customer_name", "size"),
        So_ngay_mua=("_date_only", "nunique"),
        Dia_diem=("_address", "first"),
        Ti_le_thieu_dia_diem=("_address_norm", lambda x: (x == "").mean())
    )
    .reset_index()
)

CUSTOMER["So_NPP_cung_dia_diem"] = CUSTOMER["_customer_key"].map(ADDRESS_MAP).fillna(1)
CUSTOMER["Max_NPP_cung_xe_cung_ngay"] = CUSTOMER["_customer_key"].map(VEHICLE_DAY_MAP).fillna(1)
CUSTOMER["Max_NPP_cung_xe_trong_ky"] = CUSTOMER["_customer_key"].map(VEHICLE_PERIOD_MAP).fillna(1)

if not MULTI_WH.empty:
    multi_wh_map = MULTI_WH.groupby("_customer_key")["So_kho"].max()
    CUSTOMER["Max_kho_cung_ngay"] = CUSTOMER["_customer_key"].map(multi_wh_map).fillna(1)
else:
    CUSTOMER["Max_kho_cung_ngay"] = 1

if not DAILY.empty:
    daily_max_map = DAILY.groupby("_customer_key")["So_chung_tu"].max()
    CUSTOMER["Max_chung_tu_ngay"] = CUSTOMER["_customer_key"].map(daily_max_map).fillna(0)
else:
    CUSTOMER["Max_chung_tu_ngay"] = 0

if not DUPLICATE_ROWS.empty:
    duplicate_map = DUPLICATE_ROWS.groupby("_customer_key").size()
    CUSTOMER["So_dong_nghi_trung"] = CUSTOMER["_customer_key"].map(duplicate_map).fillna(0)
else:
    CUSTOMER["So_dong_nghi_trung"] = 0

CUSTOMER["Dot_bien_san_luong"] = CUSTOMER["_customer_key"].isin(SPIKE_KEYS)

# Warehouse statistics apply only to customer vehicles.
if not CUSTOMER_CAR.empty:
    wh_customer = (
        CUSTOMER_CAR.groupby("_customer_key")
        .agg(
            So_dong_xe_kh=("_customer_name", "size"),
            So_kho_ngoai=(" _warehouse_status".strip(), lambda x: (x == "Ngoài danh sách").sum()),
            So_kho_trong=("_warehouse_status", lambda x: (x == "Trong danh sách").sum()),
            So_kho_thieu=("_warehouse_status", lambda x: (x == "Thiếu mã kho").sum()),
            So_dong_thieu_bien_so=("_plate", lambda x: (x == "").sum())
        )
        .reset_index()
    )
    CUSTOMER = CUSTOMER.merge(wh_customer, on="_customer_key", how="left")
else:
    for col in ["So_dong_xe_kh", "So_kho_ngoai", "So_kho_trong", "So_kho_thieu", "So_dong_thieu_bien_so"]:
        CUSTOMER[col] = 0

for col in ["So_dong_xe_kh", "So_kho_ngoai", "So_kho_trong", "So_kho_thieu", "So_dong_thieu_bien_so"]:
    CUSTOMER[col] = CUSTOMER[col].fillna(0)

CUSTOMER["Ti_le_kho_ngoai"] = (
    CUSTOMER["So_kho_ngoai"] /
    (CUSTOMER["So_kho_ngoai"] + CUSTOMER["So_kho_trong"]).replace(0, np.nan)
).fillna(0)

# ----------------------- Scoring with coverage ---------------

def s_warehouse(row):
    denominator = row["So_kho_ngoai"] + row["So_kho_trong"]
    if denominator == 0:
        return 0
    ratio = row["Ti_le_kho_ngoai"]
    if ratio >= .50:
        return 20
    if ratio >= .20:
        return 14
    if ratio > 0:
        return 8
    return 0


def s_address(n):
    return 15 if n >= 4 else 12 if n == 3 else 8 if n == 2 else 0


def s_same_day(n):
    return 20 if n >= 4 else 16 if n == 3 else 10 if n == 2 else 0


def s_shared_period(n):
    return 15 if n >= 4 else 12 if n == 3 else 8 if n == 2 else 0


def s_multi_wh(n):
    return 8 if n >= 3 else 5 if n == 2 else 0


CUSTOMER["Diem_kho"] = CUSTOMER.apply(s_warehouse, axis=1)
CUSTOMER["Diem_dia_diem"] = CUSTOMER["So_NPP_cung_dia_diem"].apply(s_address)
CUSTOMER["Diem_xe_cung_ngay"] = CUSTOMER["Max_NPP_cung_xe_cung_ngay"].apply(s_same_day)
CUSTOMER["Diem_xe_trong_ky"] = CUSTOMER["Max_NPP_cung_xe_trong_ky"].apply(s_shared_period)
CUSTOMER["Diem_nhieu_kho"] = CUSTOMER["Max_kho_cung_ngay"].apply(s_multi_wh)
CUSTOMER["Diem_tan_suat"] = np.where(
    CUSTOMER["Max_chung_tu_ngay"] >= 2 * min_daily_docs,
    5,
    np.where(CUSTOMER["Max_chung_tu_ngay"] >= min_daily_docs, 3, 0)
)
CUSTOMER["Diem_san_luong"] = np.where(CUSTOMER["Dot_bien_san_luong"], 5, 0)
CUSTOMER["Diem_trung_du_lieu"] = np.where(
    CUSTOMER["So_dong_nghi_trung"] >= 5,
    4,
    np.where(CUSTOMER["So_dong_nghi_trung"] > 0, 2, 0)
)
CUSTOMER["Diem_thieu_dia_diem"] = np.where(
    CUSTOMER["Ti_le_thieu_dia_diem"] >= .25, 3, 0
)

# Vehicle / warehouse missing information is a data-quality indicator.
CUSTOMER["Diem_thieu_bien_so"] = np.where(
    (CUSTOMER["So_dong_xe_kh"] > 0) &
    (CUSTOMER["So_dong_thieu_bien_so"] / CUSTOMER["So_dong_xe_kh"] >= .25),
    5, 0
)

SCORE_COLS = [
    "Diem_kho", "Diem_dia_diem", "Diem_xe_cung_ngay",
    "Diem_xe_trong_ky", "Diem_nhieu_kho", "Diem_tan_suat",
    "Diem_san_luong", "Diem_trung_du_lieu",
    "Diem_thieu_dia_diem", "Diem_thieu_bien_so"
]

# Sum max is 100.
CUSTOMER["Tong_diem"] = CUSTOMER[SCORE_COLS].sum(axis=1).clip(0, 100)

# Coverage: count checks for which evidence is actually available.
coverage_checks = pd.DataFrame(index=CUSTOMER.index)
coverage_checks["address"] = CUSTOMER["Dia_diem"].fillna("").astype(str).str.strip().ne("")
coverage_checks["vehicle_method"] = CUSTOMER["So_dong_xe_kh"] > 0
coverage_checks["warehouse_check"] = (
    CUSTOMER["So_kho_ngoai"] + CUSTOMER["So_kho_trong"] > 0
)
coverage_checks["daily_data"] = CUSTOMER["So_ngay_mua"] > 0
coverage_checks["quantity_data"] = CUSTOMER["San_luong"] > 0
coverage_checks["document_data"] = CUSTOMER["So_giao_dich"] > 0

CUSTOMER["Do_phu_du_lieu"] = coverage_checks.mean(axis=1)
# Kho/xe là hai trường kiểm soát cốt lõi trong yêu cầu NPP.
# Nếu không có dòng xe khách hàng hoặc không có giao dịch đối chiếu kho,
# không được xếp NPP vào nhóm xanh chỉ vì dữ liệu còn lại không có cảnh báo.
CUSTOMER["_du_dieu_kien_kho_xe"] = (
    (CUSTOMER["So_dong_xe_kh"] > 0) &
    ((CUSTOMER["So_kho_ngoai"] + CUSTOMER["So_kho_trong"]) > 0)
)
CUSTOMER["Muc_do"] = [
    (
        "Chưa đủ dữ liệu"
        if not bool(critical) or coverage < 0.75
        else risk_level(score, coverage)
    )
    for score, coverage, critical in zip(
        CUSTOMER["Tong_diem"],
        CUSTOMER["Do_phu_du_lieu"],
        CUSTOMER["_du_dieu_kien_kho_xe"]
    )
]

# ----------------------- Per-NPP narrative -------------------

def make_reasons(row):
    items = []
    if row["Diem_kho"]:
        items.append(
            f"Kho: {int(row['So_kho_ngoai'])} giao dịch xe khách hàng dùng mã kho ngoài danh sách vùng "
            f"(tỷ lệ {row['Ti_le_kho_ngoai']:.0%} trên giao dịch xác định được kho)."
        )
    if row["Diem_dia_diem"]:
        items.append(
            f"Địa điểm: có {int(row['So_NPP_cung_dia_diem'])} NPP cùng địa điểm sau chuẩn hóa."
        )
    if row["Diem_xe_cung_ngay"]:
        items.append(
            f"Xe: một biển số phục vụ tối đa {int(row['Max_NPP_cung_xe_cung_ngay'])} NPP trong cùng ngày."
        )
    if row["Diem_xe_trong_ky"]:
        items.append(
            f"Xe: một biển số liên quan tối đa {int(row['Max_NPP_cung_xe_trong_ky'])} NPP trong kỳ."
        )
    if row["Diem_nhieu_kho"]:
        items.append(
            f"Kho: NPP có ngày lấy hàng tại {int(row['Max_kho_cung_ngay'])} mã kho khác nhau."
        )
    if row["Diem_tan_suat"]:
        items.append(
            f"Tần suất: cao nhất {int(row['Max_chung_tu_ngay'])} chứng từ/ngày."
        )
    if row["Diem_san_luong"]:
        items.append("Sản lượng: có tháng tăng từ 3 lần trung vị các tháng trước.")
    if row["Diem_trung_du_lieu"]:
        items.append(f"Dữ liệu: {int(row['So_dong_nghi_trung'])} dòng có dấu hiệu trùng.")
    if row["Diem_thieu_dia_diem"]:
        items.append(f"Địa điểm: thiếu ở {row['Ti_le_thieu_dia_diem']:.0%} số dòng.")
    if row["Diem_thieu_bien_so"]:
        items.append(
            f"Phương tiện: thiếu biển số ở {int(row['So_dong_thieu_bien_so'])} "
            "dòng xe khách hàng."
        )
    if not items:
        return "Trong phạm vi dữ liệu hiện có chưa phát hiện dấu hiệu vượt ngưỡng."
    return " ".join(items)


def make_actions(row):
    actions = []
    if row["Diem_kho"]:
        actions.append("Đối chiếu phiếu xuất kho, xác minh lý do lấy hàng ngoài danh sách và kiểm tra phê duyệt ngoại lệ.")
    if row["Diem_dia_diem"]:
        actions.append("Đối chiếu hồ sơ đăng ký kinh doanh, địa chỉ thực tế, người đại diện và thông tin liên hệ các NPP cùng địa điểm.")
    if row["Diem_xe_cung_ngay"] or row["Diem_xe_trong_ky"]:
        actions.append("Xác minh chủ xe, người lái, người nhận hàng, chứng từ và thỏa thuận dùng chung phương tiện.")
    if row["Diem_nhieu_kho"]:
        actions.append("Kiểm tra lý do một NPP lấy hàng tại nhiều kho trong cùng ngày và phê duyệt điều phối.")
    if row["Diem_tan_suat"]:
        actions.append("Kiểm tra việc chia nhỏ đơn, số lần xuất kho, nhu cầu nhận hàng và mục đích từng chứng từ.")
    if row["Diem_san_luong"]:
        actions.append("Đối chiếu đơn đặt hàng, tồn kho đầu/cuối kỳ, giao nhận và khả năng tiêu thụ.")
    if row["Diem_trung_du_lieu"]:
        actions.append("Đối chiếu chứng từ gốc và từng dòng hàng để phân biệt trùng dữ liệu với nhiều dòng hàng hợp lệ.")
    if row["Diem_thieu_dia_diem"] or row["Diem_thieu_bien_so"]:
        actions.append("Yêu cầu đơn vị kinh doanh bổ sung hồ sơ địa điểm và thông tin phương tiện còn thiếu.")
    if row["Muc_do"] == "Chưa đủ dữ liệu":
        actions.append("Bổ sung dữ liệu trước khi kết luận mức rủi ro; không xếp NPP vào nhóm an toàn chỉ vì thiếu bằng chứng.")
    if not actions:
        return "Duy trì giám sát định kỳ và kiểm tra chọn mẫu."
    return " ".join(actions)


CUSTOMER["Nhan_dinh"] = CUSTOMER.apply(make_reasons, axis=1)
CUSTOMER["Giai_phap"] = CUSTOMER.apply(make_actions, axis=1)
CUSTOMER = CUSTOMER.sort_values(["Tong_diem", "Do_phu_du_lieu"], ascending=[False, True])

# ----------------------- NPP-to-NPP network ------------------

ADDRESS_GROUP_FOR_LINK = ADDRESS_GROUP.copy()
LINKS = build_link_pairs(ADDRESS_GROUP_FOR_LINK, VEHICLE_DATA)

# ----------------------- Daily high-frequency events ----------

if not DAILY.empty:
    DAILY_ALERT = DAILY[DAILY["So_chung_tu"] >= min_daily_docs].copy()
else:
    DAILY_ALERT = pd.DataFrame()

# ----------------------- Product summary ----------------------

product_col = item_name_col or item_code_col

if product_col:
    PRODUCT = (
        DF.groupby(product_col)
        .agg(
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum"),
            So_NPP=("_customer_key", "nunique"),
            So_giao_dich=("_customer_name", "size")
        )
        .reset_index()
        .sort_values("San_luong", ascending=False)
    )
else:
    PRODUCT = pd.DataFrame()

# ----------------------- KPI ---------------------------------

total_revenue = DF["_revenue"].sum()
total_quantity = DF["_quantity"].sum()
total_weight = DF["_weight"].sum()
n_customers = DF["_customer_key"].nunique()
n_customer_vehicles = VEHICLE_DATA["_plate"].nunique() if not VEHICLE_DATA.empty else 0
n_high = CUSTOMER["Muc_do"].isin(["Cao", "Rất cao"]).sum()
n_insufficient = (CUSTOMER["Muc_do"] == "Chưa đủ dữ liệu").sum()

st.markdown("---")
st.markdown('<div class="section-title">TỔNG QUAN NPP</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Số NPP", f"{n_customers:,}")
k2.metric("Doanh thu", f"{total_revenue:,.0f}")
k3.metric("Sản lượng", f"{total_quantity:,.0f}")
k4.metric("Khối lượng", f"{total_weight:,.0f}")
k5.metric("Xe khách hàng", f"{n_customer_vehicles:,}")
k6.metric("NPP rủi ro cao", f"{n_high:,}")

st.caption(
    f"Đã loại {removed_z:,} dòng mã hàng bắt đầu Z, "
    f"{removed_discount:,} dòng tên hàng Chiết khấu và "
    f"{removed_return:,} dòng trả/hủy/số âm theo điều kiện đã chọn. "
    f"Có {n_insufficient:,} NPP chưa đủ độ phủ dữ liệu để xếp mức an toàn."
)

T1, T2, T3, T4, T5, T6, T7 = st.tabs([
    "Tổng quan",
    "Kho lấy hàng",
    "Địa điểm NPP",
    "Xe khách hàng",
    "Mối liên kết NPP",
    "Nhận định từng NPP",
    "Doanh thu & mặt hàng"
])

# ============================================================
# TAB 1 - SUMMARY
# ============================================================

with T1:
    st.markdown('<div class="section-title">PHÂN BỐ MỨC RỦI RO</div>', unsafe_allow_html=True)

    distribution = (
        CUSTOMER["Muc_do"].value_counts()
        .reindex(RISK_ORDER, fill_value=0)
        .rename_axis("Muc_do").reset_index(name="So_NPP")
    )

    fig = px.bar(
        distribution, x="Muc_do", y="So_NPP",
        color="Muc_do", text="So_NPP",
        color_discrete_map=RISK_COLORS
    )
    fig.update_layout(
        paper_bgcolor="#07111e", plot_bgcolor="#07111e",
        font_color="#c5d7eb", showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    a, b, c, d = st.columns(4)
    a.metric("NPP trùng địa điểm", len(ADDRESS_GROUP))
    b.metric("Xe nhiều NPP cùng ngày", len(VEHICLE_DAY_SHARED))
    c.metric("Xe nhiều NPP trong kỳ", len(VEHICLE_PERIOD))
    d.metric("Giao dịch xe KH ngoài danh sách kho", len(WH_EVIDENCE))

    st.markdown('<div class="section-title">NPP ƯU TIÊN KIỂM TRA</div>', unsafe_allow_html=True)
    st.dataframe(
        CUSTOMER[[
            "NPP", "Tong_diem", "Muc_do", "Do_phu_du_lieu", "Nhan_dinh", "Giai_phap"
        ]].head(30),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Điểm rủi ro chỉ dùng để xếp thứ tự ưu tiên xác minh. "
        "Mức 'Chưa đủ dữ liệu' không đồng nghĩa rủi ro thấp."
    )

# ============================================================
# TAB 2 - WAREHOUSE
# ============================================================

with T2:
    st.markdown('<div class="section-title">ĐỐI CHIẾU KHO VỚI ĐỊA ĐIỂM NPP</div>', unsafe_allow_html=True)
    st.info(
        "Quy tắc kiểm tra áp dụng cho Xe khách hàng בלבד. "
        "Xe nhà máy và xe thuê ngoài không tham gia bảng đối chiếu."
    )

    if CUSTOMER_CAR.empty:
        st.warning("Không có giao dịch được phân loại là Xe khách hàng.")
    else:
        st.dataframe(WH_STATUS_COUNTS, use_container_width=True, hide_index=True)

        st.markdown("### Giao dịch lấy hàng ngoài danh sách vùng")
        if WH_EVIDENCE.empty:
            st.success("Chưa có giao dịch nào nằm ngoài danh sách kho theo vùng.")
        else:
            st.dataframe(
                WH_EVIDENCE[[
                    "_customer_name", "_address", "_region",
                    "_warehouse_code", "_plate_raw", "_date",
                    "_document", "_revenue", "_quantity", "_weight"
                ]].rename(columns={
                    "_customer_name": "NPP",
                    "_address": "Địa điểm",
                    "_region": "Khu vực",
                    "_warehouse_code": "Mã kho",
                    "_plate_raw": "Biển số",
                    "_date": "Ngày",
                    "_document": "Chứng từ",
                    "_revenue": "Doanh thu",
                    "_quantity": "Số lượng",
                    "_weight": "Khối lượng"
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Giao dịch chưa đủ dữ liệu để kết luận")
        if WH_UNKNOWN.empty:
            st.success("Không có giao dịch thiếu thông tin vùng/kho.")
        else:
            st.warning(f"{len(WH_UNKNOWN):,} giao dịch cần bổ sung hoặc xác minh.")
            st.dataframe(
                WH_UNKNOWN[[
                    "_customer_name", "_address", "_region",
                    "_warehouse_code", "_warehouse_status",
                    "_plate_raw", "_date", "_document"
                ]],
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Các bước kiểm tra")
        st.write("""
        1. Xác minh địa điểm NPP và vùng địa lý được nhận diện.
        2. Đối chiếu mã kho thực tế với danh sách kho đã cấu hình.
        3. Đối chiếu phiếu xuất kho, ngày lấy hàng, biển số và người nhận.
        4. Kiểm tra chứng từ điều phối, điều chuyển hoặc phê duyệt ngoại lệ.
        5. Chỉ chuyển thành phát hiện sau khi đơn vị kinh doanh giải trình và KSNB kiểm tra chứng từ.
        """)

# ============================================================
# TAB 3 - ADDRESS
# ============================================================

with T3:
    st.markdown('<div class="section-title">NPP CÓ ĐỊA ĐIỂM TRÙNG CHÍNH XÁC</div>', unsafe_allow_html=True)
    if ADDRESS_GROUP.empty:
        st.success("Chưa phát hiện địa điểm trùng chính xác.")
    else:
        st.warning(f"Có {len(ADDRESS_GROUP):,} cụm địa điểm từ hai NPP trở lên.")
        st.dataframe(
            ADDRESS_GROUP[["Dia_diem", "So_NPP", "Danh_sach_NPP"]],
            use_container_width=True,
            hide_index=True
        )

    st.markdown('<div class="section-title">ĐỊA ĐIỂM GẦN GIỐNG - CẦN XÁC MINH</div>', unsafe_allow_html=True)
    if FUZZY_ADDRESS.empty:
        st.info("Không có cặp địa điểm gần giống vượt ngưỡng hiện tại hoặc dữ liệu địa chỉ chưa đủ.")
    else:
        st.caption(
            "So khớp văn bản chỉ đề xuất các cặp gần giống; không tự động coi là cùng địa điểm."
        )
        st.dataframe(FUZZY_ADDRESS, use_container_width=True, hide_index=True)

    st.markdown("### Hướng xác minh")
    st.write("""
    - Đối chiếu địa chỉ trên hồ sơ mở khách hàng và giấy phép kinh doanh.
    - Kiểm tra số nhà, đường, phường/xã, quận/huyện và tỉnh/thành.
    - Kiểm tra người đại diện, số điện thoại, email và người nhận hàng.
    - Xác minh thực tế có nhiều NPP cùng hoạt động tại một địa điểm hay không.
    """)

# ============================================================
# TAB 4 - VEHICLE
# ============================================================

with T4:
    st.markdown('<div class="section-title">MỘT XE - NHIỀU NPP - CÙNG NGÀY</div>', unsafe_allow_html=True)
    if VEHICLE_DAY_SHARED.empty:
        st.success("Chưa ghi nhận một xe phục vụ từ hai NPP trở lên trong cùng ngày.")
    else:
        st.warning(f"Có {len(VEHICLE_DAY_SHARED):,} biển số/ngày liên quan nhiều NPP.")
        st.dataframe(
            VEHICLE_DAY_SHARED.rename(columns={
                "_date_only": "Ngày",
                "Bien_so": "Biển số",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP",
                "Danh_sach_chung_tu": "Chứng từ",
                "Danh_sach_kho": "Mã kho",
                "Danh_sach_dia_diem": "Địa điểm",
                "So_dia_diem": "Số địa điểm",
                "So_kho": "Số kho",
                "So_giao_dich": "Số giao dịch"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown('<div class="section-title">MỘT XE - NHIỀU NPP - LẶP LẠI TRONG NHIỀU NGÀY</div>', unsafe_allow_html=True)
    if VEHICLE_PERIOD.empty:
        st.success("Chưa có biển số dùng chung bởi nhiều NPP trong kỳ.")
    else:
        st.dataframe(
            VEHICLE_PERIOD.rename(columns={
                "_plate": "Biển số chuẩn hóa",
                "Bien_so": "Biển số",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP",
                "So_ngay_hoat_dong": "Số ngày hoạt động",
                "So_ngay_dung_chung": "Số ngày nhiều NPP cùng dùng",
                "So_giao_dich": "Số giao dịch",
                "Danh_sach_dia_diem": "Địa điểm",
                "Danh_sach_kho": "Mã kho"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown('<div class="section-title">THIẾU BIỂN SỐ TRONG GIAO DỊCH XE KHÁCH HÀNG</div>', unsafe_allow_html=True)
    if MISSING_PLATE.empty:
        st.success("Không có dòng xe khách hàng thiếu biển số.")
    else:
        st.warning(f"Có {len(MISSING_PLATE):,} dòng xe khách hàng chưa có biển số.")
        st.dataframe(
            MISSING_PLATE[[
                "_customer_name", "_date", "_document",
                "_method", "_address", "_warehouse_code",
                "_revenue", "_quantity", "_weight"
            ]],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### Cách xác minh")
    st.write("""
    - Một xe phục vụ nhiều NPP trong cùng ngày là dấu hiệu cần kiểm tra, chưa tự động kết luận sai phạm.
    - Đối chiếu chứng từ, giờ xuất hàng nếu có, người lái và người nhận hàng.
    - Nếu không có giờ lấy hàng, dữ liệu chỉ chứng minh các giao dịch cùng ngày, không chứng minh xe không thể di chuyển giữa các điểm.
    - Nếu lặp lại nhiều ngày, ưu tiên kiểm tra mối quan hệ và thỏa thuận vận chuyển giữa các NPP.
    """)

# ============================================================
# TAB 5 - NETWORK LINKS
# ============================================================

with T5:
    st.markdown('<div class="section-title">MỐI LIÊN KẾT GIỮA CÁC NPP</div>', unsafe_allow_html=True)
    if LINKS.empty:
        st.info("Chưa phát hiện cặp NPP có chung địa điểm hoặc biển số xe trong dữ liệu.")
    else:
        st.warning(
            f"Có {len(LINKS):,} cặp NPP có ít nhất một dấu hiệu liên kết. "
            "Đây là danh sách để xác minh, không phải kết luận quan hệ sở hữu."
        )
        st.dataframe(LINKS, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">TỔNG HỢP CÁC TÌNH HUỐNG CẦN XÁC MINH</div>', unsafe_allow_html=True)
    st.write("""
    1. NPP A và NPP B cùng địa điểm: kiểm tra địa điểm kinh doanh, hồ sơ pháp lý và người đại diện.
    2. NPP A và NPP B dùng chung biển số: kiểm tra chủ xe, người lái, thỏa thuận vận chuyển và chứng từ.
    3. Cùng địa điểm và cùng biển số: ưu tiên xác minh sâu hơn vì có nhiều dấu hiệu độc lập.
    4. Chỉ dùng chung một xe một lần: kiểm tra trước khi đánh giá là bất thường lặp lại.
    """)

# ============================================================
# TAB 6 - CUSTOMER RISK ASSESSMENT
# ============================================================

with T6:
    st.markdown('<div class="section-title">BẢNG ĐIỂM VÀ NHẬN ĐỊNH TỪNG NPP</div>', unsafe_allow_html=True)

    score_view = CUSTOMER[[
        "NPP", "Tong_diem", "Muc_do", "Do_phu_du_lieu",
        "Diem_kho", "Diem_dia_diem", "Diem_xe_cung_ngay",
        "Diem_xe_trong_ky", "Diem_nhieu_kho", "Diem_tan_suat",
        "Diem_san_luong", "Diem_trung_du_lieu",
        "Diem_thieu_dia_diem", "Diem_thieu_bien_so",
        "Nhan_dinh", "Giai_phap"
    ]].copy()

    st.dataframe(score_view, use_container_width=True, hide_index=True)

    st.markdown("### Hồ sơ phân tích một NPP")
    selected = st.selectbox("Chọn NPP", CUSTOMER["NPP"].dropna().unique().tolist())

    detail = CUSTOMER[CUSTOMER["NPP"] == selected].iloc[0]
    st.metric(
        "Điểm sàng lọc",
        f"{int(detail['Tong_diem'])}/100",
        delta=f"{detail['Muc_do']} | Độ phủ dữ liệu {detail['Do_phu_du_lieu']:.0%}"
    )

    st.markdown(
        f'<div class="{risk_css(detail["Muc_do"])}">'
        f'<b>NHẬN ĐỊNH DỰA TRÊN DỮ LIỆU:</b><br>{detail["Nhan_dinh"]}'
        f'<br><br><b>HƯỚNG XỬ LÝ:</b><br>{detail["Giai_phap"]}'
        f'</div>',
        unsafe_allow_html=True
    )

    # Transaction-level evidence for selected customer
    selected_key = detail["_customer_key"]
    st.markdown("### Bằng chứng giao dịch của NPP")

    car_detail = CUSTOMER_CAR[CUSTOMER_CAR["_customer_key"] == selected_key].copy()
    if not car_detail.empty:
        st.markdown("#### Giao dịch xe khách hàng")
        st.dataframe(
            car_detail[[
                "_date", "_document", "_method", "_plate_raw",
                "_address", "_region", "_warehouse_code",
                "_warehouse_status", "_revenue", "_quantity", "_weight"
            ]].rename(columns={
                "_date": "Ngày", "_document": "Chứng từ",
                "_method": "Hình thức vận chuyển", "_plate_raw": "Biển số",
                "_address": "Địa điểm", "_region": "Vùng",
                "_warehouse_code": "Mã kho", "_warehouse_status": "Đối chiếu kho",
                "_revenue": "Doanh thu", "_quantity": "Số lượng",
                "_weight": "Khối lượng"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("NPP chưa có giao dịch xe khách hàng trong phạm vi dữ liệu.")

    npp_addresses = ADDRESS_PAIRS[
        ADDRESS_PAIRS["_customer_key"] == selected_key
    ] if not ADDRESS_PAIRS.empty else pd.DataFrame()

    if not npp_addresses.empty:
        st.markdown("#### Địa điểm được ghi nhận")
        st.dataframe(npp_addresses, use_container_width=True, hide_index=True)

    npp_vehicle_events = VEHICLE_DATA[
        VEHICLE_DATA["_customer_key"] == selected_key
    ] if not VEHICLE_DATA.empty else pd.DataFrame()

    if not npp_vehicle_events.empty:
        st.markdown("#### Lịch sử biển số xe")
        st.dataframe(
            npp_vehicle_events[[
                "_date", "_document", "_plate_raw",
                "_address", "_warehouse_code", "_revenue",
                "_quantity", "_weight"
            ]],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("#### Cơ cấu điểm")
    components = pd.DataFrame({
        "Nhóm": [
            "Kho ngoài danh sách", "Địa điểm dùng chung",
            "Xe nhiều NPP cùng ngày", "Xe nhiều NPP trong kỳ",
            "Nhiều kho cùng ngày", "Tần suất",
            "Sản lượng đột biến", "Dữ liệu trùng",
            "Thiếu địa điểm", "Thiếu biển số"
        ],
        "Điểm": [
            detail["Diem_kho"], detail["Diem_dia_diem"],
            detail["Diem_xe_cung_ngay"], detail["Diem_xe_trong_ky"],
            detail["Diem_nhieu_kho"], detail["Diem_tan_suat"],
            detail["Diem_san_luong"], detail["Diem_trung_du_lieu"],
            detail["Diem_thieu_dia_diem"], detail["Diem_thieu_bien_so"]
        ]
    })

    fig = px.bar(
        components, x="Điểm", y="Nhóm",
        orientation="h", text="Điểm",
        title="Các thành phần tạo nên điểm rủi ro"
    )
    fig.update_layout(
        paper_bgcolor="#07111e", plot_bgcolor="#07111e",
        font_color="#c5d7eb", height=380
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 7 - SALES / PRODUCT
# ============================================================

with T7:
    st.markdown('<div class="section-title">DOANH THU VÀ SẢN LƯỢNG THEO THÁNG</div>', unsafe_allow_html=True)
    monthly_summary = (
        DF.groupby("_month")
        .agg(
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum"),
            So_NPP=("_customer_key", "nunique")
        )
        .reset_index()
        .sort_values("_month")
    )

    a, b = st.columns(2)
    with a:
        fig = px.bar(monthly_summary, x="_month", y="Doanh_thu", title="Doanh thu")
        fig.update_layout(paper_bgcolor="#07111e", plot_bgcolor="#07111e", font_color="#c5d7eb")
        st.plotly_chart(fig, use_container_width=True)
    with b:
        fig = px.line(monthly_summary, x="_month", y="San_luong", markers=True, title="Sản lượng")
        fig.update_layout(paper_bgcolor="#07111e", plot_bgcolor="#07111e", font_color="#c5d7eb")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Mặt hàng")
    if PRODUCT.empty:
        st.info("Chưa chọn cột tên hàng hoặc mã hàng.")
    else:
        st.dataframe(PRODUCT, use_container_width=True, hide_index=True)

    st.markdown("### Tháng sản lượng tăng đột biến")
    if SPIKE_TABLE.empty:
        st.info("Chưa có trường hợp vượt ngưỡng 3 lần trung vị các tháng trước.")
    else:
        st.dataframe(SPIKE_TABLE, use_container_width=True, hide_index=True)

# ============================================================
# EXCEL EXPORT
# ============================================================

st.markdown("---")
st.markdown('<div class="section-title">TẢI HỒ SƠ KIỂM TRA NPP</div>', unsafe_allow_html=True)

source_columns = list(dict.fromkeys([
    x for x in [
        customer_col, customer_id_col, group_col, date_col, time_col,
        document_col, address_col, warehouse_col, method_col, vehicle_col,
        revenue_col, quantity_col, weight_col, item_code_col, item_name_col
    ] if x and x in DF.columns
]))

safe_detail = DF[source_columns].copy()
safe_detail["Vung_nhan_dien"] = DF["_region"]
safe_detail["Ma_kho_chuan_hoa"] = DF["_warehouse_code"]
safe_detail["Phan_loai_phuong_tien"] = DF["_vehicle_type"]

safe_car = CUSTOMER_CAR[source_columns].copy()
for col in [
    "_customer_name", "_customer_key", "_date", "_date_only",
    "_address", "_region", "_warehouse_code", "_warehouse_status",
    "_vehicle_type", "_plate", "_transaction_key"
]:
    if col in CUSTOMER_CAR.columns:
        safe_car[col] = CUSTOMER_CAR[col]

safe_wh_evidence = WH_EVIDENCE[source_columns].copy()
for col in [
    "_customer_name", "_customer_key", "_date", "_date_only",
    "_address", "_region", "_warehouse_code", "_warehouse_status",
    "_vehicle_type", "_plate"
]:
    if col in WH_EVIDENCE.columns:
        safe_wh_evidence[col] = WH_EVIDENCE[col]

safe_wh_unknown = WH_UNKNOWN[source_columns].copy()
for col in [
    "_customer_name", "_customer_key", "_date", "_date_only",
    "_address", "_region", "_warehouse_code", "_warehouse_status",
    "_vehicle_type", "_plate"
]:
    if col in WH_UNKNOWN.columns:
        safe_wh_unknown[col] = WH_UNKNOWN[col]

safe_duplicates = DUPLICATE_ROWS[source_columns].copy()
for col in [
    "_customer_name", "_customer_key", "_date", "_date_only",
    "_address", "_region", "_warehouse_code", "_vehicle_type", "_plate"
]:
    if col in DUPLICATE_ROWS.columns:
        safe_duplicates[col] = DUPLICATE_ROWS[col]

export = io.BytesIO()

with pd.ExcelWriter(export, engine="openpyxl") as writer:
    CUSTOMER.to_excel(writer, sheet_name="Tong_hop_rui_ro_NPP", index=False)
    safe_detail.to_excel(writer, sheet_name="Du_lieu_sau_loc", index=False)
    safe_car.to_excel(writer, sheet_name="Xe_khach_hang", index=False)
    ADDRESS_GROUP.to_excel(writer, sheet_name="NPP_trung_dia_diem", index=False)
    FUZZY_ADDRESS.to_excel(writer, sheet_name="Dia_diem_gan_giong", index=False)
    VEHICLE_DAY_SHARED.to_excel(writer, sheet_name="Xe_nhieu_NPP_cung_ngay", index=False)
    VEHICLE_PERIOD.to_excel(writer, sheet_name="Xe_nhieu_NPP_trong_ky", index=False)
    LINKS.to_excel(writer, sheet_name="Lien_ket_NPP", index=False)
    safe_wh_evidence.to_excel(writer, sheet_name="Kho_ngoai_danh_sach", index=False)
    safe_wh_unknown.to_excel(writer, sheet_name="Kho_thieu_du_lieu", index=False)
    MULTI_WH.to_excel(writer, sheet_name="Mot_NPP_nhieu_kho_ngay", index=False)
    DAILY_ALERT.to_excel(writer, sheet_name="Tan_suat_cao", index=False)
    safe_duplicates.to_excel(writer, sheet_name="Dong_nghi_trung", index=False)
    SPIKE_TABLE.to_excel(writer, sheet_name="San_luong_dot_bien", index=False)
    PRODUCT.to_excel(writer, sheet_name="Mat_hang", index=False)

export.seek(0)

st.download_button(
    "TẢI BÁO CÁO KIỂM SOÁT NPP (EXCEL)",
    data=export.getvalue(),
    file_name="NPP_Risk_Analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ----------------------- Legend -----------------------------

st.markdown("---")
st.markdown('<div class="section-title">THANG MÀU VÀ CÁCH DIỄN GIẢI</div>', unsafe_allow_html=True)

a, b, c, d, e = st.columns(5)
with a:
    st.markdown('<div class="risk-green"><b>XANH</b><br>0–24 điểm</div>', unsafe_allow_html=True)
with b:
    st.markdown('<div class="risk-yellow"><b>VÀNG</b><br>25–44 điểm</div>', unsafe_allow_html=True)
with c:
    st.markdown('<div class="risk-orange"><b>CAM</b><br>45–64 điểm</div>', unsafe_allow_html=True)
with d:
    st.markdown('<div class="risk-red"><b>ĐỎ</b><br>65–100 điểm</div>', unsafe_allow_html=True)
with e:
    st.markdown('<div class="risk-gray"><b>CHƯA ĐỦ</b><br>Độ phủ dưới 60%</div>', unsafe_allow_html=True)

st.caption(
    "Phân tích là công cụ sàng lọc. Mỗi cảnh báo cần được đối chiếu chứng từ, giải trình và xác minh thực tế. "
    "Không dùng riêng điểm số để kết luận vi phạm hoặc thông đồng."
)
