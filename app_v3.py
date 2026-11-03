
import io
import re
import warnings
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

warnings.filterwarnings("ignore")

# ============================================================
# HOA SEN GROUP - NPP BUSINESS RISK ANALYTICS
# ============================================================

st.set_page_config(
    page_title="NPP Risk Analytics - Hoa Sen",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 1. GIAO DIỆN
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Be Vietnam Pro', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background: #07111e;
}

[data-testid="stHeader"] {
    background: transparent;
}

section[data-testid="stSidebar"] {
    background: #091626;
    border-right: 1px solid #1b2b40;
}

section[data-testid="stSidebar"] * {
    color: #d4e2f2;
}

.main-title {
    font-size: 27px;
    font-weight: 800;
    color: #e4efff;
}

.sub-title {
    font-size: 12px;
    color: #829ab5;
    margin-bottom: 18px;
}

.section-title {
    color: #70aaff;
    font-size: 14px;
    font-weight: 800;
    margin: 20px 0 10px;
    border-left: 3px solid #388bfd;
    padding-left: 9px;
}

.risk-red {
    background: #39191c;
    color: #ffb5b5;
    border-left: 4px solid #ef4444;
    padding: 12px;
    margin: 5px 0;
    border-radius: 5px;
}

.risk-orange {
    background: #3b2814;
    color: #ffd199;
    border-left: 4px solid #f97316;
    padding: 12px;
    margin: 5px 0;
    border-radius: 5px;
}

.risk-yellow {
    background: #39320f;
    color: #fff0a8;
    border-left: 4px solid #eab308;
    padding: 12px;
    margin: 5px 0;
    border-radius: 5px;
}

