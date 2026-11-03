import io
import re
import unicodedata
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# NPP BUSINESS RISK ANALYTICS - REBUILD
# Focus: sales/product, pickup warehouse vs distributor address,
# customer-owned vehicles shared by multiple distributors.
# Unknown/unmapped records are isolated, never silently scored.
# ============================================================

st.set_page_config(
    page_title="NPP Business Risk Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Be Vietnam Pro',sans-serif;}
[data-testid="stAppViewContainer"] {background:#081321;}
[data-testid="stHeader"] {background:transparent;}
section[data-testid="stSidebar"] {background:#0c1b2d;}
.main-title {font-size:28px;font-weight:800;color:#eaf2ff;margin-bottom:2px;}
.sub-title {font-size:12px;color:#8ea6c2;margin-bottom:18px;}
.section-title {color:#8fc1ff;font-size:14px;font-weight:800;margin:16px 0 8px;}
.risk-card {padding:12px 14px;border-radius:9px;margin:4px 0;}
.risk-low {background:#102d22;color:#a7f3d0;border-left:4px solid #22c55e;}
.risk-watch {background:#39320f;color:#fff0a8;border-left:4px solid #eab308;}
.risk-high {background:#3b2814;color:#ffd199;border-left:4px solid #f97316;}
.risk-critical {background:#39191c;color:#ffb5b5;border-left:4px solid #ef4444;}
.risk-unknown {background:#1b2939;color:#cbd5e1;border-left:4px solid #94a3b8;}
div[data-testid="stMetric"] {background:#101f31;padding:12px;border-radius:10px;border:1px solid #1e344d;}
</style>
""", unsafe_allow_html=True)

# Mã kho được trích từ 3 chữ số đầu của Số chứng từ, ví dụ 263.18067094 -> 263.
WAREHOUSE_NAMES = {
    "053": "Nhựa Phú Mỹ", "054": "Nhựa Phú Mỹ", "055": "Nhựa Phú Mỹ",
    "251": "Nhựa BĐ", "252": "TK Đaklak", "253": "Nhựa BĐ", "254": "Nhựa BĐ",
    "261": "Nhựa HN", "262": "Nhựa HN", "263": "TK ĐN", "264": "TK ĐN",
    "281": "TK CT", "282": "Kho hàng gửi tại HS Home của HSN Phú Mỹ",
    "283": "TK CT", "284": "TK PT", "285": "TK PT", "291": "TK YB",
    "292": "Kho hàng gửi tại HS Home của HSN Phú Mỹ",
    "301": "TK Nam Cấm", "302": "TK Nam Cấm",
}

# Ma trận kho ưu tiên theo địa chỉ cụ thể do người dùng cung cấp.
ADDRESS_WAREHOUSE_RULES = {
    "Miền Bắc": {
        "keywords": ["hai phong", "ha noi", "hung yen", "bac ninh", "quang ninh", "ninh binh",
            "thanh hoa", "nghe an", "ha tinh", "tuyen quang", "phu tho", "thai nguyen",
            "lao cai", "lai chau", "son la", "dien bien", "xa nghia dan", "xa kim anh",
            "phuong tam thanh", "phuong quyet thang", "phuong minh xuan"],
        "warehouses": {"261", "291"},
    },
    "Huế và Quảng Trị": {
        "keywords": ["hue", "thua thien hue", "quang tri"],
        "warehouses": {"251", "261", "263"},
    },
    "Đà Nẵng": {
        "keywords": ["da nang"],
        "warehouses": {"251", "263"},
    },
    "Khánh Hòa và Quảng Ngãi": {
        "keywords": ["khanh hoa", "quang ngai"],
        "warehouses": {"251", "263", "053", "284"},
    },
    "Tây Nguyên và địa bàn liên quan": {
        "keywords": ["dak lak", "daklak", "gia lai", "lam dong", "xa duc lap",
            "xa cat tien 2", "xa cat tien", "xa nam ban lam ha", "xa quang lap",
            "xa duc trong", "phuong lam vien da lat"],
        "warehouses": {"251", "252", "263", "053", "054", "284"},
    },
    "Đông Nam Bộ": {
        "keywords": ["dong nai", "ho chi minh", "tay ninh", "binh duong",
            "ba ria vung tau", "ba ria- vung tau", "quan thu duc", "phuong thong nhat"],
        "warehouses": {"053", "054", "281", "284"},
    },
    "Tây Nam Bộ": {
        "keywords": ["an giang", "dong thap", "vinh long", "can tho", "ca mau"],
        "warehouses": {"053", "054", "281", "284"},
    },
}
BROAD_REGION_RULES = {
    "Miền Bắc": {"261", "291"},
    "Miền Trung": {"251", "261", "263", "053", "054", "284"},
    "Tây Nguyên": {"251", "252", "263", "053", "054", "284"},
    "Miền Nam": {"053", "054", "281", "284"},
    "Miền Tây": {"053", "054", "281", "284"},
}
SPECIAL_WAREHOUSES = {"282", "292"}
WAREHOUSE_STATUS_OUTSIDE = "Ngoài danh sách kho hợp lý - cần xác minh"
WAREHOUSE_STATUS_SPECIAL = "Kho hàng gửi HS Home - cần xác minh riêng"
WAREHOUSE_STATUS_FALLBACK = "Phù hợp theo miền tổng quát - cần xác minh địa chỉ"

NPP_TYPES = {
    "nha phan phoi ong nhua",
    "nha phan phoi nhua kd ton thep",
}
RISK_ORDER = ["Rất cao", "Cao", "Theo dõi", "Thấp", "Chưa đủ dữ liệu"]
RISK_CSS = {
    "Thấp": "risk-low",
    "Theo dõi": "risk-watch",
    "Cao": "risk-high",
    "Rất cao": "risk-critical",
    "Chưa đủ dữ liệu": "risk-unknown",
}

ALIASES = {
    "customer": ["Tên khách hàng", "Tên KH", "Khách hàng"],
    "customer_id": ["Mã khách hàng", "Mã KH"],
    "customer_type": ["Loại khách hàng", "Nhóm khách hàng", "Loại KH"],
    "date": ["Ngày chứng từ", "Ngày xuất", "Ngày lấy hàng", "Ngày giao hàng"],
    "time": ["Giờ chứng từ", "Giờ xuất", "Giờ lấy hàng"],
    "document": ["Số chứng từ", "Số CT", "Số phiếu"],
    "address": ["Địa chỉ", "Địa chỉ khách hàng", "Địa chỉ KH", "Địa điểm"],
    "region": ["Miền2", "Miền", "Vùng miền", "Khu vực"],
    "warehouse": ["Mã kho", "Mã kho xuất", "Kho xuất", "Kho lấy hàng"],
    "method": ["Hình thức vận chuyển", "Phương thức vận chuyển", "Loại vận chuyển"],
    "vehicle": ["Số xe", "Biển số xe", "Biển kiểm soát"],
    "revenue": ["Thành tiền bán", "Doanh thu", "Thành tiền"],
    "quantity": ["Số lượng", "SL"],
    "weight": ["Khối lượng", "Trọng lượng"],
    "item_code": ["Mã hàng", "Mã SP", "Mã sản phẩm"],
    "item_name": ["Tên hàng", "Tên sản phẩm"],
}


def norm(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    value = str(value).strip()
    return "" if value.lower() in {"nan", "none", "null"} else value


def clean_code(value):
    text = clean(value).upper()
    if not text:
        return ""
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return str(int(float(text))).zfill(3)
    return re.sub(r"[^A-Z0-9]", "", text)


def clean_plate(value):
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())


def is_valid_plate(value):
    # Screening format only; unusual legitimate formats must be checked manually.
    return bool(re.fullmatch(r"\d{2}[A-Z]{1,2}\d{4,6}", clean_plate(value)))


def parse_number(value):
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        pass
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
    except ValueError:
        return 0.0


def parse_date_series(series):
    numeric = pd.to_numeric(series, errors="coerce")
    result = pd.to_datetime(series, errors="coerce", dayfirst=True)
    mask = numeric.between(20000, 80000)
    if mask.any():
        result.loc[mask] = pd.to_datetime(
            numeric.loc[mask], unit="D", origin="1899-12-30", errors="coerce"
        )
    return result


def find_column(columns, aliases):
    normalized = {norm(c): c for c in columns}
    for alias in aliases:
        if norm(alias) in normalized:
            return normalized[norm(alias)]
    return None


def best_header(preview):
    best_index, best_score = 0, -1
    required_keys = ["customer", "date", "document", "method", "revenue"]
    for i in range(len(preview)):
        cells = [norm(x) for x in preview.iloc[i].tolist()]
        score = 0
        for key in required_keys:
            if any(norm(a) in cells for a in ALIASES[key]):
                score += 1
        if score > best_score:
            best_index, best_score = i, score
    return best_index, best_score


@st.cache_data(show_spinner=False, max_entries=4)
def inspect_workbook(file_bytes):
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    options, logs = [], []
    for sheet in xls.sheet_names:
        try:
            preview = pd.read_excel(
                io.BytesIO(file_bytes), sheet_name=sheet,
                header=None, nrows=35, engine="openpyxl"
            )
            if preview.empty:
                continue
            header_row, score = best_header(preview)
            options.append({
                "sheet": sheet,
                "header_row": header_row,
                "score": score,
                "rows": len(preview),
            })
            logs.append(f"{sheet}: dòng tiêu đề dự kiến {header_row + 1}, nhận diện {score}/5")
        except Exception as exc:
            logs.append(f"{sheet}: không đọc được ({exc})")
    options.sort(key=lambda x: (x["score"], x["rows"]), reverse=True)
    return options, logs


@st.cache_data(show_spinner=False, max_entries=4)
def load_sheet(file_bytes, sheet, header_row):
    data = pd.read_excel(
        io.BytesIO(file_bytes), sheet_name=sheet,
        header=header_row, engine="openpyxl"
    )
    data.columns = [
        str(c).strip() if str(c).strip() else f"Column_{i}"
        for i, c in enumerate(data.columns)
    ]
    data = data.dropna(how="all").copy()
    data["_dong_nguon"] = np.arange(len(data)) + header_row + 2
    return data


def classify_transport(value):
    text = norm(value)
    if not text:
        return "Chưa xác định"
    if any(x in text for x in ["thue ngoai", "xe thue", "nha may thue ngoai", "outsourc"]):
        return "Xe nhà máy thuê ngoài"
    if any(x in text for x in ["xe nha may", "nha may", "factory"]):
        return "Xe nhà máy"
    if any(x in text for x in ["xe khach hang", "xe kh", "khach hang", "khach tu lay", "customer"]):
        return "Xe khách hàng"
    return "Chưa xác định"


def identify_region(region_value, address):
    """Ưu tiên nhóm địa chỉ cụ thể; dùng Miền2 làm dự phòng."""
    a = norm(address)
    matches = []
    for group, rule in ADDRESS_WAREHOUSE_RULES.items():
        for keyword in rule["keywords"]:
            key = norm(keyword)
            # Match whole phrase boundaries; tránh "Huế" bị nhận nhầm
            # bên trong từ "huyện".
            pattern = r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])"
            if key and re.search(pattern, a):
                matches.append((len(key), group))
    if matches:
        matches.sort(reverse=True)
        return matches[0][1]

    r = norm(region_value)
    if "mien bac" in r or r == "bac":
        return "Miền Bắc"
    if "tay nguyen" in r:
        return "Tây Nguyên"
    if "mien trung" in r or r == "trung":
        return "Miền Trung"
    if "mien tay" in r or "dbscl" in r:
        return "Miền Tây"
    if "mien nam" in r or "dong nam bo" in r or r == "nam":
        return "Miền Nam"
    return "Chưa xác định vùng"


def extract_warehouse_code(document_number):
    """Lấy 3 chữ số đầu Số chứng từ: 263.18067094 -> 263."""
    text = clean(document_number).strip()
    match = re.match(r"^(\d{3})(?=\.|/|-|\s|$)", text)
    return match.group(1) if match else ""


def warehouse_name(code):
    return WAREHOUSE_NAMES.get(code, "Mã kho chưa có trong danh mục")


def allowed_warehouses_for_region(region):
    if region in ADDRESS_WAREHOUSE_RULES:
        return ADDRESS_WAREHOUSE_RULES[region]["warehouses"], "Địa chỉ cụ thể"
    if region in BROAD_REGION_RULES:
        return BROAD_REGION_RULES[region], "Miền2 dự phòng"
    return set(), "Chưa xác định"


def warehouse_check(region, warehouse):
    if not warehouse:
        return "Không trích xuất được mã kho từ số chứng từ"
    if warehouse not in WAREHOUSE_NAMES:
        return "Mã kho chưa có trong danh mục"
    if warehouse in SPECIAL_WAREHOUSES:
        return WAREHOUSE_STATUS_SPECIAL
    allowed, basis = allowed_warehouses_for_region(region)
    if not allowed:
        return "Chưa đủ dữ liệu địa chỉ/vùng"
    if warehouse in allowed:
        return WAREHOUSE_STATUS_FALLBACK if basis == "Miền2 dự phòng" else "Phù hợp địa chỉ/khu vực"
    return WAREHOUSE_STATUS_OUTSIDE


def money_fmt(value):
    return f"{value:,.0f}"


def make_risk_label(score, enough_data):
    if not enough_data:
        return "Chưa đủ dữ liệu"
    if score >= 65:
        return "Rất cao"
    if score >= 45:
        return "Cao"
    if score >= 25:
        return "Theo dõi"
    return "Thấp"


def build_excel_export(sheets):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            safe_name = name[:31]
            (frame if frame is not None else pd.DataFrame()).to_excel(
                writer, sheet_name=safe_name, index=False
            )
    output.seek(0)
    return output.getvalue()


# ============================================================
# HEADER AND UPLOAD
# ============================================================

st.markdown('<div class="main-title">NPP BUSINESS RISK ANALYTICS</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">HOA SEN GROUP | SÀNG LỌC RỦI RO KINH DOANH NHÀ PHÂN PHỐI</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 1. DỮ LIỆU")
    uploaded = st.file_uploader("Tải báo cáo Excel (.xlsx)", type=["xlsx"])
    st.caption("Chọn một workbook mỗi lần phân tích để tránh cộng trùng dữ liệu giữa các báo cáo.")

if uploaded is None:
    st.info("Tải báo cáo Excel để bắt đầu phân tích.")
    st.stop()

file_bytes = uploaded.getvalue()
try:
    sheet_options, sheet_logs = inspect_workbook(file_bytes)
except Exception as exc:
    st.error(f"Không thể mở file Excel: {exc}")
    st.stop()

if not sheet_options:
    st.error("Không tìm thấy sheet có thể đọc. Kiểm tra lại file và dòng tiêu đề.")
    st.stop()

with st.sidebar:
    st.markdown("## 2. CHỌN SHEET")
    sheet_names = [x["sheet"] for x in sheet_options]
    best_sheet = sheet_options[0]["sheet"]
    selected_sheet = st.selectbox(
        "Sheet dữ liệu",
        sheet_names,
        index=sheet_names.index(best_sheet),
    )
    selected_meta = next(x for x in sheet_options if x["sheet"] == selected_sheet)
    st.caption(f"Dòng tiêu đề dự kiến: {selected_meta['header_row'] + 1} | Nhận diện: {selected_meta['score']}/5")

try:
    raw = load_sheet(file_bytes, selected_sheet, selected_meta["header_row"])
except Exception as exc:
    st.error(f"Lỗi khi đọc sheet {selected_sheet}: {exc}")
    st.stop()

if raw.empty:
    st.warning("Sheet không có dữ liệu.")
    st.stop()

# Auto-map fields; explicit aliases match actual workbook names.
mapped = {key: find_column(raw.columns, aliases) for key, aliases in ALIASES.items()}

with st.expander("Nhật ký đọc file và ánh xạ cột", expanded=False):
    for line in sheet_logs:
        st.write(line)
    mapping_view = pd.DataFrame([
        {"Trường phân tích": key, "Cột trong Excel": value or "Chưa nhận diện"}
        for key, value in mapped.items()
    ])
    st.dataframe(mapping_view, use_container_width=True, hide_index=True)

# Critical fields for the requested analysis.
required = ["customer", "customer_type", "date", "document", "address", "method", "vehicle"]
missing = [x for x in required if not mapped.get(x)]
if missing:
    st.warning(
        "Một số trường quan trọng chưa được nhận diện: "
        + ", ".join(missing)
        + ". Các phân tích liên quan sẽ chuyển sang khu vực Chưa đủ dữ liệu."
    )

if not mapped["customer"]:
    st.error("Không nhận diện được cột Tên khách hàng. Không thể tiếp tục phân tích.")
    st.stop()

# ============================================================
# NORMALIZE AND FILTER NPP
# ============================================================

df = raw.copy()
def get_col(key, default=""):
    col = mapped.get(key)
    return df[col] if col and col in df.columns else pd.Series([default] * len(df), index=df.index)

df["_ten_kh"] = get_col("customer").map(clean)
df["_ma_kh"] = get_col("customer_id").map(clean)
df["_loai_kh"] = get_col("customer_type").map(clean)
df["_loai_kh_norm"] = df["_loai_kh"].map(norm)
df["_ngay"] = parse_date_series(get_col("date"))
df["_gio"] = get_col("time").map(clean)
df["_chung_tu"] = get_col("document").map(clean)
df["_dia_chi"] = get_col("address").map(clean)
df["_mien_goc"] = get_col("region").map(clean)
df["_ma_kho"] = get_col("document").map(extract_warehouse_code)
df["_ten_kho"] = df["_ma_kho"].map(warehouse_name)
df["_hinh_thuc_goc"] = get_col("method").map(clean)
df["_loai_xe"] = df["_hinh_thuc_goc"].map(classify_transport)
df["_bien_so_goc"] = get_col("vehicle").map(clean)
df["_bien_so"] = df["_bien_so_goc"].map(clean_plate)
df["_bien_so_hop_le"] = df["_bien_so"].map(is_valid_plate)
df["_doanh_thu"] = get_col("revenue").map(parse_number)
df["_san_luong"] = get_col("quantity").map(parse_number)
df["_khoi_luong"] = get_col("weight").map(parse_number)
df["_ma_hang"] = get_col("item_code").map(clean)
df["_ten_hang"] = get_col("item_name").map(clean)
df["_vung"] = [
    identify_region(r, a) for r, a in zip(df["_mien_goc"], df["_dia_chi"])
]
df["_doi_chieu_kho"] = [
    warehouse_check(r, w) for r, w in zip(df["_vung"], df["_ma_kho"])
]
df["_customer_key"] = np.where(
    df["_ma_kh"].ne(""),
    df["_ma_kh"].str.upper(),
    df["_ten_kh"].map(norm),
)
df["_customer_key"] = pd.Series(df["_customer_key"], index=df.index).fillna("")
df["_ngay_only"] = df["_ngay"].dt.date
df["_thang"] = df["_ngay"].dt.to_period("M").astype(str).replace("NaT", "")
df["_ma_hang_z"] = df["_ma_hang"].str.upper().str.startswith("Z", na=False)

# NPP classification must be based on Loại khách hàng, not Mã nhóm KH.
npp_mask = df["_loai_kh_norm"].isin(NPP_TYPES)
if not mapped["customer_type"]:
    npp_mask = pd.Series(False, index=df.index)

with st.sidebar:
    st.markdown("## 3. PHẠM VI NPP")
    found_types = sorted(x for x in df["_loai_kh"].dropna().unique().tolist() if clean(x))
    default_npp_types = [x for x in found_types if norm(x) in NPP_TYPES]
    selected_types = st.multiselect(
        "Loại khách hàng Nhà phân phối",
        options=found_types,
        default=default_npp_types,
        help="Mặc định chọn hai loại NPP đã xác định trong workbook mẫu."
    )
    if not selected_types:
        st.warning("Chọn ít nhất một loại khách hàng NPP để chạy phân tích.")

if not selected_types:
    st.stop()

npp = df[df["_loai_kh"].isin(selected_types)].copy()
if npp.empty:
    st.warning("Không có dòng dữ liệu thuộc loại khách hàng đã chọn.")
    st.stop()

# Simple filters. Unmapped rows remain available in the separate data-quality tab.
with st.sidebar:
    st.markdown("## 4. BỘ LỌC")
    valid_dates = npp["_ngay"].dropna()
    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        date_range = st.date_input(
            "Khoảng ngày chứng từ",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None
    regions_found = sorted(x for x in npp["_vung"].unique() if x)
    selected_regions = st.multiselect("Vùng", regions_found, default=regions_found)
    customers_found = sorted(npp["_ten_kh"].dropna().unique().tolist())
    selected_customers = st.multiselect(
        "NPP (để trống = tất cả)",
        customers_found,
        default=[],
    )

filtered = npp.copy()
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["_ngay"].notna()
        & (filtered["_ngay"].dt.date >= start_date)
        & (filtered["_ngay"].dt.date <= end_date)
    ]
if selected_regions:
    filtered = filtered[filtered["_vung"].isin(selected_regions)]
if selected_customers:
    filtered = filtered[filtered["_ten_kh"].isin(selected_customers)]

if filtered.empty:
    st.warning("Không có dữ liệu sau khi áp dụng bộ lọc. Hãy mở rộng khoảng ngày hoặc vùng.")
    st.stop()

# Product Z-prefix rows are discount rows and excluded from revenue/product analytics.
sales = filtered[~filtered["_ma_hang_z"]].copy()
if mapped["item_code"] and sales.empty:
    st.warning("Sau khi loại mã hàng bắt đầu bằng Z, không còn dòng hàng để phân tích doanh thu/mặt hàng.")

# ============================================================
# PREPARE RISK TABLES
# ============================================================

customer_summary = (
    filtered.groupby(["_customer_key", "_ten_kh"], dropna=False)
    .agg(
        So_dong=("_customer_key", "size"),
        So_chung_tu=("_chung_tu", "nunique"),
        Doanh_thu=("_doanh_thu", "sum"),
        San_luong=("_san_luong", "sum"),
        So_dia_chi=("_dia_chi", lambda s: s.replace("", np.nan).nunique()),
        So_kho=("_ma_kho", lambda s: s.replace("", np.nan).nunique()),
    )
    .reset_index()
)

# Warehouse: evaluate customer-owned vehicle transactions only.
customer_vehicle = filtered[filtered["_loai_xe"] == "Xe khách hàng"].copy()
warehouse_evidence = customer_vehicle[
    customer_vehicle["_doi_chieu_kho"] == WAREHOUSE_STATUS_OUTSIDE
].copy()
warehouse_special = customer_vehicle[
    customer_vehicle["_doi_chieu_kho"] == WAREHOUSE_STATUS_SPECIAL
].copy()
warehouse_unknown = customer_vehicle[
    customer_vehicle["_doi_chieu_kho"].isin([
        "Không trích xuất được mã kho từ số chứng từ",
        "Mã kho chưa có trong danh mục",
        "Chưa đủ dữ liệu địa chỉ/vùng",
        "Chưa xác định vùng",
        WAREHOUSE_STATUS_FALLBACK
    ])
].copy()
warehouse_counts = (
    customer_vehicle.groupby("_doi_chieu_kho")
    .size().reset_index(name="Số dòng")
    .sort_values("Số dòng", ascending=False)
)

# Same vehicle, multiple distributors on the same date.
vehicle_valid = customer_vehicle[
    customer_vehicle["_bien_so_hop_le"] & customer_vehicle["_ngay_only"].notna()
].copy()
vehicle_day = (
    vehicle_valid.groupby(["_bien_so", "_ngay_only"])
    .agg(
        Bien_so_goc=("_bien_so_goc", "first"),
        So_NPP=("_customer_key", "nunique"),
        Danh_sach_NPP=("_ten_kh", lambda s: " | ".join(sorted(set(x for x in s if x)))),
        So_chung_tu=("_chung_tu", "nunique"),
        So_kho=("_ma_kho", "nunique"),
        So_dia_diem=("_dia_chi", "nunique"),
        So_giao_dich=("_dong_nguon", "nunique"),
        Danh_sach_kho=("_ma_kho", lambda s: ", ".join(sorted(set(x for x in s if x)))),
    )
    .reset_index()
)
vehicle_day_shared = vehicle_day[vehicle_day["So_NPP"] >= 2].copy()

# Same plate used by multiple NPP over the selected period, even on separate days.
vehicle_period = (
    vehicle_valid.groupby("_bien_so")
    .agg(
        Bien_so_goc=("_bien_so_goc", "first"),
        So_NPP=("_customer_key", "nunique"),
        Danh_sach_NPP=("_ten_kh", lambda s: " | ".join(sorted(set(x for x in s if x)))),
        So_ngay_hoat_dong=("_ngay_only", "nunique"),
        So_giao_dich=("_dong_nguon", "nunique"),
        Danh_sach_kho=("_ma_kho", lambda s: ", ".join(sorted(set(x for x in s if x)))),
    )
    .reset_index()
)
vehicle_period_shared = vehicle_period[
    (vehicle_period["So_NPP"] >= 2) & (vehicle_period["So_ngay_hoat_dong"] >= 2)
].copy()

# Exact shared addresses across distinct distributors.
address_rows = filtered[filtered["_dia_chi"].map(norm).ne("")].copy()
address_rows["_dia_chi_norm"] = address_rows["_dia_chi"].map(norm)
address_pairs = address_rows[["_customer_key", "_ten_kh", "_dia_chi", "_dia_chi_norm"]].drop_duplicates()
address_shared = (
    address_pairs.groupby("_dia_chi_norm")
    .agg(
        Dia_chi=("_dia_chi", "first"),
        So_NPP=("_customer_key", "nunique"),
        Danh_sach_NPP=("_ten_kh", lambda s: " | ".join(sorted(set(x for x in s if x)))),
    )
    .reset_index()
)
address_shared = address_shared[address_shared["So_NPP"] >= 2].copy()

# Sales/product analytics.
product_key = ["_ma_hang", "_ten_hang"]
product_rows = sales[
    sales["_ma_hang"].ne("") | sales["_ten_hang"].ne("")
].copy()
if not product_rows.empty:
    product_summary = (
        product_rows.groupby(product_key, dropna=False)
        .agg(
            Doanh_thu=("_doanh_thu", "sum"),
            San_luong=("_san_luong", "sum"),
            Khoi_luong=("_khoi_luong", "sum"),
            So_NPP=("_customer_key", "nunique"),
            So_chung_tu=("_chung_tu", "nunique"),
        )
        .reset_index()
        .sort_values("Doanh_thu", ascending=False)
    )
else:
    product_summary = pd.DataFrame(columns=["_ma_hang", "_ten_hang", "Doanh_thu", "San_luong", "Khoi_luong", "So_NPP", "So_chung_tu"])

monthly_sales = (
    sales[sales["_thang"].ne("")]
    .groupby("_thang")
    .agg(Doanh_thu=("_doanh_thu", "sum"), San_luong=("_san_luong", "sum"), So_NPP=("_customer_key", "nunique"))
    .reset_index()
    .sort_values("_thang")
)

# Unrecognized data are isolated and not treated as confirmed risk.
unknown_parts = []
for label, mask, reason in [
    ("Thiếu ngày chứng từ", filtered["_ngay"].isna(), "Không nhận diện được ngày chứng từ"),
    ("Thiếu địa chỉ", filtered["_dia_chi"].eq(""), "Thiếu địa chỉ NPP"),
    ("Chưa xác định vùng", filtered["_vung"].eq("Chưa xác định vùng"), "Không xác định được vùng từ Miền2/địa chỉ"),
    ("Không trích xuất được mã kho", filtered["_ma_kho"].eq(""), "Không lấy được 3 số đầu từ Số chứng từ"),
    ("Mã kho chưa có trong danh mục", filtered["_ma_kho"].ne("") & ~filtered["_ma_kho"].isin(WAREHOUSE_NAMES), "Mã kho trích từ chứng từ chưa có trong danh mục 20 mã kho"),
    ("Thiếu mã kho", filtered["_ma_kho"].eq(""), "Thiếu mã kho"),
    ("Chưa xác định hình thức vận chuyển", filtered["_loai_xe"].eq("Chưa xác định"), "Không phân loại được hình thức vận chuyển"),
    ("Thiếu/không chuẩn biển số", (filtered["_loai_xe"] == "Xe khách hàng") & (~filtered["_bien_so_hop_le"]), "Xe khách hàng thiếu hoặc biển số không đạt định dạng sàng lọc"),
]:
    part = filtered.loc[mask].copy()
    if not part.empty:
        part["_ly_do_chua_nhan_dien"] = reason
        part["_nhom_chua_nhan_dien"] = label
        unknown_parts.append(part)
unrecognized = pd.concat(unknown_parts, ignore_index=True).drop_duplicates("_dong_nguon") if unknown_parts else pd.DataFrame()

# Risk points are transparent screening weights, not legal conclusions.
warehouse_by_customer = warehouse_evidence.groupby("_customer_key").size() if not warehouse_evidence.empty else pd.Series(dtype=float)
vehicle_day_by_customer = (
    vehicle_valid.merge(
        vehicle_day_shared[["_bien_so", "_ngay_only"]],
        on=["_bien_so", "_ngay_only"], how="inner"
    ).groupby("_customer_key").size()
    if not vehicle_day_shared.empty else pd.Series(dtype=float)
)
vehicle_period_by_customer = (
    vehicle_valid.merge(vehicle_period_shared[["_bien_so"]], on="_bien_so", how="inner")
    .groupby("_customer_key").size()
    if not vehicle_period_shared.empty else pd.Series(dtype=float)
)
address_by_customer = (
    address_pairs.merge(address_shared[["_dia_chi_norm"]], on="_dia_chi_norm", how="inner")
    .groupby("_customer_key").size()
    if not address_shared.empty else pd.Series(dtype=float)
)

risk_rows = []
for _, row in customer_summary.iterrows():
    key = row["_customer_key"]
    n = max(int(row["So_dong"]), 1)
    wh_n = int(warehouse_by_customer.get(key, 0))
    day_n = int(vehicle_day_by_customer.get(key, 0))
    period_n = int(vehicle_period_by_customer.get(key, 0))
    addr_n = int(address_by_customer.get(key, 0))
    score = min(100, min(40, wh_n * 10) + min(30, day_n * 15) + min(20, period_n * 5) + min(10, addr_n * 10))
    has_critical_fields = (
        mapped["customer_type"] is not None
        and mapped["address"] is not None
        and mapped["document"] is not None
        and mapped["method"] is not None
        and mapped["date"] is not None
    )
    coverage = sum([
        bool(row["So_dong"]),
        bool(row["So_dia_chi"]),
        bool(row["So_kho"]),
        bool((customer_vehicle["_customer_key"] == key).any()) if not customer_vehicle.empty else False,
    ]) / 4
    has_customer_vehicle_data = (
        bool((customer_vehicle["_customer_key"] == key).any())
        if not customer_vehicle.empty else False
    )
    # Do not assign a green/low result when the NPP has no evidence
    # for the currently enabled customer-vehicle control.
    enough = has_critical_fields and coverage >= 0.75 and has_customer_vehicle_data
    level = make_risk_label(score, enough)
    reasons = []
    actions = []
    if wh_n:
        reasons.append(f"{wh_n} dòng xe khách hàng lấy hàng ngoài danh sách kho theo vùng.")
        actions.append("Đối chiếu phiếu xuất kho, địa chỉ NPP, vùng Miền2 và chứng từ điều chuyển/phê duyệt ngoại lệ.")
    if day_n:
        reasons.append(f"{day_n} dòng liên quan biển số được nhiều NPP sử dụng trong cùng ngày.")
        actions.append("Đối chiếu giờ lấy hàng, số chứng từ, chủ xe, tài xế và người nhận; xác minh khả năng xe phục vụ nhiều điểm.")
    if period_n:
        reasons.append(f"{period_n} dòng liên quan biển số xuất hiện với nhiều NPP trong nhiều ngày.")
        actions.append("Kiểm tra lịch sử sử dụng xe, thỏa thuận vận chuyển và mối liên hệ giữa các NPP.")
    if addr_n:
        reasons.append("Có địa chỉ trùng với NPP khác.")
        actions.append("Đối chiếu hồ sơ pháp lý, địa điểm kinh doanh và xác minh thực tế.")
    if not reasons:
        reasons.append("Chưa ghi nhận tín hiệu thuộc các quy tắc sàng lọc hiện tại.")
    if not actions:
        actions.append("Duy trì đối chiếu định kỳ; không kết luận không có rủi ro chỉ từ việc chưa phát hiện cảnh báo.")
    risk_rows.append({
        "Mã khách hàng": key,
        "NPP": row["_ten_kh"],
        "Điểm sàng lọc": score,
        "Mức độ": level,
        "Độ phủ dữ liệu": coverage,
        "Dòng kho ngoài danh sách": wh_n,
        "Dòng xe dùng chung cùng ngày": day_n,
        "Dòng xe dùng chung nhiều ngày": period_n,
        "Dòng địa chỉ trùng": addr_n,
        "Nhận định": " ".join(reasons),
        "Hướng xử lý": " ".join(actions),
    })
risk_summary = pd.DataFrame(risk_rows)
if not risk_summary.empty:
    risk_summary["_sort"] = risk_summary["Mức độ"].map({x: i for i, x in enumerate(RISK_ORDER)})
    risk_summary = risk_summary.sort_values(["_sort", "Điểm sàng lọc"], ascending=[True, False]).drop(columns="_sort")

# ============================================================
# DASHBOARD
# ============================================================

total_npp = filtered["_customer_key"].nunique()
total_revenue = sales["_doanh_thu"].sum()
total_qty = sales["_san_luong"].sum()
high_risk = int(risk_summary["Mức độ"].isin(["Cao", "Rất cao"]).sum()) if not risk_summary.empty else 0
unknown_count = len(unrecognized)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Số NPP", f"{total_npp:,}")
k2.metric("Doanh thu", money_fmt(total_revenue))
k3.metric("Sản lượng", f"{total_qty:,.2f}")
k4.metric("NPP rủi ro cao", f"{high_risk:,}")
k5.metric("Dòng chưa nhận diện", f"{unknown_count:,}")

tab_overview, tab_sales, tab_warehouse, tab_vehicle, tab_risk, tab_unknown = st.tabs([
    "Tổng quan", "Doanh thu & mặt hàng", "Kho lấy hàng", "Xe khách hàng", "Đánh giá rủi ro", "Chưa nhận diện"
])

with tab_overview:
    st.markdown('<div class="section-title">TỔNG QUAN RỦI RO NHÀ PHÂN PHỐI</div>', unsafe_allow_html=True)
    if risk_summary.empty:
        st.info("Chưa có dữ liệu đủ điều kiện để lập bảng đánh giá NPP.")
    else:
        levels = risk_summary["Mức độ"].value_counts().reindex(["Rất cao", "Cao", "Theo dõi", "Thấp", "Chưa đủ dữ liệu"], fill_value=0).reset_index()
        levels.columns = ["Mức độ", "Số NPP"]
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.bar(levels, x="Mức độ", y="Số NPP", color="Mức độ", title="Phân bố mức độ rủi ro")
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            if not monthly_sales.empty:
                fig = px.line(monthly_sales, x="_thang", y="Doanh_thu", markers=True, title="Doanh thu theo tháng")
                fig.update_layout(height=340, margin=dict(l=10, r=10, t=45, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa nhận diện được ngày để tổng hợp doanh thu theo tháng.")
        st.markdown("### NPP cần ưu tiên xác minh")
        st.dataframe(
            risk_summary[["NPP", "Điểm sàng lọc", "Mức độ", "Dòng kho ngoài danh sách", "Dòng xe dùng chung cùng ngày", "Dòng xe dùng chung nhiều ngày", "Nhận định"]],
            use_container_width=True, hide_index=True
        )
    st.markdown("### Danh mục mã kho và tên kho")
    st.dataframe(pd.DataFrame([
        {"Mã kho": code, "Tên kho": name}
        for code, name in WAREHOUSE_NAMES.items()
    ]), use_container_width=True, hide_index=True)
    st.markdown("### Quy tắc kho hợp lý theo địa chỉ")
    st.dataframe(pd.DataFrame([
        {"Nhóm địa chỉ": region, "Mã kho được chấp nhận": ", ".join(sorted(rule["warehouses"]))}
        for region, rule in ADDRESS_WAREHOUSE_RULES.items()
    ]), use_container_width=True, hide_index=True)
    st.caption("Nếu không khớp địa chỉ cụ thể, hệ thống mới dùng cột Miền2 làm quy tắc dự phòng và đánh dấu cần xác minh địa chỉ.")

with tab_sales:
    st.markdown('<div class="section-title">PHÂN TÍCH DOANH THU VÀ MẶT HÀNG</div>', unsafe_allow_html=True)
    st.caption("Chỉ phân tích doanh thu, sản lượng và khối lượng. Không sử dụng giá bán đơn vị, giá vốn hoặc lợi nhuận. Dòng mã hàng bắt đầu bằng Z được loại khỏi phân tích mặt hàng/doanh thu.")
    if not monthly_sales.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(monthly_sales, x="_thang", y="Doanh_thu", title="Doanh thu theo tháng")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(monthly_sales, x="_thang", y="San_luong", markers=True, title="Sản lượng theo tháng")
            st.plotly_chart(fig, use_container_width=True)
    if product_summary.empty:
        st.info("Không đủ cột mã hàng/tên hàng để lập cơ cấu mặt hàng.")
    else:
        top_n = st.slider("Số mặt hàng hiển thị", min_value=5, max_value=50, value=20, step=5)
        st.dataframe(
            product_summary.head(top_n).rename(columns={
                "_ma_hang": "Mã hàng", "_ten_hang": "Tên hàng",
                "Doanh_thu": "Doanh thu", "San_luong": "Sản lượng",
                "Khoi_luong": "Khối lượng", "So_NPP": "Số NPP",
                "So_chung_tu": "Số chứng từ"
            }),
            use_container_width=True, hide_index=True
        )
        fig = px.bar(
            product_summary.head(top_n).sort_values("Doanh_thu"),
            x="Doanh_thu", y="_ten_hang", orientation="h",
            title=f"Top {top_n} mặt hàng theo doanh thu"
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Cảnh báo biến động doanh thu/sản lượng")
    if len(monthly_sales) >= 3:
        trend = monthly_sales.copy()
        trend["Doanh_thu_TB_3T_truoc"] = trend["Doanh_thu"].shift(1).rolling(3, min_periods=2).mean()
        trend["San_luong_TB_3T_truoc"] = trend["San_luong"].shift(1).rolling(3, min_periods=2).mean()
        trend["Bien_dong_DT_%"] = np.where(
            trend["Doanh_thu_TB_3T_truoc"] > 0,
            (trend["Doanh_thu"] / trend["Doanh_thu_TB_3T_truoc"] - 1) * 100,
            np.nan
        )
        trend["Bien_dong_SL_%"] = np.where(
            trend["San_luong_TB_3T_truoc"] > 0,
            (trend["San_luong"] / trend["San_luong_TB_3T_truoc"] - 1) * 100,
            np.nan
        )
        alerts = trend[
            (trend["Bien_dong_DT_%"].abs() >= 50)
            | (trend["Bien_dong_SL_%"].abs() >= 50)
        ].copy()
        if alerts.empty:
            st.success("Chưa có tháng biến động từ 50% trở lên so với bình quân các tháng trước trong phạm vi dữ liệu.")
        else:
            st.dataframe(alerts, use_container_width=True, hide_index=True)
    else:
        st.info("Cần ít nhất 3 tháng dữ liệu để sàng lọc biến động theo xu hướng.")

with tab_warehouse:
    st.markdown('<div class="section-title">ĐỐI CHIẾU KHO LẤY HÀNG VỚI ĐỊA CHỈ NPP</div>', unsafe_allow_html=True)
    st.caption("Chỉ xét các dòng có hình thức vận chuyển là Xe khách hàng. Xe nhà máy và xe nhà máy thuê ngoài được loại khỏi phần này.")
    a, b, c = st.columns(3)
    a.metric("Dòng xe khách hàng", f"{len(customer_vehicle):,}")
    b.metric("Ngoài vùng ưu tiên", f"{len(warehouse_evidence):,}")
    c.metric("Kho HS Home / thiếu dữ liệu", f"{len(warehouse_special) + len(warehouse_unknown):,}")
    if not warehouse_counts.empty:
        st.dataframe(warehouse_counts, use_container_width=True, hide_index=True)
    st.markdown("### Giao dịch kho ngoài vùng ưu tiên")
    if warehouse_evidence.empty:
        st.success("Không có giao dịch ngoài vùng ưu tiên theo ma trận sàng lọc hiện tại.")
    else:
        st.warning(f"Có {len(warehouse_evidence):,} dòng cần xác minh khoảng cách, điều phối và lý do chọn kho.")
        st.dataframe(warehouse_evidence[[
            "_ten_kh", "_dia_chi", "_mien_goc", "_vung", "_chung_tu", "_ma_kho", "_ten_kho",
            "_doi_chieu_kho", "_ngay", "_bien_so_goc"
        ]].rename(columns={
            "_ten_kh": "NPP", "_dia_chi": "Địa chỉ", "_mien_goc": "Miền2 gốc",
            "_vung": "Vùng chuẩn hóa", "_ma_kho": "Mã kho trích từ chứng từ",
            "_ten_kho": "Tên kho theo danh mục", "_doi_chieu_kho": "Kết quả đối chiếu", "_ngay": "Ngày",
            "_chung_tu": "Chứng từ", "_bien_so_goc": "Số xe gốc"
        }), use_container_width=True, hide_index=True)
    st.markdown("### Kho hàng gửi tại HS Home của HSN Phú Mỹ")
    if warehouse_special.empty:
        st.info("Không có giao dịch thuộc mã kho HS Home (282/292).")
    else:
        st.warning("Không xếp 282/292 vào nhóm phù hợp vùng thông thường. Cần kiểm tra vị trí lưu hàng, phiếu nhập/xuất và đơn vị quản lý kho.")
        st.dataframe(warehouse_special[[
            "_ten_kh", "_dia_chi", "_vung", "_chung_tu", "_ma_kho", "_ten_kho",
            "_doi_chieu_kho", "_ngay", "_bien_so_goc"
        ]].rename(columns={
            "_ten_kh": "NPP", "_dia_chi": "Địa chỉ", "_vung": "Vùng",
            "_chung_tu": "Chứng từ", "_ma_kho": "Mã kho",
            "_ten_kho": "Tên kho", "_doi_chieu_kho": "Kết quả",
            "_ngay": "Ngày", "_bien_so_goc": "Biển số xe"
        }), use_container_width=True, hide_index=True)

    st.markdown("### Giao dịch chưa đủ dữ liệu")
    if warehouse_unknown.empty:
        st.success("Không có giao dịch kho thiếu thông tin.")
    else:
        st.dataframe(warehouse_unknown[[
            "_ten_kh", "_dia_chi", "_mien_goc", "_vung", "_chung_tu", "_ma_kho", "_ten_kho",
            "_doi_chieu_kho", "_ngay"
        ]], use_container_width=True, hide_index=True)
    st.markdown("### Cách xử lý đề xuất")
    st.write(
        "1. Xác minh địa chỉ NPP và vùng địa lý thực tế. "
        "2. Đối chiếu mã kho trích từ 3 số đầu chứng từ với tên kho trong danh mục và vùng địa chỉ NPP. "
        "3. Với mã kho ngoài vùng ưu tiên, kiểm tra khoảng cách thực tế, tuyến đường, năng lực kho, tồn kho và lý do điều phối. "
        "4. Với mã 282/292 (hàng gửi HS Home), kiểm tra riêng địa điểm lưu hàng, phiếu nhập/xuất và đơn vị quản lý. "
        "5. Chỉ kết luận bất thường sau khi đối chiếu hồ sơ, giải trình và phê duyệt ngoại lệ."
    )

with tab_vehicle:
    st.markdown('<div class="section-title">PHÂN TÍCH XE KHÁCH HÀNG DÙNG CHUNG</div>', unsafe_allow_html=True)
    st.caption("Hiện tại chỉ phân tích Xe khách hàng. Xe nhà máy và thuê ngoài được loại trừ; có thể bổ sung loại hình khác ở phiên bản sau.")
    a, b, c = st.columns(3)
    a.metric("Dòng xe khách hàng", f"{len(customer_vehicle):,}")
    b.metric("Xe nhiều NPP cùng ngày", f"{len(vehicle_day_shared):,}")
    c.metric("Xe nhiều NPP qua nhiều ngày", f"{len(vehicle_period_shared):,}")
    st.markdown("### Một xe phục vụ nhiều NPP trong cùng ngày")
    if vehicle_day_shared.empty:
        st.success("Chưa phát hiện xe hợp lệ phục vụ từ hai NPP trở lên trong cùng ngày.")
    else:
        st.dataframe(vehicle_day_shared.rename(columns={
            "_bien_so": "Biển số chuẩn hóa", "_ngay_only": "Ngày",
            "Bien_so_goc": "Biển số gốc", "So_NPP": "Số NPP",
            "Danh_sach_NPP": "Danh sách NPP", "So_chung_tu": "Số chứng từ",
            "So_kho": "Số kho", "So_dia_diem": "Số địa điểm",
            "So_giao_dich": "Số dòng giao dịch", "Danh_sach_kho": "Danh sách kho"
        }), use_container_width=True, hide_index=True)
    st.markdown("### Một xe phục vụ nhiều NPP qua nhiều ngày")
    if vehicle_period_shared.empty:
        st.success("Chưa phát hiện xe được nhiều NPP sử dụng trong các ngày khác nhau.")
    else:
        st.dataframe(vehicle_period_shared.rename(columns={
            "_bien_so": "Biển số chuẩn hóa", "Bien_so_goc": "Biển số gốc",
            "So_NPP": "Số NPP", "Danh_sach_NPP": "Danh sách NPP",
            "So_ngay_hoat_dong": "Số ngày hoạt động", "So_giao_dich": "Số dòng giao dịch",
            "Danh_sach_kho": "Danh sách kho"
        }), use_container_width=True, hide_index=True)
    st.markdown("### Xe khách hàng thiếu hoặc không nhận diện được biển số")
    invalid_vehicle = customer_vehicle[~customer_vehicle["_bien_so_hop_le"]]
    if invalid_vehicle.empty:
        st.success("Không có biển số thiếu/không đúng định dạng sàng lọc.")
    else:
        st.warning(f"{len(invalid_vehicle):,} dòng cần bổ sung hoặc xác minh biển số.")
        st.dataframe(invalid_vehicle[[
            "_ten_kh", "_ngay", "_chung_tu", "_bien_so_goc", "_dia_chi", "_ma_kho"
        ]].rename(columns={
            "_ten_kh": "NPP", "_ngay": "Ngày", "_chung_tu": "Chứng từ",
            "_bien_so_goc": "Giá trị số xe gốc", "_dia_chi": "Địa chỉ", "_ma_kho": "Mã kho"
        }), use_container_width=True, hide_index=True)
    st.markdown("### Hướng xác minh")
    st.write(
        "Cùng biển số trong cùng ngày là dấu hiệu cần kiểm tra, chưa đủ để kết luận bất thường. "
        "Đối chiếu giờ lấy hàng, số chứng từ, chủ xe, tài xế, người nhận và lộ trình. "
        "Trường hợp lặp lại qua nhiều ngày cần kiểm tra thỏa thuận vận chuyển và mối liên hệ giữa các NPP."
    )

with tab_risk:
    st.markdown('<div class="section-title">BẢNG ĐÁNH GIÁ VÀ NHẬN ĐỊNH RỦI RO NPP</div>', unsafe_allow_html=True)
    st.caption("Điểm là mức ưu tiên sàng lọc theo các tín hiệu quan sát được; không phải kết luận vi phạm.")
    if risk_summary.empty:
        st.info("Không có dữ liệu để lập bảng đánh giá.")
    else:
        st.dataframe(risk_summary, use_container_width=True, hide_index=True)
        options = risk_summary["NPP"].dropna().unique().tolist()
        if options:
            selected_npp = st.selectbox("Xem hồ sơ chi tiết NPP", options)
            detail = risk_summary[risk_summary["NPP"] == selected_npp].iloc[0]
            level = detail["Mức độ"]
            st.markdown(
                f'<div class="{RISK_CSS.get(level, "risk-unknown")}">'
                f'<b>{level.upper()} | {int(detail["Điểm sàng lọc"])}/100 điểm</b><br>'
                f'<b>Nhận định:</b> {detail["Nhận định"]}<br>'
                f'<b>Hướng xử lý:</b> {detail["Hướng xử lý"]}'
                f'</div>',
                unsafe_allow_html=True
            )
            evidence = filtered[filtered["_customer_key"] == detail["Mã khách hàng"]]
            st.markdown("### Giao dịch làm căn cứ")
            st.dataframe(evidence[[
                "_ngay", "_chung_tu", "_dia_chi", "_vung", "_ma_kho", "_ten_kho",
                "_doi_chieu_kho", "_loai_xe", "_bien_so_goc",
                "_doanh_thu", "_san_luong", "_ma_hang", "_ten_hang"
            ]].rename(columns={
                "_ngay": "Ngày", "_chung_tu": "Chứng từ", "_dia_chi": "Địa chỉ",
                "_vung": "Vùng", "_ma_kho": "Mã kho trích từ chứng từ", "_ten_kho": "Tên kho", "_doi_chieu_kho": "Đối chiếu kho",
                "_loai_xe": "Hình thức", "_bien_so_goc": "Số xe",
                "_doanh_thu": "Doanh thu", "_san_luong": "Sản lượng",
                "_ma_hang": "Mã hàng", "_ten_hang": "Tên hàng"
            }), use_container_width=True, hide_index=True)

    st.markdown("### Thang màu")
    cols = st.columns(5)
    legend = [
        ("XANH", "0–24 điểm", "risk-low"),
        ("VÀNG", "25–44 điểm", "risk-watch"),
        ("CAM", "45–64 điểm", "risk-high"),
        ("ĐỎ", "65–100 điểm", "risk-critical"),
        ("XÁM", "Chưa đủ dữ liệu", "risk-unknown"),
    ]
    for col, (title, desc, css) in zip(cols, legend):
        with col:
            st.markdown(f'<div class="risk-card {css}"><b>{title}</b><br>{desc}</div>', unsafe_allow_html=True)

with tab_unknown:
    st.markdown('<div class="section-title">DỮ LIỆU CHƯA NHẬN DIỆN / CHƯA ĐỦ CĂN CỨ</div>', unsafe_allow_html=True)
    st.caption("Các dòng này được tách riêng, không tự suy đoán và không dùng làm bằng chứng kết luận rủi ro.")
    if unrecognized.empty:
        st.success("Không phát hiện dòng thiếu dữ liệu theo các trường kiểm tra hiện tại.")
    else:
        reason_options = sorted(unrecognized["_nhom_chua_nhan_dien"].unique().tolist())
        selected_reasons = st.multiselect("Lọc theo lý do", reason_options, default=reason_options)
        unknown_view = unrecognized[unrecognized["_nhom_chua_nhan_dien"].isin(selected_reasons)]
        st.metric("Số dòng chưa nhận diện", f"{len(unknown_view):,}")
        st.dataframe(unknown_view[[
            "_ten_kh", "_loai_kh", "_ngay", "_chung_tu", "_dia_chi",
            "_mien_goc", "_vung", "_ma_kho", "_hinh_thuc_goc",
            "_bien_so_goc", "_nhom_chua_nhan_dien", "_ly_do_chua_nhan_dien"
        ]].rename(columns={
            "_ten_kh": "NPP", "_loai_kh": "Loại khách hàng", "_ngay": "Ngày",
            "_chung_tu": "Chứng từ", "_dia_chi": "Địa chỉ", "_mien_goc": "Miền2 gốc",
            "_vung": "Vùng nhận diện", "_ma_kho": "Mã kho trích từ chứng từ",
            "_ten_kho": "Tên kho theo danh mục", "_hinh_thuc_goc": "Hình thức gốc", "_bien_so_goc": "Số xe gốc",
            "_nhom_chua_nhan_dien": "Nhóm lỗi", "_ly_do_chua_nhan_dien": "Lý do"
        }), use_container_width=True, hide_index=True)

# ============================================================
# EXPORT
# ============================================================

st.markdown("---")
st.markdown('<div class="section-title">TẢI KẾT QUẢ PHÂN TÍCH</div>', unsafe_allow_html=True)

export_rows = filtered.copy()
export_sheets = {
    "Tong_hop_rui_ro": risk_summary,
    "Doanh_thu_mat_hang": product_summary,
    "Theo_thang": monthly_sales,
    "Kho_ngoai_vung_uu_tien": warehouse_evidence,
    "Kho_HS_Home_can_xac_minh": warehouse_special,
    "Kho_chua_du_du_lieu": warehouse_unknown,
    "Xe_cung_ngay": vehicle_day_shared,
    "Xe_nhieu_ngay": vehicle_period_shared,
    "Dia_chi_trung": address_shared,
    "Chua_nhan_dien": unrecognized,
    "Du_lieu_da_loc": export_rows,
}
try:
    excel_bytes = build_excel_export(export_sheets)
    st.download_button(
        "TẢI BÁO CÁO KIỂM SOÁT NPP (EXCEL)",
        data=excel_bytes,
        file_name="NPP_Business_Risk_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
except Exception as exc:
    st.error(f"Không tạo được file Excel xuất kết quả: {exc}")

st.caption(
    "Lưu ý: hệ thống sàng lọc dấu hiệu dựa trên dữ liệu được cung cấp. "
    "Cần đối chiếu chứng từ, xác minh thực tế và lấy giải trình trước khi kết luận. "
    "Các bản ghi chưa nhận diện được tách riêng, không mặc định là rủi ro thấp."
)