.risk-green {
    background: #102d22;
    color: #a7f3d0;
    border-left: 4px solid #22c55e;
    padding: 12px;
    margin: 5px 0;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. CẤU HÌNH NGHIỆP VỤ
# ============================================================

RISK_COLORS = {
    "Thấp": "#22c55e",
    "Theo dõi": "#eab308",
    "Cao": "#f97316",
    "Rất cao": "#ef4444"
}

RISK_ORDER = ["Thấp", "Theo dõi", "Cao", "Rất cao"]

VEHICLE_CLASSES = [
    "Xe khách hàng",
    "Xe nhà máy",
    "Thuê ngoài",
    "Khác / Chưa xác định"
]

# Danh sách kho được phép theo yêu cầu

DEFAULT_WAREHOUSE_RULES = {
    "Miền Nam và Tây Nam Bộ": ["053", "281", "284", "054"],
    "Miền Trung và Tây Nguyên": [
        "053", "252", "251", "261", "263", "284", "291"
    ],
    "Miền Bắc": ["291", "261"]
}

# Bao gồm tên tỉnh trước và sau sắp xếp hành chính.
# Có thể điều chỉnh thêm tại Sidebar.

DEFAULT_REGION_ALIASES = {
    "Miền Nam và Tây Nam Bộ": """
    Hồ Chí Minh; TP.HCM; TPHCM; Sài Gòn; Bình Dương;
    Bà Rịa Vũng Tàu; Bà Rịa; Vũng Tàu; Đồng Nai; Bình Phước;
    Tây Ninh; Long An; Tiền Giang; Bến Tre; Trà Vinh;
    Vĩnh Long; Đồng Tháp; An Giang; Kiên Giang; Cần Thơ;
    Hậu Giang; Sóc Trăng; Bạc Liêu; Cà Mau
    """,

    "Miền Trung và Tây Nguyên": """
    Thanh Hóa; Nghệ An; Hà Tĩnh; Quảng Bình; Quảng Trị;
    Thừa Thiên Huế; Huế; Đà Nẵng; Quảng Nam; Quảng Ngãi;
    Kon Tum; Bình Định; Gia Lai; Phú Yên; Đắk Lắk;
    Đắk Nông; Khánh Hòa; Ninh Thuận; Bình Thuận; Lâm Đồng
    """,

    "Miền Bắc": """
    Hà Nội; Cao Bằng; Tuyên Quang; Hà Giang; Điện Biên;
    Lai Châu; Sơn La; Lào Cai; Yên Bái; Thái Nguyên;
    Bắc Kạn; Lạng Sơn; Quảng Ninh; Bắc Ninh; Bắc Giang;
    Phú Thọ; Vĩnh Phúc; Hòa Bình; Hải Phòng; Hải Dương;
    Hưng Yên; Thái Bình; Ninh Bình; Hà Nam; Nam Định
    """
}


# ============================================================
# 3. TÊN CỘT CÓ THỂ NHẬN DIỆN
# ============================================================

COLUMN_ALIASES = {
    "customer": [
        "Tên khách hàng", "Tên KH", "Khách hàng",
        "Customer", "Customer Name"
    ],

    "customer_id": [
        "Mã khách hàng", "Mã KH", "Customer Code",
        "Customer ID"
    ],

    "customer_group": [
        "Tên nhóm KH", "Mã nhóm KH", "Nhóm khách hàng",
        "Loại khách hàng", "Loại KH", "Customer Group"
    ],

    "date": [
        "Ngày chứng từ", "Ngày xuất", "Ngày lấy hàng",
        "Ngày giao hàng", "Document Date", "Posting Date"
    ],

    "document": [
        "Số chứng từ", "Số CT", "Số phiếu",
        "Document No", "Invoice No"
    ],

    "revenue": [
        "Thành tiền bán", "Doanh thu",
        "Thành tiền", "Sales Amount", "Amount"
    ],

    "quantity": [
        "Số lượng", "SL", "Quantity"
    ],

    "weight": [
        "Khối lượng", "KL", "Trọng lượng", "Weight"
    ],

    "item_code": [
        "Mã hàng", "Mã SP", "Mã sản phẩm",
        "Item Code", "SKU"
    ],

    "item_name": [
        "Tên hàng", "Tên sản phẩm",
        "Item Name", "Product Name"
    ],

    "location": [
        "Địa điểm", "Địa điểm khách hàng",
        "Địa điểm giao hàng", "Địa chỉ khách hàng",
        "Địa chỉ", "Địa chỉ KH", "Nơi giao hàng"
    ],

    "warehouse": [
        "Mã kho", "Mã kho xuất", "Kho xuất",
        "Kho lấy hàng", "Địa điểm xuất",
        "Warehouse", "Storage Location", "Plant"
    ],

    "shipping_method": [
        "Shipping method", "Hình thức vận chuyển",
        "Phương thức vận chuyển", "Loại vận chuyển"
    ],

    "vehicle": [
        "Biển số xe", "Số xe", "Xe khách hàng",
        "Biển kiểm soát", "Vehicle No", "License Plate"
    ],

    "note": [
        "Ghi chú", "Diễn giải", "Remark", "Notes"
    ],

    "order_type": [
        "Loại đơn hàng", "Loại giao dịch",
        "Transaction Type"
    ]
}


# ============================================================
# 4. CÁC HÀM CHUẨN HÓA
# ============================================================

def normalize_text(value):
    if pd.isna(value):
        return ""

    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_text(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.lower() in ["nan", "none", "null"]:
        return ""

    return value


def clean_vehicle(value):
    if pd.isna(value):
        return ""

    value = str(value).upper().strip()
    value = re.sub(r"[^A-Z0-9]", "", value)

    if value in ["NAN", "NONE", "NULL"]:
        return ""

    return value


def number_value(value):
    """Chuyển số có dấu phân cách Việt Nam/Anh thành số."""

    if pd.isna(value):
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
        parts = text.split(",")

        if len(parts[-1]) <= 2:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return 0.0


def numeric_series(series):
    return series.apply(number_value)


def clean_warehouse_code(value):
    """Chuẩn hóa 53, 53.0, 053 hoặc Kho 053 thành 053."""

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in ["", "nan", "none", "null"]:
        return ""

    match = re.search(
        r"(?<!\d)(\d{1,3})(?:\.0+)?(?!\d)",
        text
    )

    if not match:
        return ""

    return match.group(1).zfill(3)


def split_values(value):
    return [
        x.strip()
        for x in re.split(r"[,;\n]+", str(value))
        if x.strip()
    ]


def unique_join(series):
    values = sorted({
        str(x).strip()
        for x in series
        if pd.notna(x) and str(x).strip()
    })

    return "; ".join(values)


def risk_level(score):
    if score >= 65:
        return "Rất cao"

    if score >= 45:
        return "Cao"

    if score >= 25:
        return "Theo dõi"

    return "Thấp"


def format_number(value):
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "0"


def find_column(columns, aliases):
    normalized = {
        normalize_text(c): c
        for c in columns
    }

    for alias in aliases:
        key = normalize_text(alias)

        if key in normalized:
            return normalized[key]

    for alias in aliases:
        key = normalize_text(alias)

        for norm_col, original in normalized.items():
            if key and key in norm_col:
                return original

    return None


# ============================================================
# 5. ĐỌC FILE EXCEL
# ============================================================

HEADER_KEYWORDS = [
    "ten khach hang",
    "ma khach hang",
    "ngay chung tu",
    "dia diem",
    "ma kho",
    "ten hang",
    "shipping method",
    "thanh tien ban",
    "so luong"
]


def detect_header_row(file_bytes, sheet_name):
    raw = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name=sheet_name,
        header=None,
        nrows=40,
        engine="openpyxl"
    )

    best_row = 0
    best_score = 0

    for idx in range(len(raw)):
        values = [
            normalize_text(v)
            for v in raw.iloc[idx].tolist()
        ]

        joined = " ".join(values)

        score = sum(
            keyword in joined
            for keyword in HEADER_KEYWORDS
        )

        if score > best_score:
            best_score = score
            best_row = idx

    return best_row


def unique_columns(columns):
    seen = {}
    output = []

    for col in columns:
        name = str(col).strip().replace("\n", " ")

        if not name or name.lower() == "nan":
            name = "Column"

        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0

        output.append(name)

    return output


def read_excel_files(files):
    frames = []
    errors = []

    for uploaded in files:
        file_bytes = uploaded.getvalue()

        try:
            excel = pd.ExcelFile(
                io.BytesIO(file_bytes),
                engine="openpyxl"
            )

            for sheet_name in excel.sheet_names:
                try:
                    header = detect_header_row(
                        file_bytes,
                        sheet_name
                    )

                    data = pd.read_excel(
                        io.BytesIO(file_bytes),
                        sheet_name=sheet_name,
                        header=header,
                        engine="openpyxl"
                    )

                    data.columns = unique_columns(data.columns)
                    data = data.dropna(how="all")

                    if data.empty:
                        continue

                    data["_File"] = uploaded.name
                    data["_Sheet"] = sheet_name

                    frames.append(data)

                except Exception as exc:
                    errors.append(
                        f"{uploaded.name} / {sheet_name}: {exc}"
                    )

        except Exception as exc:
            errors.append(f"{uploaded.name}: {exc}")

    if not frames:
        return pd.DataFrame(), errors

    result = pd.concat(
        frames,
        ignore_index=True,
        sort=False
    )

    result = result.loc[
        :, ~result.columns.duplicated()
    ].copy()

    return result, errors


# ============================================================
# 6. XÁC ĐỊNH VÙNG ĐỊA LÝ
# ============================================================

def build_region_aliases(config):
    output = {}

    for region, text in config.items():
        aliases = split_values(text)

        output[region] = sorted(
            {
                normalize_text(x)
                for x in aliases
                if normalize_text(x)
            },
            key=len,
            reverse=True
        )

    return output


def detect_region(address, aliases):
    address_norm = normalize_text(address)

    if not address_norm:
        return "Thiếu địa điểm"

    padded = f" {address_norm} "

    for region, names in aliases.items():
        for name in names:
            if f" {name} " in padded:
                return region

    return "Chưa xác định vùng"


# ============================================================
# 7. KIỂM TRA VÀ XỬ LÝ DỮ LIỆU
# ============================================================

def process_data(
    raw,
    customer_col,
    customer_id_col,
    date_col,
    location_col,
    warehouse_col,
    shipping_col,
    vehicle_col,
    revenue_col,
    quantity_col,
    weight_col,
    item_code_col,
    item_name_col,
    document_col,
    group_col,
    note_col,
    order_type_col
):

    data = raw.copy()

    data["_customer_name"] = data[customer_col].apply(
        clean_text
    )

    if customer_id_col:
        data["_customer_id"] = data[customer_id_col].apply(
            clean_text
        )

        data["_customer_key"] = np.where(
            data["_customer_id"].ne(""),
            "ID:" + data["_customer_id"],
            "NAME:" + data["_customer_name"].apply(normalize_text)
        )
    else:
        data["_customer_key"] = (
            "NAME:" + data["_customer_name"].apply(normalize_text)
        )

    data["_date"] = pd.to_datetime(
        data[date_col],
        dayfirst=True,
        errors="coerce"
    )

    data = data[
        data["_date"].notna()
        & data["_customer_name"].ne("")
    ].copy()

    data["_date_only"] = data["_date"].dt.date
    data["_month"] = data["_date"].dt.to_period("M").astype(str)

    data["_address"] = data[location_col].apply(clean_text)
    data["_address_norm"] = data["_address"].apply(normalize_text)

    data["_warehouse_raw"] = data[warehouse_col].apply(clean_text)
    data["_warehouse_code"] = data["_warehouse_raw"].apply(
        clean_warehouse_code
    )

    data["_method"] = data[shipping_col].apply(clean_text)
    data["_vehicle_raw"] = data[vehicle_col].apply(clean_text)
    data["_vehicle_norm"] = data["_vehicle_raw"].apply(clean_vehicle)

    data["_revenue"] = (
        numeric_series(data[revenue_col])
        if revenue_col else 0.0
    )

    data["_quantity"] = (
        numeric_series(data[quantity_col])
        if quantity_col else 0.0
    )

    data["_weight"] = (
        numeric_series(data[weight_col])
        if weight_col else 0.0
    )

    return data


# ============================================================
# 8. HEADER ỨNG DỤNG
# ============================================================

st.markdown("""
<div class="main-title">NPP BUSINESS RISK ANALYTICS</div>
<div class="sub-title">
HOA SEN GROUP | PHÂN TÍCH RỦI RO NHÀ PHÂN PHỐI
</div>
""", unsafe_allow_html=True)


# ============================================================
# 9. UPLOAD FILE
# ============================================================

with st.sidebar:
    st.markdown("## 📂 DỮ LIỆU")

    uploaded_files = st.file_uploader(
        "Tải file Excel báo cáo bán hàng",
        type=["xlsx"],
        accept_multiple_files=True
    )

if not uploaded_files:
    st.info("Tải file Excel để bắt đầu phân tích.")
    st.stop()

RAW, READ_ERRORS = read_excel_files(uploaded_files)

if RAW.empty:
    st.error("Không đọc được dữ liệu từ file Excel.")
    st.stop()

if READ_ERRORS:
    with st.expander("Các sheet/file gặp lỗi"):
        for error in READ_ERRORS:
            st.write(error)

COLUMNS = RAW.columns.tolist()


# ============================================================
# 10. CHỌN CỘT
# ============================================================

def choose_column(label, key, required=False):
    detected = find_column(
        COLUMNS,
        COLUMN_ALIASES[key]
    )

    options = ["-- Không chọn --"] + COLUMNS

    default_index = (
        options.index(detected)
        if detected in options
        else 0
    )

    selected = st.selectbox(
        label,
        options,
        index=default_index,
        key=f"column_{key}"
    )

    if selected == "-- Không chọn --":
        if required:
            st.warning(f"Bạn cần chọn cột {label}.")
        return None

    return selected


with st.sidebar:
    st.markdown("---")
    st.markdown("## 🧩 ÁNH XẠ CỘT")

    customer_col = choose_column("Tên khách hàng", "customer", True)
    customer_id_col = choose_column("Mã khách hàng", "customer_id")
    group_col = choose_column("Nhóm khách hàng", "customer_group")
    date_col = choose_column("Ngày chứng từ", "date", True)
    document_col = choose_column("Số chứng từ", "document")

    location_col = choose_column(
        "Địa điểm (địa chỉ NPP)",
        "location",
        True
    )

    warehouse_col = choose_column(
        "Mã kho / Kho xuất",
        "warehouse",
        True
    )

    shipping_col = choose_column(
        "Hình thức vận chuyển",
        "shipping_method",
        True
    )

    vehicle_col = choose_column(
        "Biển số xe",
        "vehicle",
        True
    )

    revenue_col = choose_column("Doanh thu", "revenue")
    quantity_col = choose_column("Số lượng", "quantity")
    weight_col = choose_column("Khối lượng", "weight")
    item_code_col = choose_column("Mã hàng", "item_code")
    item_name_col = choose_column("Tên hàng", "item_name")
    note_col = choose_column("Ghi chú", "note")
    order_type_col = choose_column("Loại giao dịch", "order_type")

if not all([
    customer_col,
    date_col,
    location_col,
    warehouse_col,
    shipping_col,
    vehicle_col
]):
    st.error(
        "Cần chọn đủ các cột: Tên khách hàng, Ngày chứng từ, "
        "Địa điểm, Mã kho, Hình thức vận chuyển và Biển số xe."
    )
    st.stop()


# ============================================================
# 11. LỌC ĐÚNG KHÁCH HÀNG NPP
# ============================================================

BASE = RAW.copy()
BASE["_customer_name"] = BASE[customer_col].apply(clean_text)

if group_col:
    group_options = sorted(
        BASE[group_col].dropna().astype(str).unique()
    )

    default_groups = [
        x for x in group_options
        if (
            "npp" in normalize_text(x)
            or "nha phan phoi" in normalize_text(x)
        )
    ]

    with st.sidebar:
        st.markdown("---")
        st.markdown("## 🏢 PHẠM VI NPP")

        selected_groups = st.multiselect(
            "Chọn nhóm Nhà Phân Phối",
            group_options,
            default=default_groups
        )

    if not selected_groups:
        st.warning("Chọn nhóm khách hàng NPP trước khi phân tích.")
        st.stop()

    BASE = BASE[
        BASE[group_col].astype(str).isin(selected_groups)
    ].copy()

else:
    with st.sidebar:
        confirm_npp = st.checkbox(
            "Tôi xác nhận file này chỉ chứa Nhà Phân Phối",
            value=False
        )

    if not confirm_npp:
        st.warning(
            "File không có cột nhóm khách hàng. "
            "Cần xác nhận dữ liệu chỉ bao gồm NPP."
        )
        st.stop()


# ============================================================
# 12. LOẠI MÃ HÀNG Z VÀ HÀNG CHIẾT KHẤU
# ============================================================

rows_before_filter = len(BASE)

removed_z = 0
removed_discount = 0

if item_code_col:
    code = BASE[item_code_col].fillna("").astype(str).str.strip()

    mask_z = code.str.upper().str.startswith("Z", na=False)

    removed_z = int(mask_z.sum())

    BASE = BASE[~mask_z].copy()

if item_name_col:
    item_norm = BASE[item_name_col].apply(normalize_text)

    mask_discount = item_norm.str.contains(
        "chiet khau",
        na=False
    )

    removed_discount = int(mask_discount.sum())

    BASE = BASE[~mask_discount].copy()


# ============================================================
# 13. TÙY CHỌN LOẠI GIAO DỊCH TRẢ HÀNG
# ============================================================

if note_col:
    note_norm = BASE[note_col].apply(normalize_text)
else:
    note_norm = pd.Series("", index=BASE.index)

if order_type_col:
    order_norm = BASE[order_type_col].apply(normalize_text)
else:
    order_norm = pd.Series("", index=BASE.index)

return_mask = (
    note_norm.str.contains(
        r"nhap tra|tra hang|huy hoa don",
        regex=True,
        na=False
    )
    |
    order_norm.str.contains(
        r"tra hang|huy hd|nhap tra",
        regex=True,
        na=False
    )
)

if revenue_col:
    return_mask |= numeric_series(BASE[revenue_col]) < 0

if quantity_col:
    return_mask |= numeric_series(BASE[quantity_col]) < 0

with st.sidebar:
    exclude_returns = st.checkbox(
        "Loại giao dịch trả hàng / hủy / số âm",
        value=True
    )

removed_returns = int(return_mask.sum()) if exclude_returns else 0

if exclude_returns:
    BASE = BASE[~return_mask].copy()


# ============================================================
# 14. CHUẨN HÓA TOÀN BỘ DỮ LIỆU
# ============================================================

DF = process_data(
    BASE,
    customer_col,
    customer_id_col,
    date_col,
    location_col,
    warehouse_col,
    shipping_col,
    vehicle_col,
    revenue_col,
    quantity_col,
    weight_col,
    item_code_col,
    item_name_col,
    document_col,
    group_col,
    note_col,
    order_type_col
)

if DF.empty:
    st.error("Không có dữ liệu hợp lệ sau khi làm sạch.")
    st.stop()


# ============================================================
# 15. PHÂN LOẠI HÌNH THỨC VẬN CHUYỂN
# ============================================================

def suggest_vehicle_class(value):
    text = normalize_text(value)

    if any(x in text for x in [
        "thue ngoai", "xe thue", "outsourced"
    ]):
        return "Thuê ngoài"

    if any(x in text for x in [
        "xe nha may", "nha may", "factory"
    ]):
        return "Xe nhà máy"

    if any(x in text for x in [
        "xe khach hang", "khach hang", "khach tu lay",
        "xe kh", "npp", "customer"
    ]):
        return "Xe khách hàng"

    return "Khác / Chưa xác định"


method_values = sorted(
    DF["_method"].dropna().astype(str).unique()
)

method_config = pd.DataFrame({
    "Hình thức vận chuyển": method_values,
    "Phân loại": [
        suggest_vehicle_class(x)
        for x in method_values
    ]
})

st.markdown(
    '<div class="section-title">PHÂN LOẠI PHƯƠNG TIỆN VẬN CHUYỂN</div>',
    unsafe_allow_html=True
)

st.caption(
    "Kiểm tra và điều chỉnh phân loại trước khi chạy. "
    "Chỉ hình thức được xác định là Xe khách hàng được phân tích. "
    "Xe nhà máy, thuê ngoài và chưa xác định sẽ bị loại khỏi module xe."
)

method_config = st.data_editor(
    method_config,
    use_container_width=True,
    hide_index=True,
    disabled=["Hình thức vận chuyển"],
    column_config={
        "Phân loại": st.column_config.SelectboxColumn(
            "Phân loại",
            options=VEHICLE_CLASSES,
            required=True
        )
    },
    key="method_config"
)

method_map = dict(
    zip(
        method_config["Hình thức vận chuyển"],
        method_config["Phân loại"]
    )
)

DF["_vehicle_class"] = (
    DF["_method"].map(method_map)
    .fillna("Khác / Chưa xác định")
)

# Chỉ dùng xe khách hàng.
CUSTOMER_CAR = DF[
    DF["_vehicle_class"] == "Xe khách hàng"
].copy()

FACTORY_CAR = DF[
    DF["_vehicle_class"] == "Xe nhà máy"
].copy()

OUTSOURCE_CAR = DF[
    DF["_vehicle_class"] == "Thuê ngoài"
].copy()

UNKNOWN_CAR = DF[
    DF["_vehicle_class"] == "Khác / Chưa xác định"
].copy()


# ============================================================
# 16. CẤU HÌNH ĐỊA BÀN
# ============================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("## 🗺️ CẤU HÌNH VÙNG")

    region_config = {}

    for region, default_text in DEFAULT_REGION_ALIASES.items():
        region_config[region] = st.text_area(
            region,
            value=default_text.strip(),
            height=100,
            key=f"region_{region}"
        )

region_aliases = build_region_aliases(region_config)


# ============================================================
# 17. CẤU HÌNH KHO
# ============================================================

with st.sidebar:
    st.markdown("## 🏭 DANH SÁCH MÃ KHO")

    warehouse_config = {}

    for region, codes in DEFAULT_WAREHOUSE_RULES.items():
        warehouse_config[region] = st.text_input(
            region,
            value=", ".join(codes),
            key=f"warehouse_{region}"
        )

warehouse_rules = {
    region: {
        clean_warehouse_code(code)
        for code in split_values(text)
        if clean_warehouse_code(code)
    }
    for region, text in warehouse_config.items()
}


# ============================================================
# 18. XÁC ĐỊNH VÙNG VÀ ĐỐI CHIẾU KHO
# ============================================================

DF["_region"] = DF["_address"].apply(
    lambda x: detect_region(x, region_aliases)
)

DF["_warehouse_status"] = "Không áp dụng"

CUSTOMER_CAR = DF[
    DF["_vehicle_class"] == "Xe khách hàng"
].copy()


def check_warehouse(row):
    region = row["_region"]
    code = row["_warehouse_code"]

    if not code:
        return "Thiếu mã kho"

    if region == "Thiếu địa điểm":
        return "Thiếu địa điểm"

    if region == "Chưa xác định vùng":
        return "Chưa xác định vùng"

    allowed = warehouse_rules.get(region, set())

    if not allowed:
        return "Chưa cấu hình danh sách kho"

    if code in allowed:
        return "Trong danh sách"

    return "Ngoài danh sách"


CUSTOMER_CAR["_warehouse_status"] = CUSTOMER_CAR.apply(
    check_warehouse,
    axis=1
)


# ============================================================
# 19. BỘ LỌC THỜI GIAN
# ============================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("## 🔍 BỘ LỌC")

    min_date = DF["_date"].min().date()
    max_date = DF["_date"].max().date()

    date_range = st.date_input(
        "Khoảng thời gian",
        value=(min_date, max_date)
    )

    daily_threshold = st.number_input(
        "Số chứng từ/ngày cảnh báo",
        min_value=2,
        max_value=100,
        value=5
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

DF = DF[
    (DF["_date"].dt.date >= start_date)
    & (DF["_date"].dt.date <= end_date)
].copy()

CUSTOMER_CAR = CUSTOMER_CAR[
    (CUSTOMER_CAR["_date"].dt.date >= start_date)
    & (CUSTOMER_CAR["_date"].dt.date <= end_date)
].copy()

if DF.empty:
    st.warning("Không có dữ liệu trong kỳ đã chọn.")
    st.stop()


# ============================================================
# 20. PHÂN TÍCH NPP TRÙNG ĐỊA CHỈ
# ============================================================

ADDRESS_DATA = DF[
    DF["_address_norm"].ne("")
].copy()

ADDRESS_PAIRS = ADDRESS_DATA[
    ["_customer_key", "_customer_name", "_address", "_address_norm"]
].drop_duplicates(
    subset=["_customer_key", "_address_norm"]
)

if not ADDRESS_PAIRS.empty:

    ADDRESS_GROUP = (
        ADDRESS_PAIRS.groupby("_address_norm")
        .agg(
            Dia_diem=("_address", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_join)
        )
        .reset_index()
    )

    ADDRESS_GROUP = ADDRESS_GROUP[
        ADDRESS_GROUP["So_NPP"] >= 2
    ].sort_values(
        "So_NPP",
        ascending=False
    )

    address_count_map = (
        ADDRESS_GROUP.set_index("_address_norm")["So_NPP"]
    )

    ADDRESS_PAIRS["_address_npp_count"] = (
        ADDRESS_PAIRS["_address_norm"]
        .map(address_count_map)
        .fillna(1)
    )

    CUSTOMER_ADDRESS_MAX = (
        ADDRESS_PAIRS.groupby("_customer_key")
        ["_address_npp_count"].max()
    )

else:
    ADDRESS_GROUP = pd.DataFrame()
    CUSTOMER_ADDRESS_MAX = pd.Series(dtype=float)


# ============================================================
# 21. MỘT XE - NHIỀU NPP - CÙNG NGÀY
# ============================================================

VEHICLE_DATA = CUSTOMER_CAR[
    CUSTOMER_CAR["_vehicle_norm"].ne("")
].copy()

if not VEHICLE_DATA.empty:

    VEHICLE_DAY_ALL = (
        VEHICLE_DATA.groupby(
            ["_vehicle_norm", "_date_only"]
        )
        .agg(
            Bien_so=("_vehicle_raw", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_join),
            So_dia_diem=("_address_norm", "nunique"),
            So_kho=("_warehouse_code", "nunique"),
            So_giao_dich=("_customer_name", "size"),
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum")
        )
        .reset_index()
    )

    VEHICLE_DAY = VEHICLE_DAY_ALL[
        VEHICLE_DAY_ALL["So_NPP"] >= 2
    ].copy()

    per_day_customer = VEHICLE_DATA.merge(
        VEHICLE_DAY_ALL[
            ["_vehicle_norm", "_date_only", "So_NPP"]
        ],
        on=["_vehicle_norm", "_date_only"],
        how="left"
    )

    CUSTOMER_VEHICLE_DAY_MAX = (
        per_day_customer.groupby("_customer_key")["So_NPP"]
        .max()
    )

else:
    VEHICLE_DAY_ALL = pd.DataFrame()
    VEHICLE_DAY = pd.DataFrame()
    CUSTOMER_VEHICLE_DAY_MAX = pd.Series(dtype=float)


# ============================================================
# 22. MỘT XE - NHIỀU NPP - NHIỀU NGÀY
# ============================================================

if not VEHICLE_DATA.empty:

    VEHICLE_PERIOD_ALL = (
        VEHICLE_DATA.groupby("_vehicle_norm")
        .agg(
            Bien_so=("_vehicle_raw", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_join),
            So_ngay_hoat_dong=("_date_only", "nunique"),
            So_dia_diem=("_address_norm", "nunique"),
            So_kho=("_warehouse_code", "nunique"),
            So_giao_dich=("_customer_name", "size"),
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum")
        )
        .reset_index()
    )

    VEHICLE_PERIOD = VEHICLE_PERIOD_ALL[
        VEHICLE_PERIOD_ALL["So_NPP"] >= 2
    ].sort_values(
        ["So_NPP", "So_ngay_hoat_dong"],
        ascending=False
    )

    per_vehicle_customer = VEHICLE_DATA.merge(
        VEHICLE_PERIOD_ALL[
            ["_vehicle_norm", "So_NPP"]
        ],
        on="_vehicle_norm",
        how="left"
    )

    CUSTOMER_VEHICLE_PERIOD_MAX = (
        per_vehicle_customer.groupby("_customer_key")["So_NPP"]
        .max()
    )

else:
    VEHICLE_PERIOD_ALL = pd.DataFrame()
    VEHICLE_PERIOD = pd.DataFrame()
    CUSTOMER_VEHICLE_PERIOD_MAX = pd.Series(dtype=float)


# ============================================================
# 23. MỘT NPP - NHIỀU KHO TRONG CÙNG NGÀY
# ============================================================

if not CUSTOMER_CAR.empty:

    warehouse_daily = (
        CUSTOMER_CAR[
            CUSTOMER_CAR["_warehouse_code"].ne("")
        ]
        .groupby(["_customer_key", "_date_only"])
        ["_warehouse_code"]
        .nunique()
    )

    CUSTOMER_MULTI_WAREHOUSE_MAX = (
        warehouse_daily.groupby("_customer_key").max()
    )

else:
    CUSTOMER_MULTI_WAREHOUSE_MAX = pd.Series(dtype=float)


# ============================================================
# 24. TẦN SUẤT LẤY HÀNG
# ============================================================

if not CUSTOMER_CAR.empty:

    if document_col:
        DAILY_ACTIVITY = (
            CUSTOMER_CAR.groupby(
                ["_customer_key", "_customer_name", "_date_only"]
            )[document_col]
            .nunique()
            .reset_index(name="So_chung_tu_ngay")
        )

    else:
        DAILY_ACTIVITY = (
            CUSTOMER_CAR.groupby(
                ["_customer_key", "_customer_name", "_date_only"]
            )
            .size()
            .reset_index(name="So_chung_tu_ngay")
        )

    CUSTOMER_DAILY_MAX = (
        DAILY_ACTIVITY.groupby("_customer_key")
        ["So_chung_tu_ngay"].max()
    )

else:
    DAILY_ACTIVITY = pd.DataFrame()
    CUSTOMER_DAILY_MAX = pd.Series(dtype=float)


# ============================================================
# 25. PHÁT HIỆN CHỨNG TỪ / DÒNG HÀNG TRÙNG
# ============================================================

duplicate_keys = [
    "_customer_key",
    "_date_only"
]

if document_col:
    duplicate_keys.append(document_col)

if item_code_col:
    duplicate_keys.append(item_code_col)
elif item_name_col:
    duplicate_keys.append(item_name_col)

duplicate_keys += [
    "_quantity",
    "_revenue"
]

if document_col:
    DUPLICATE_ROWS = DF[
        DF.duplicated(
            subset=duplicate_keys,
            keep=False
        )
    ].copy()

else:
    DUPLICATE_ROWS = DF.iloc[0:0].copy()

if not DUPLICATE_ROWS.empty:
    CUSTOMER_DUPLICATE_COUNT = (
        DUPLICATE_ROWS.groupby("_customer_key").size()
    )
else:
    CUSTOMER_DUPLICATE_COUNT = pd.Series(dtype=float)


# ============================================================
# 26. BẤT THƯỜNG SẢN LƯỢNG THEO THÁNG
# ============================================================

MONTHLY_CUSTOMER = (
    DF.groupby(["_customer_key", "_month"])
    .agg(
        Doanh_thu=("_revenue", "sum"),
        San_luong=("_quantity", "sum"),
        Khoi_luong=("_weight", "sum")
    )
    .reset_index()
)

SPIKE_CUSTOMERS = set()
SPIKE_DETAILS = []

for customer_key, group in MONTHLY_CUSTOMER.groupby("_customer_key"):

    group = group.sort_values("_month")

    if len(group) < 4:
        continue

    quantities = group["San_luong"].astype(float)

    for i in range(3, len(group)):

        history = quantities.iloc[:i]
        current = quantities.iloc[i]

        baseline = history[history > 0].median()

        if baseline <= 0:
            continue

        if current >= 3 * baseline and current > 0:

            SPIKE_CUSTOMERS.add(customer_key)

            SPIKE_DETAILS.append({
                "Mã NPP": customer_key,
                "Tháng": group.iloc[i]["_month"],
                "Sản lượng tháng": current,
                "Trung vị các tháng trước": baseline,
                "Lần mức bình thường": current / baseline
            })

SPIKE_TABLE = pd.DataFrame(SPIKE_DETAILS)


# ============================================================
# 27. TỔNG HỢP THÔNG TIN TỪNG NPP
# ============================================================

CUSTOMER_SUMMARY = (
    DF.groupby("_customer_key")
    .agg(
        NPP=("_customer_name", "first"),
        Doanh_thu=("_revenue", "sum"),
        San_luong=("_quantity", "sum"),
        Khoi_luong=("_weight", "sum"),
        So_ngay_mua=("_date_only", "nunique"),
        So_giao_dich=("_customer_name", "size"),
        Dia_diem=("_address", "first"),
        Ti_le_thieu_dia_diem=(
            "_address_norm",
            lambda x: (x == "").mean()
        )
    )
    .reset_index()
)

CUSTOMER_SUMMARY["So_NPP_cung_dia_diem"] = (
    CUSTOMER_SUMMARY["_customer_key"]
    .map(CUSTOMER_ADDRESS_MAX)
    .fillna(1)
)

CUSTOMER_SUMMARY["So_NPP_cung_xe_cung_ngay"] = (
    CUSTOMER_SUMMARY["_customer_key"]
    .map(CUSTOMER_VEHICLE_DAY_MAX)
    .fillna(1)
)

CUSTOMER_SUMMARY["So_NPP_cung_xe_trong_ky"] = (
    CUSTOMER_SUMMARY["_customer_key"]
    .map(CUSTOMER_VEHICLE_PERIOD_MAX)
    .fillna(1)
)

CUSTOMER_SUMMARY["So_kho_max_cung_ngay"] = (
    CUSTOMER_SUMMARY["_customer_key"]
    .map(CUSTOMER_MULTI_WAREHOUSE_MAX)
    .fillna(1)
)

CUSTOMER_SUMMARY["Max_chung_tu_ngay"] = (
    CUSTOMER_SUMMARY["_customer_key"]
    .map(CUSTOMER_DAILY_MAX)
    .fillna(0)
)

CUSTOMER_SUMMARY["So_dong_trung"] = (
    CUSTOMER_SUMMARY["_customer_key"]
    .map(CUSTOMER_DUPLICATE_COUNT)
    .fillna(0)
)

CUSTOMER_SUMMARY["Bien_dong_san_luong"] = (
    CUSTOMER_SUMMARY["_customer_key"].isin(SPIKE_CUSTOMERS)
)


# ============================================================
# 28. RỦI RO KHO - CHỈ XÉT XE KHÁCH HÀNG
# ============================================================

if not CUSTOMER_CAR.empty:

    WAREHOUSE_SUMMARY = (
        CUSTOMER_CAR.groupby("_customer_key")
        .agg(
            So_dong_xe_kh=("_customer_name", "size"),
            So_kho_ngoai_danh_sach=(
                "_warehouse_status",
                lambda x: (x == "Ngoài danh sách").sum()
            ),
            So_kho_trong_danh_sach=(
                "_warehouse_status",
                lambda x: (x == "Trong danh sách").sum()
            ),
            So_dong_thieu_ma_kho=(
                "_warehouse_status",
                lambda x: (x == "Thiếu mã kho").sum()
            ),
            So_dong_chua_xac_dinh=(
                "_warehouse_status",
                lambda x: x.isin([
                    "Chưa xác định vùng",
                    "Thiếu địa điểm",
                    "Chưa cấu hình danh sách kho"
                ]).sum()
            )
        )
        .reset_index()
    )

    CUSTOMER_SUMMARY = CUSTOMER_SUMMARY.merge(
        WAREHOUSE_SUMMARY,
        on="_customer_key",
        how="left"
    )

else:

    for col in [
        "So_dong_xe_kh",
        "So_kho_ngoai_danh_sach",
        "So_kho_trong_danh_sach",
        "So_dong_thieu_ma_kho",
        "So_dong_chua_xac_dinh"
    ]:
        CUSTOMER_SUMMARY[col] = 0

CUSTOMER_SUMMARY = CUSTOMER_SUMMARY.fillna(0)

CUSTOMER_SUMMARY["Ti_le_kho_ngoai_danh_sach"] = (
    CUSTOMER_SUMMARY["So_kho_ngoai_danh_sach"]
    /
    (
        CUSTOMER_SUMMARY["So_kho_ngoai_danh_sach"]
        + CUSTOMER_SUMMARY["So_kho_trong_danh_sach"]
    ).replace(0, np.nan)
).fillna(0)


# ============================================================
# 29. CHẤM ĐIỂM RỦI RO
# Tổng điểm tối đa: 100
#
# 1. Kho ngoài danh sách: 25
# 2. Địa chỉ nhiều NPP: 20
# 3. Xe nhiều NPP cùng ngày: 20
# 4. Xe nhiều NPP trong kỳ: 15
# 5. Tần suất lấy hàng/ngày: 5
# 6. NPP nhiều kho cùng ngày: 5
# 7. Sản lượng đột biến: 5
# 8. Dòng giao dịch trùng: 3
# 9. Thiếu địa điểm: 2
# ============================================================

def score_warehouse(row):

    checked = (
        row["So_kho_ngoai_danh_sach"]
        + row["So_kho_trong_danh_sach"]
    )

    if checked == 0:
        return 0

    ratio = row["Ti_le_kho_ngoai_danh_sach"]

    if ratio >= 0.50:
        return 25

    if ratio >= 0.20:
        return 18

    if ratio > 0:
        return 10

    return 0


def score_address(n):
    if n >= 4:
        return 20
    if n == 3:
        return 16
    if n == 2:
        return 10
    return 0


def score_vehicle_day(n):
    if n >= 4:
        return 20
    if n == 3:
        return 16
    if n == 2:
        return 10
    return 0


def score_vehicle_period(n):
    if n >= 4:
        return 15
    if n == 3:
        return 12
    if n == 2:
        return 8
    return 0


def score_daily_frequency(n):
    if n >= daily_threshold * 2:
        return 5
    if n >= daily_threshold:
        return 3
    return 0


def score_multi_warehouse(n):
    if n >= 3:
        return 5
    if n == 2:
        return 3
    return 0


def score_duplicate(n):
    if n >= 5:
        return 3
    if n > 0:
        return 1
    return 0


CUSTOMER_SUMMARY["Diem_kho"] = CUSTOMER_SUMMARY.apply(
    score_warehouse,
    axis=1
)

CUSTOMER_SUMMARY["Diem_dia_diem"] = (
    CUSTOMER_SUMMARY["So_NPP_cung_dia_diem"]
    .apply(score_address)
)

CUSTOMER_SUMMARY["Diem_xe_cung_ngay"] = (
    CUSTOMER_SUMMARY["So_NPP_cung_xe_cung_ngay"]
    .apply(score_vehicle_day)
)

CUSTOMER_SUMMARY["Diem_xe_trong_ky"] = (
    CUSTOMER_SUMMARY["So_NPP_cung_xe_trong_ky"]
    .apply(score_vehicle_period)
)

CUSTOMER_SUMMARY["Diem_tan_suat"] = (
    CUSTOMER_SUMMARY["Max_chung_tu_ngay"]
    .apply(score_daily_frequency)
)

CUSTOMER_SUMMARY["Diem_nhieu_kho"] = (
    CUSTOMER_SUMMARY["So_kho_max_cung_ngay"]
    .apply(score_multi_warehouse)
)

CUSTOMER_SUMMARY["Diem_dot_bien_san_luong"] = np.where(
    CUSTOMER_SUMMARY["Bien_dong_san_luong"],
    5,
    0
)

CUSTOMER_SUMMARY["Diem_chung_tu_trung"] = (
    CUSTOMER_SUMMARY["So_dong_trung"]
    .apply(score_duplicate)
)

CUSTOMER_SUMMARY["Diem_thieu_dia_diem"] = np.where(
    CUSTOMER_SUMMARY["Ti_le_thieu_dia_diem"] >= 0.25,
    2,
    0
)

SCORE_COLS = [
    "Diem_kho",
    "Diem_dia_diem",
    "Diem_xe_cung_ngay",
    "Diem_xe_trong_ky",
    "Diem_tan_suat",
    "Diem_nhieu_kho",
    "Diem_dot_bien_san_luong",
    "Diem_chung_tu_trung",
    "Diem_thieu_dia_diem"
]

CUSTOMER_SUMMARY["Tong_diem"] = (
    CUSTOMER_SUMMARY[SCORE_COLS].sum(axis=1)
).clip(0, 100)

CUSTOMER_SUMMARY["Muc_do"] = (
    CUSTOMER_SUMMARY["Tong_diem"]
    .apply(risk_level)
)


# ============================================================
# 30. NHẬN ĐỊNH VÀ GIẢI PHÁP
# ============================================================

def make_reasons(row):

    reasons = []

    if row["Diem_kho"] > 0:
        reasons.append(
            f"Có {int(row['So_kho_ngoai_danh_sach'])} giao dịch "
            "lấy hàng tại kho ngoài danh sách vùng."
        )

    if row["Diem_dia_diem"] > 0:
        reasons.append(
            f"Địa điểm có liên quan {int(row['So_NPP_cung_dia_diem'])} NPP."
        )

    if row["Diem_xe_cung_ngay"] > 0:
        reasons.append(
            f"Một xe phục vụ tối đa "
            f"{int(row['So_NPP_cung_xe_cung_ngay'])} NPP trong cùng ngày."
        )

    if row["Diem_xe_trong_ky"] > 0:
        reasons.append(
            f"Một xe được sử dụng bởi tối đa "
            f"{int(row['So_NPP_cung_xe_trong_ky'])} NPP trong kỳ."
        )

    if row["Diem_tan_suat"] > 0:
        reasons.append(
            f"Tần suất cao nhất {int(row['Max_chung_tu_ngay'])} "
            "chứng từ/ngày."
        )

    if row["Diem_nhieu_kho"] > 0:
        reasons.append(
            f"NPP sử dụng {int(row['So_kho_max_cung_ngay'])} kho "
            "trong cùng ngày."
        )

    if row["Diem_dot_bien_san_luong"] > 0:
        reasons.append(
            "Sản lượng có tháng tăng đột biến so với các tháng trước."
        )

    if row["Diem_chung_tu_trung"] > 0:
        reasons.append(
            f"Có {int(row['So_dong_trung'])} dòng dữ liệu "
            "có dấu hiệu trùng."
        )

    if row["Diem_thieu_dia_diem"] > 0:
        reasons.append("Thiếu thông tin địa điểm ở một số giao dịch.")

    if not reasons:
        return "Chưa phát hiện dấu hiệu bất thường theo các tiêu chí hiện tại."

    return " ".join(reasons)


def make_action(row):

    actions = []

    if row["Diem_kho"] > 0:
        actions.append(
            "Đối chiếu phiếu xuất kho, xác minh lý do lấy hàng "
            "ngoài danh sách kho vùng, kiểm tra phê duyệt ngoại lệ."
        )

    if row["Diem_dia_diem"] > 0:
        actions.append(
            "Kiểm tra hồ sơ pháp lý, địa điểm kinh doanh thực tế, "
            "người đại diện và thông tin liên hệ của các NPP."
        )

    if row["Diem_xe_cung_ngay"] > 0 or row["Diem_xe_trong_ky"] > 0:
        actions.append(
            "Đối chiếu biển số, người lái xe, phiếu xuất kho, "
            "thời gian nhận hàng và xác minh thỏa thuận dùng chung xe."
        )

    if row["Diem_tan_suat"] > 0:
        actions.append(
            "Kiểm tra nhiều phiếu lấy hàng trong ngày, số lần chia nhỏ "
            "đơn và tính phù hợp với nhu cầu kinh doanh."
        )

    if row["Diem_nhieu_kho"] > 0:
        actions.append(
            "Xác minh nguyên nhân lấy hàng tại nhiều kho trong cùng ngày "
            "và kiểm tra chứng từ điều chuyển hoặc phê duyệt."
        )

    if row["Diem_dot_bien_san_luong"] > 0:
        actions.append(
            "Đối chiếu đơn đặt hàng, sản lượng giao nhận, khả năng "
            "tiêu thụ và tồn kho của NPP."
        )

    if row["Diem_chung_tu_trung"] > 0:
        actions.append(
            "Kiểm tra số chứng từ gốc, dòng hàng, phiếu xuất kho "
            "và dữ liệu ghi nhận trùng."
        )

    if row["Diem_thieu_dia_diem"] > 0:
        actions.append(
            "Yêu cầu bổ sung địa điểm khách hàng và cập nhật hồ sơ."
        )

    if not actions:
        return (
            "Tiếp tục giám sát định kỳ, duy trì kiểm tra theo mẫu."
        )

    return " ".join(actions)


CUSTOMER_SUMMARY["Nhan_dinh"] = (
    CUSTOMER_SUMMARY.apply(make_reasons, axis=1)
)

CUSTOMER_SUMMARY["Giai_phap"] = (
    CUSTOMER_SUMMARY.apply(make_action, axis=1)
)

CUSTOMER_SUMMARY = CUSTOMER_SUMMARY.sort_values(
    "Tong_diem",
    ascending=False
)


# ============================================================
# 31. BẢNG TỔNG HỢP KHO
# ============================================================

if not CUSTOMER_CAR.empty:

    CUSTOMER_CAR["_region"] = CUSTOMER_CAR["_address"].apply(
        lambda x: detect_region(x, region_aliases)
    )

    WAREHOUSE_EVIDENCE = CUSTOMER_CAR.copy()

    WAREHOUSE_SUMMARY = (
        WAREHOUSE_EVIDENCE.groupby(
            ["_region", "_warehouse_code", "_warehouse_status"]
        )
        .agg(
            So_giao_dich=("_customer_name", "size"),
            So_NPP=("_customer_key", "nunique"),
            Doanh_thu=("_revenue", "sum"),
            San_luong=("_quantity", "sum"),
            Khoi_luong=("_weight", "sum")
        )
        .reset_index()
    )

else:
    WAREHOUSE_EVIDENCE = pd.DataFrame()
    WAREHOUSE_SUMMARY = pd.DataFrame()


# ============================================================
# 32. BẢNG SẢN PHẨM
# ============================================================

PRODUCT_GROUP_COL = (
    item_name_col
    if item_name_col
    else item_code_col
)

if PRODUCT_GROUP_COL:

    PRODUCT_SUMMARY = (
        DF.groupby(PRODUCT_GROUP_COL)
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
    PRODUCT_SUMMARY = pd.DataFrame()


# ============================================================
# 33. KPI TỔNG QUAN
# ============================================================

TOTAL_REVENUE = DF["_revenue"].sum()
TOTAL_QTY = DF["_quantity"].sum()
TOTAL_WEIGHT = DF["_weight"].sum()

N_CUSTOMER = DF["_customer_key"].nunique()
N_DOCUMENT = (
    DF[document_col].nunique()
    if document_col else len(DF)
)

N_CUSTOMER_CAR = CUSTOMER_CAR["_customer_key"].nunique()
N_VEHICLE = VEHICLE_DATA["_vehicle_norm"].nunique()

N_DUP_ADDRESS = (
    len(ADDRESS_GROUP)
    if not ADDRESS_GROUP.empty else 0
)

N_VEHICLE_DAY = (
    len(VEHICLE_DAY)
    if not VEHICLE_DAY.empty else 0
)

N_VEHICLE_PERIOD = (
    len(VEHICLE_PERIOD)
    if not VEHICLE_PERIOD.empty else 0
)

N_HIGH = CUSTOMER_SUMMARY["Muc_do"].isin(
    ["Cao", "Rất cao"]
).sum()

N_VERY_HIGH = (
    CUSTOMER_SUMMARY["Muc_do"] == "Rất cao"
).sum()

N_WAREHOUSE_OUTSIDE = (
    (CUSTOMER_CAR["_warehouse_status"] == "Ngoài danh sách").sum()
    if not CUSTOMER_CAR.empty else 0
)


# ============================================================
# 34. HIỂN THỊ TỔNG QUAN
# ============================================================

st.markdown("---")

st.markdown(
    '<div class="section-title">TỔNG QUAN HOẠT ĐỘNG NPP</div>',
    unsafe_allow_html=True
)

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Số NPP", f"{N_CUSTOMER:,}")
k2.metric("Doanh thu", format_number(TOTAL_REVENUE))
k3.metric("Sản lượng", format_number(TOTAL_QTY))
k4.metric("Khối lượng", format_number(TOTAL_WEIGHT))
k5.metric("Xe khách hàng", f"{N_VEHICLE:,}")
k6.metric("NPP rủi ro cao", f"{N_HIGH:,}")


st.caption(
    f"Đã loại {removed_z:,} dòng mã hàng đầu Z; "
    f"{removed_discount:,} dòng hàng chiết khấu; "
    f"{removed_returns:,} dòng trả hàng/hủy/số âm."
)

st.markdown("---")


# ============================================================
# 35. CÁC TAB PHÂN TÍCH
# ============================================================

T1, T2, T3, T4, T5, T6, T7 = st.tabs([
    "📊 Tổng quan rủi ro",
    "🏭 Kho lấy hàng",
    "📍 Địa chỉ NPP",
    "🚚 Xe khách hàng",
    "📦 Doanh thu & mặt hàng",
    "⚠️ Điểm rủi ro NPP",
    "📋 Xuất bằng chứng"
])


# ============================================================
# TAB 1 - TỔNG QUAN RỦI RO
# ============================================================

with T1:

    st.markdown(
        '<div class="section-title">PHÂN BỐ MỨC ĐỘ RỦI RO</div>',
        unsafe_allow_html=True
    )

    risk_distribution = (
        CUSTOMER_SUMMARY["Muc_do"]
        .value_counts()
        .reindex(RISK_ORDER, fill_value=0)
        .rename_axis("Muc_do")
        .reset_index(name="So_NPP")
    )

    fig = px.bar(
        risk_distribution,
        x="Muc_do",
        y="So_NPP",
        color="Muc_do",
        text="So_NPP",
        color_discrete_map=RISK_COLORS
    )

    fig.update_layout(
        paper_bgcolor="#07111e",
        plot_bgcolor="#07111e",
        font_color="#c5d7eb",
        showlegend=False,
        height=320
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<div class="section-title">CÁC DẤU HIỆU RỦI RO CHÍNH</div>',
        unsafe_allow_html=True
    )

    a, b, c, d = st.columns(4)

    a.metric("NPP trùng địa điểm", f"{N_DUP_ADDRESS:,}")
    b.metric("Xe nhiều NPP cùng ngày", f"{N_VEHICLE_DAY:,}")
    c.metric("Xe nhiều NPP trong kỳ", f"{N_VEHICLE_PERIOD:,}")
    d.metric("Lượt xe lấy hàng ngoài danh sách kho", f"{N_WAREHOUSE_OUTSIDE:,}")

    st.markdown(
        '<div class="section-title">TOP NPP CẦN ƯU TIÊN KIỂM TRA</div>',
        unsafe_allow_html=True
    )

    top = CUSTOMER_SUMMARY.head(20)

    st.dataframe(
        top[[
            "NPP",
            "Tong_diem",
            "Muc_do",
            "Nhan_dinh",
            "Giai_phap"
        ]],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# TAB 2 - KHO LẤY HÀNG
# ============================================================

with T2:

    st.markdown(
        '<div class="section-title">ĐỐI CHIẾU ĐỊA ĐIỂM NPP VÀ MÃ KHO</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Chỉ phân tích các giao dịch được phân loại là Xe khách hàng. "
        "Xe nhà máy và xe thuê ngoài không được đưa vào bảng này."
    )

    if WAREHOUSE_EVIDENCE.empty:

        st.warning("Không có giao dịch xe khách hàng để phân tích kho.")

    else:

        st.markdown("### Kết quả đối chiếu")

        warehouse_status_summary = (
            WAREHOUSE_EVIDENCE["_warehouse_status"]
            .value_counts()
            .rename_axis("Trạng thái")
            .reset_index(name="Số giao dịch")
        )

        st.dataframe(
            warehouse_status_summary,
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            warehouse_status_summary,
            x="Trạng thái",
            y="Số giao dịch",
            color="Trạng thái",
            text="Số giao dịch"
        )

        fig.update_layout(
            paper_bgcolor="#07111e",
            plot_bgcolor="#07111e",
            font_color="#c5d7eb",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Giao dịch lấy hàng ngoài danh sách vùng")

        outside = WAREHOUSE_EVIDENCE[
            WAREHOUSE_EVIDENCE["_warehouse_status"] == "Ngoài danh sách"
        ].copy()

        if outside.empty:

            st.success("Chưa phát hiện giao dịch ngoài danh sách kho vùng.")

        else:

            st.error(
                f"Có {len(outside):,} giao dịch cần kiểm tra."
            )

            st.dataframe(
                outside[[
                    "_customer_name",
                    "_address",
                    "_region",
                    "_warehouse_code",
                    "_vehicle_raw",
                    "_date",
                    "_revenue",
                    "_quantity",
                    "_weight"
                ]].rename(columns={
                    "_customer_name": "NPP",
                    "_address": "Địa điểm",
                    "_region": "Vùng",
                    "_warehouse_code": "Mã kho thực tế",
                    "_vehicle_raw": "Biển số xe",
                    "_date": "Ngày",
                    "_revenue": "Doanh thu",
                    "_quantity": "Số lượng",
                    "_weight": "Khối lượng"
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Cách xử lý")

        st.write("""
        1. Đối chiếu địa điểm NPP với khu vực được cấu hình.
        2. Kiểm tra mã kho thực tế trên phiếu xuất hàng.
        3. Xác minh trường hợp lấy hàng ngoài vùng được phép.
        4. Kiểm tra phê duyệt điều chuyển, xuất hàng khác kho hoặc ngoại lệ.
        5. Yêu cầu đơn vị kinh doanh giải trình nếu chưa có chứng từ hợp lệ.
        """)

        st.markdown("### Tổng hợp theo vùng và mã kho")

        st.dataframe(
            WAREHOUSE_SUMMARY,
            use_container_width=True,
            hide_index=True
        )

        missing_region = WAREHOUSE_EVIDENCE[
            WAREHOUSE_EVIDENCE["_warehouse_status"].isin([
                "Chưa xác định vùng",
                "Thiếu địa điểm"
            ])
        ]

        if not missing_region.empty:
            st.warning(
                f"Có {len(missing_region):,} giao dịch chưa xác định được vùng. "
                "Không nên kết luận sai kho đối với các giao dịch này."
            )


# ============================================================
# TAB 3 - ĐỊA CHỈ NPP
# ============================================================

with T3:

    st.markdown(
        '<div class="section-title">NPP TRÙNG ĐỊA ĐIỂM</div>',
        unsafe_allow_html=True
    )

    if ADDRESS_GROUP.empty:

        st.success(
            "Chưa phát hiện địa điểm được sử dụng bởi từ 2 NPP trở lên."
        )

    else:

        st.warning(
            f"Phát hiện {len(ADDRESS_GROUP):,} địa điểm có từ 2 NPP trở lên."
        )

        st.dataframe(
            ADDRESS_GROUP.rename(columns={
                "Dia_diem": "Địa điểm",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
        '<div class="section-title">HƯỚNG KIỂM TRA ĐỊA CHỈ</div>',
        unsafe_allow_html=True
    )

    st.write("""
    Một địa điểm có nhiều NPP là dấu hiệu cần xác minh, chưa đủ để kết luận
    các NPP có cùng chủ sở hữu hoặc thông đồng.

    Kiểm tra thêm:

    - Giấy chứng nhận đăng ký kinh doanh.
    - Địa chỉ đăng ký và địa điểm hoạt động thực tế.
    - Người đại diện pháp luật, người liên hệ.
    - Số điện thoại, email, người nhận hàng.
    - Kho bãi, cửa hàng và hoạt động kinh doanh thực tế.
    - Quan hệ giữa các NPP nếu có dấu hiệu liên kết.
    """)


# ============================================================
# TAB 4 - XE KHÁCH HÀNG
# ============================================================

with T4:

    st.markdown(
        '<div class="section-title">MỘT XE - NHIỀU NPP - CÙNG NGÀY</div>',
        unsafe_allow_html=True
    )

    if VEHICLE_DAY.empty:

        st.success(
            "Chưa phát hiện một xe phục vụ nhiều NPP trong cùng ngày."
        )

    else:

        st.warning(
            f"Phát hiện {len(VEHICLE_DAY):,} trường hợp "
            "một xe phục vụ nhiều NPP trong cùng ngày."
        )

        st.dataframe(
            VEHICLE_DAY.rename(columns={
                "_date_only": "Ngày",
                "Bien_so": "Biển số",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP",
                "So_dia_diem": "Số địa điểm",
                "So_kho": "Số kho",
                "So_giao_dich": "Số giao dịch",
                "Doanh_thu": "Doanh thu",
                "San_luong": "Sản lượng",
                "Khoi_luong": "Khối lượng"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
        '<div class="section-title">MỘT XE - NHIỀU NPP - NHIỀU NGÀY</div>',
        unsafe_allow_html=True
    )

    if VEHICLE_PERIOD.empty:

        st.success(
            "Chưa phát hiện xe dùng chung bởi nhiều NPP trong kỳ."
        )

    else:

        st.warning(
            f"Phát hiện {len(VEHICLE_PERIOD):,} xe liên quan từ 2 NPP trở lên."
        )

        st.dataframe(
            VEHICLE_PERIOD.rename(columns={
                "Bien_so": "Biển số",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP",
                "So_ngay_hoat_dong": "Số ngày hoạt động",
                "So_dia_diem": "Số địa điểm",
                "So_kho": "Số kho",
                "So_giao_dich": "Số giao dịch",
                "Doanh_thu": "Doanh thu",
                "San_luong": "Sản lượng",
                "Khoi_luong": "Khối lượng"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
        '<div class="section-title">HƯỚNG KIỂM TRA</div>',
        unsafe_allow_html=True
    )

    st.write("""
    - Xác minh chủ phương tiện và người điều khiển.
    - Đối chiếu phiếu xuất kho và thời điểm lấy hàng của từng NPP.
    - Kiểm tra các địa điểm lấy hàng của cùng biển số.
    - Xác minh việc dùng chung xe có hợp đồng hoặc thỏa thuận hay không.
    - Kiểm tra quan hệ giữa các NPP cùng sử dụng xe.
    - Đối chiếu tính hợp lý về thời gian và địa lý nếu có dữ liệu giờ lấy hàng.
    """)


# ============================================================
# TAB 5 - DOANH THU VÀ MẶT HÀNG
# ============================================================

with T5:

    st.markdown(
        '<div class="section-title">DOANH THU VÀ SẢN LƯỢNG THEO THÁNG</div>',
        unsafe_allow_html=True
    )

    MONTHLY = (
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

    col1, col2 = st.columns(2)

    with col1:

        fig = px.bar(
            MONTHLY,
            x="_month",
            y="Doanh_thu",
            title="Doanh thu theo tháng"
        )

        fig.update_layout(
            paper_bgcolor="#07111e",
            plot_bgcolor="#07111e",
            font_color="#c5d7eb"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:

        fig = px.line(
            MONTHLY,
            x="_month",
            y="San_luong",
            markers=True,
            title="Sản lượng theo tháng"
        )

        fig.update_layout(
            paper_bgcolor="#07111e",
            plot_bgcolor="#07111e",
            font_color="#c5d7eb"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Bảng mặt hàng")

    if PRODUCT_SUMMARY.empty:

        st.info("Chưa chọn cột tên hàng hoặc mã hàng.")

    else:

        st.dataframe(
            PRODUCT_SUMMARY,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### Tháng có sản lượng đột biến")

    if SPIKE_TABLE.empty:

        st.success(
            "Chưa phát hiện tháng có sản lượng gấp từ 3 lần trung vị "
            "của các tháng trước theo điều kiện kiểm tra."
        )

    else:

        st.warning(
            f"Có {len(SPIKE_TABLE):,} trường hợp sản lượng cần xem xét."
        )

        st.dataframe(
            SPIKE_TABLE,
            use_container_width=True,
            hide_index=True
        )

        st.write("""
        Hướng kiểm tra: đối chiếu đơn đặt hàng, sản lượng giao nhận,
        tồn kho NPP, khả năng tiêu thụ và các chương trình bán hàng
        trong kỳ. Đột biến sản lượng không đồng nghĩa với việc ghi nhận
        giao dịch bất thường.
        """)


# ============================================================
# TAB 6 - BẢNG ĐIỂM RỦI RO
# ============================================================

with T6:

    st.markdown(
        '<div class="section-title">ĐÁNH GIÁ RỦI RO TỪNG NHÀ PHÂN PHỐI</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Điểm tối đa 100. Mô hình dùng để sàng lọc và xếp thứ tự ưu tiên kiểm tra."
    )

    SCORE_TABLE = CUSTOMER_SUMMARY[[
        "NPP",
        "Diem_kho",
        "Diem_dia_diem",
        "Diem_xe_cung_ngay",
        "Diem_xe_trong_ky",
        "Diem_tan_suat",
        "Diem_nhieu_kho",
        "Diem_dot_bien_san_luong",
        "Diem_chung_tu_trung",
        "Diem_thieu_dia_diem",
        "Tong_diem",
        "Muc_do",
        "Nhan_dinh",
        "Giai_phap"
    ]].copy()

    SCORE_TABLE = SCORE_TABLE.rename(columns={
        "Diem_kho": "Kho /25",
        "Diem_dia_diem": "Địa điểm /20",
        "Diem_xe_cung_ngay": "Xe cùng ngày /20",
        "Diem_xe_trong_ky": "Xe trong kỳ /15",
        "Diem_tan_suat": "Tần suất /5",
        "Diem_nhieu_kho": "Nhiều kho /5",
        "Diem_dot_bien_san_luong": "Sản lượng /5",
        "Diem_chung_tu_trung": "Trùng dữ liệu /3",
        "Diem_thieu_dia_diem": "Thiếu địa điểm /2",
        "Tong_diem": "Tổng điểm",
        "Muc_do": "Mức độ",
        "Nhan_dinh": "Nhận định",
        "Giai_phap": "Giải pháp"
    })

    st.dataframe(
        SCORE_TABLE,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Phân tích chi tiết một NPP")

    selected_customer = st.selectbox(
        "Chọn NPP",
        CUSTOMER_SUMMARY["NPP"].dropna().unique().tolist()
    )

    detail = CUSTOMER_SUMMARY[
        CUSTOMER_SUMMARY["NPP"] == selected_customer
    ].iloc[0]

    score = int(detail["Tong_diem"])
    level = detail["Muc_do"]

    st.metric(
        "Điểm rủi ro",
        f"{score}/100",
        delta=level
    )

    st.markdown(
        f'<div class="{risk_class_css(level)}">'
        f'<b>NHẬN ĐỊNH:</b> {detail["Nhan_dinh"]}<br><br>'
        f'<b>GIẢI PHÁP:</b> {detail["Giai_phap"]}'
        f'</div>',
        unsafe_allow_html=True
    )

    score_detail = pd.DataFrame({
        "Nhóm rủi ro": [
            "Kho ngoài danh sách",
            "NPP trùng địa điểm",
            "Xe nhiều NPP cùng ngày",
            "Xe nhiều NPP trong kỳ",
            "Tần suất lấy hàng",
            "NPP nhiều kho cùng ngày",
            "Sản lượng đột biến",
            "Dòng giao dịch trùng",
            "Thiếu địa điểm"
        ],
        "Điểm": [
            detail["Diem_kho"],
            detail["Diem_dia_diem"],
            detail["Diem_xe_cung_ngay"],
            detail["Diem_xe_trong_ky"],
            detail["Diem_tan_suat"],
            detail["Diem_nhieu_kho"],
            detail["Diem_dot_bien_san_luong"],
            detail["Diem_chung_tu_trung"],
            detail["Diem_thieu_dia_diem"]
        ]
    })

    fig = px.bar(
        score_detail,
        x="Điểm",
        y="Nhóm rủi ro",
        orientation="h",
        text="Điểm",
        title=f"Cơ cấu điểm rủi ro - {selected_customer}"
    )

    fig.update_layout(
        paper_bgcolor="#07111e",
        plot_bgcolor="#07111e",
        font_color="#c5d7eb",
        height=390
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 7 - XUẤT BẰNG CHỨNG
# ============================================================

with T7:

    st.markdown(
        '<div class="section-title">XUẤT BÁO CÁO VÀ BẰNG CHỨNG</div>',
        unsafe_allow_html=True
    )

    st.write("""
    File Excel xuất ra gồm các sheet:
    - Tổng hợp rủi ro NPP.
    - Giao dịch xe khách hàng.
    - Giao dịch lấy hàng ngoài danh sách kho.
    - NPP trùng địa điểm.
    - Một xe nhiều NPP cùng ngày.
    - Một xe nhiều NPP trong kỳ.
    - Dòng dữ liệu nghi trùng.
    - Sản lượng đột biến.
    - Tổng hợp mặt hàng.
    - Dữ liệu sau lọc.
    """)

    export_data = io.BytesIO()

    with pd.ExcelWriter(
        export_data,
        engine="openpyxl"
    ) as writer:

        CUSTOMER_SUMMARY.to_excel(
            writer,
            sheet_name="Tong_hop_rui_ro_NPP",
            index=False
        )

        CUSTOMER_CAR.to_excel(
            writer,
            sheet_name="Xe_khach_hang",
            index=False
        )

        WAREHOUSE_EVIDENCE[
            WAREHOUSE_EVIDENCE["_warehouse_status"] == "Ngoài danh sách"
        ].to_excel(
            writer,
            sheet_name="Kho_ngoai_danh_sach",
            index=False
        )

        ADDRESS_GROUP.to_excel(
            writer,
            sheet_name="NPP_trung_dia_diem",
            index=False
        )

        VEHICLE_DAY.to_excel(
            writer,
            sheet_name="Xe_nhieu_NPP_cung_ngay",
            index=False
        )

        VEHICLE_PERIOD.to_excel(
            writer,
            sheet_name="Xe_nhieu_NPP_trong_ky",
            index=False
        )

        DUPLICATE_ROWS.to_excel(
            writer,
            sheet_name="Dong_du_lieu_trung",
            index=False
        )

        SPIKE_TABLE.to_excel(
            writer,
            sheet_name="San_luong_dot_bien",
            index=False
        )

        PRODUCT_SUMMARY.to_excel(
            writer,
            sheet_name="Tong_hop_mat_hang",
            index=False
        )

        DF.to_excel(
            writer,
            sheet_name="Du_lieu_sau_loc",
            index=False
        )

    export_data.seek(0)

    st.download_button(
        label="⬇️ TẢI BÁO CÁO RỦI RO NPP (EXCEL)",
        data=export_data,
        file_name="Bao_cao_phan_tich_rui_ro_NPP.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================
# 36. THANG MÀU ĐÁNH GIÁ
# ============================================================

st.markdown("---")

st.markdown(
    '<div class="section-title">THANG MÀU ĐÁNH GIÁ RỦI RO</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        '<div class="risk-green"><b>XANH - THẤP</b><br>0–24 điểm</div>',
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        '<div class="risk-yellow"><b>VÀNG - THEO DÕI</b><br>25–44 điểm</div>',
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        '<div class="risk-orange"><b>CAM - CAO</b><br>45–64 điểm</div>',
        unsafe_allow_html=True
    )

with c4:
    st.markdown(
        '<div class="risk-red"><b>ĐỎ - RẤT CAO</b><br>65–100 điểm</div>',
        unsafe_allow_html=True
    )


st.caption(
    "Lưu ý: Điểm số là mô hình sàng lọc rủi ro. "
    "Dấu hiệu trùng địa điểm, dùng chung xe hoặc lấy hàng ngoài danh sách "
    "cần được xác minh bằng chứng từ và giải trình trước khi kết luận."
)

st.markdown(
    """
    <div style='text-align:center;color:#526982;font-size:10px;margin-top:25px;'>
    HOA SEN GROUP | INTERNAL CONTROL & BUSINESS RISK ANALYTICS
    </div>
    """,
    unsafe_allow_html=True
)
