
import io
import re
import unicodedata
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

warnings.filterwarnings("ignore")

# ============================================================
# NPP BUSINESS RISK ANALYTICS - HOA SEN GROUP
# ============================================================

st.set_page_config(
    page_title="NPP Risk Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 1. STYLE
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
    color: #829ab5;
    font-size: 12px;
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

.risk-green {
    background: #102d22;
    color: #a7f3d0;
    border-left: 4px solid #22c55e;
    padding: 12px;
    border-radius: 5px;
    margin: 5px 0;
}

.risk-yellow {
    background: #39320f;
    color: #fff0a8;
    border-left: 4px solid #eab308;
    padding: 12px;
    border-radius: 5px;
    margin: 5px 0;
}

.risk-orange {
    background: #3b2814;
    color: #ffd199;
    border-left: 4px solid #f97316;
    padding: 12px;
    border-radius: 5px;
    margin: 5px 0;
}

.risk-red {
    background: #39191c;
    color: #ffb5b5;
    border-left: 4px solid #ef4444;
    padding: 12px;
    border-radius: 5px;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. CẤU HÌNH KHO THEO VÙNG
# ============================================================

DEFAULT_WAREHOUSES = {
    "Miền Nam và Tây Nam Bộ": ["053", "281", "284", "054"],
    "Miền Trung và Tây Nguyên": [
        "053", "252", "251", "261", "263", "284", "291"
    ],
    "Miền Bắc": ["291", "261"]
}

DEFAULT_REGIONS = {
    "Miền Nam và Tây Nam Bộ": """
    Hồ Chí Minh; TP.HCM; TPHCM; Sài Gòn; Bình Dương;
    Bà Rịa Vũng Tàu; Vũng Tàu; Đồng Nai; Bình Phước;
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

LEVELS = ["Thấp", "Theo dõi", "Cao", "Rất cao"]

LEVEL_COLORS = {
    "Thấp": "#22c55e",
    "Theo dõi": "#eab308",
    "Cao": "#f97316",
    "Rất cao": "#ef4444"
}

METHOD_TYPES = [
    "Xe khách hàng",
    "Xe nhà máy",
    "Thuê ngoài",
    "Khác / Chưa xác định"
]


# ============================================================
# 3. DANH SÁCH TÊN CỘT
# ============================================================

ALIASES = {
    "customer": [
        "Tên khách hàng", "Tên KH", "Khách hàng",
        "Customer", "Customer Name"
    ],

    "customer_id": [
        "Mã khách hàng", "Mã KH",
        "Customer Code", "Customer ID"
    ],

    "group": [
        "Tên nhóm KH", "Mã nhóm KH",
        "Nhóm khách hàng", "Loại khách hàng",
        "Loại KH", "Customer Group"
    ],

    "date": [
        "Ngày chứng từ", "Ngày xuất", "Ngày lấy hàng",
        "Ngày giao hàng", "Document Date"
    ],

    "document": [
        "Số chứng từ", "Số CT", "Số phiếu",
        "Document No", "Invoice No"
    ],

    "revenue": [
        "Thành tiền bán", "Doanh thu",
        "Thành tiền", "Sales Amount"
    ],

    "quantity": [
        "Số lượng", "SL", "Quantity"
    ],

    "weight": [
        "Khối lượng", "KL", "Trọng lượng", "Weight"
    ],

    "item_code": [
        "Mã hàng", "Mã SP", "Mã sản phẩm", "Item Code"
    ],

    "item_name": [
        "Tên hàng", "Tên sản phẩm", "Item Name"
    ],

    "address": [
        "Địa điểm", "Địa điểm khách hàng",
        "Địa điểm giao hàng", "Địa chỉ khách hàng",
        "Địa chỉ", "Địa chỉ KH", "Nơi giao hàng"
    ],

    "warehouse": [
        "Mã kho", "Mã kho xuất", "Kho xuất",
        "Kho lấy hàng", "Địa điểm xuất",
        "Warehouse", "Plant"
    ],

    "method": [
        "Shipping method", "Hình thức vận chuyển",
        "Phương thức vận chuyển", "Loại vận chuyển"
    ],

    "vehicle": [
        "Biển số xe", "Số xe", "Biển kiểm soát",
        "Vehicle No", "License Plate"
    ],

    "note": [
        "Ghi chú", "Diễn giải", "Remark", "Notes"
    ],

    "order_type": [
        "Loại đơn hàng", "Loại giao dịch", "Transaction Type"
    ]
}


# ============================================================
# 4. HÀM CHUẨN HÓA
# ============================================================

def norm(value):
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean(value):
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


def clean_warehouse(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    match = re.search(
        r"(?<!\d)(\d{1,3})(?:\.0+)?(?!\d)",
        text
    )

    if not match:
        return ""

    return match.group(1).zfill(3)


def parse_number(value):
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
        last = text.split(",")[-1]

        if len(last) <= 2:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return 0.0


def split_values(value):
    return [
        x.strip()
        for x in re.split(r"[,;\n]+", str(value))
        if x.strip()
    ]


def unique_names(series):
    return "; ".join(sorted({
        str(x).strip()
        for x in series
        if pd.notna(x) and str(x).strip()
    }))


def risk_level(score):
    if score >= 65:
        return "Rất cao"
    if score >= 45:
        return "Cao"
    if score >= 25:
        return "Theo dõi"
    return "Thấp"


def detect_column(columns, aliases):
    normalized = {norm(c): c for c in columns}

    for alias in aliases:
        key = norm(alias)
        if key in normalized:
            return normalized[key]

    for alias in aliases:
        key = norm(alias)

        for ncol, original in normalized.items():
            if key and key in ncol:
                return original

    return None


# ============================================================
# 5. ĐỌC EXCEL VÀ TỰ TÌM DÒNG TIÊU ĐỀ
# ============================================================

def score_header(values):
    normalized = [norm(v) for v in values]

    score = 0

    for key in ["customer", "date", "address", "warehouse", "method"]:
        aliases = ALIASES[key]

        found = False

        for alias in aliases:
            a = norm(alias)

            if any(a == v or (a and a in v) for v in normalized):
                found = True
                break

        if found:
            score += 1

    return score


def find_header(excel_bytes, sheet):
    raw = pd.read_excel(
        io.BytesIO(excel_bytes),
        sheet_name=sheet,
        header=None,
        nrows=40,
        engine="openpyxl"
    )

    best_row = 0
    best_score = -1

    for i in range(len(raw)):
        current_score = score_header(raw.iloc[i].tolist())

        if current_score > best_score:
            best_score = current_score
            best_row = i

    return best_row, best_score


def make_columns_unique(columns):
    seen = {}
    result = []

    for value in columns:
        name = str(value).strip().replace("\n", " ")

        if not name or name.lower() == "nan":
            name = "Column"

        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0

        result.append(name)

    return result


def read_files(files):
    frames = []
    logs = []

    for uploaded in files:
        content = uploaded.getvalue()

        try:
            excel = pd.ExcelFile(
                io.BytesIO(content),
                engine="openpyxl"
            )

            best_sheet = None
            best_header = 0
            best_score = -1

            for sheet in excel.sheet_names:
                header, score = find_header(content, sheet)

                if score > best_score:
                    best_sheet = sheet
                    best_header = header
                    best_score = score

            if best_sheet is None:
                logs.append(f"{uploaded.name}: Không tìm thấy sheet dữ liệu.")
                continue

            data = pd.read_excel(
                io.BytesIO(content),
                sheet_name=best_sheet,
                header=best_header,
                engine="openpyxl"
            )

            data.columns = make_columns_unique(data.columns)
            data = data.dropna(how="all")

            if data.empty:
                logs.append(f"{uploaded.name}: Sheet dữ liệu trống.")
                continue

            data["_File"] = uploaded.name
            data["_Sheet"] = best_sheet

            frames.append(data)

            logs.append(
                f"{uploaded.name}: Sheet '{best_sheet}', "
                f"dòng tiêu đề Excel số {best_header + 1}, "
                f"độ khớp tiêu đề {best_score}/5."
            )

        except Exception as exc:
            logs.append(f"{uploaded.name}: Lỗi đọc file: {exc}")

    if not frames:
        return pd.DataFrame(), logs

    return pd.concat(
        frames,
        ignore_index=True,
        sort=False
    ), logs


# ============================================================
# 6. NHẬN DIỆN VÙNG ĐỊA LÝ
# ============================================================

def build_region_aliases(region_text):
    result = {}

    for region, text in region_text.items():
        result[region] = sorted(
            {norm(x) for x in split_values(text) if norm(x)},
            key=len,
            reverse=True
        )

    return result


def detect_region(address, aliases):
    address = norm(address)

    if not address:
        return "Thiếu địa điểm"

    padded = f" {address} "

    for region, names in aliases.items():
        for name in names:
            if f" {name} " in padded:
                return region

    return "Chưa xác định vùng"


def score_address(count):
    if count >= 4:
        return 20
    if count == 3:
        return 16
    if count == 2:
        return 10
    return 0


# ============================================================
# 7. HEADER VÀ UPLOAD
# ============================================================

st.markdown("""
<div class="main-title">NPP BUSINESS RISK ANALYTICS</div>
<div class="sub-title">
HOA SEN GROUP | PHÂN TÍCH RỦI RO NHÀ PHÂN PHỐI
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📂 DỮ LIỆU")

    files = st.file_uploader(
        "Chọn file Excel",
        type=["xlsx"],
        accept_multiple_files=True
    )

if not files:
    st.info("Tải file Excel để bắt đầu.")
    st.stop()

RAW, read_logs = read_files(files)

with st.expander("Thông tin đọc file Excel"):
    for log in read_logs:
        st.write(log)

if RAW.empty:
    st.error("Không có sheet dữ liệu nào được đọc thành công.")
    st.stop()

COLUMNS = RAW.columns.tolist()


# ============================================================
# 8. CHỌN CỘT EXCEL
# ============================================================

def select_column(label, key, required=False):
    detected = detect_column(COLUMNS, ALIASES[key])

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
        key=f"col_{key}"
    )

    if selected == "-- Không chọn --":
        if required:
            st.warning(f"Chưa chọn cột {label}.")
        return None

    return selected


with st.sidebar:
    st.markdown("---")
    st.markdown("## 🧩 ÁNH XẠ CỘT")

    customer_col = select_column("Tên khách hàng", "customer", True)
    customer_id_col = select_column("Mã khách hàng", "customer_id")
    group_col = select_column("Nhóm khách hàng", "group")
    date_col = select_column("Ngày chứng từ", "date", True)
    document_col = select_column("Số chứng từ", "document")

    address_col = select_column("Địa điểm", "address", True)
    warehouse_col = select_column("Mã kho", "warehouse", True)

    method_col = select_column("Hình thức vận chuyển", "method", True)
    vehicle_col = select_column("Biển số xe", "vehicle", True)

    revenue_col = select_column("Doanh thu", "revenue")
    quantity_col = select_column("Số lượng", "quantity")
    weight_col = select_column("Khối lượng", "weight")
    item_code_col = select_column("Mã hàng", "item_code")
    item_name_col = select_column("Tên hàng", "item_name")
    note_col = select_column("Ghi chú", "note")
    order_type_col = select_column("Loại giao dịch", "order_type")

required_cols = [
    customer_col,
    date_col,
    address_col,
    warehouse_col,
    method_col,
    vehicle_col
]

if any(x is None for x in required_cols):
    st.error("Chưa chọn đủ cột bắt buộc. Hãy kiểm tra Sidebar.")
    st.stop()


# ============================================================
# 9. CHỈ LỌC NHÀ PHÂN PHỐI
# ============================================================

BASE = RAW.copy()

if group_col:

    group_values = sorted(
        BASE[group_col].dropna().astype(str).unique()
    )

    suggested = [
        x for x in group_values
        if "npp" in norm(x) or "nha phan phoi" in norm(x)
    ]

    with st.sidebar:
        st.markdown("---")
        st.markdown("## 🏢 CHỌN NHÓM NPP")

        selected_groups = st.multiselect(
            "Nhóm khách hàng",
            group_values,
            default=suggested
        )

    if not selected_groups:
        st.warning("Bạn chưa chọn nhóm Nhà Phân Phối.")
        st.stop()

    BASE = BASE[
        BASE[group_col].astype(str).isin(selected_groups)
    ].copy()

else:
    with st.sidebar:
        only_npp = st.checkbox(
            "File chỉ chứa Nhà Phân Phối",
            value=False
        )

    if not only_npp:
        st.warning(
            "Không có cột nhóm khách hàng. "
            "Cần xác nhận file chỉ gồm NPP."
        )
        st.stop()


# ============================================================
# 10. LOẠI MÃ HÀNG Z VÀ CHIẾT KHẤU
# ============================================================

removed_z = 0
removed_discount = 0

if item_code_col:
    code = BASE[item_code_col].fillna("").astype(str).str.strip()

    mask_z = code.str.upper().str.startswith("Z", na=False)

    removed_z = int(mask_z.sum())

    BASE = BASE[~mask_z].copy()

if item_name_col:
    names = BASE[item_name_col].apply(norm)

    mask_discount = names.str.contains(
        "chiet khau",
        na=False
    )

    removed_discount = int(mask_discount.sum())

    BASE = BASE[~mask_discount].copy()


# ============================================================
# 11. CHUẨN HÓA CỘT DỮ LIỆU
# ============================================================

DF = BASE.copy()

DF["_customer_name"] = DF[customer_col].apply(clean)

if customer_id_col:
    DF["_customer_id"] = DF[customer_id_col].apply(clean)

    DF["_customer_key"] = np.where(
        DF["_customer_id"] != "",
        "ID:" + DF["_customer_id"].astype(str),
        "NAME:" + DF["_customer_name"].apply(norm)
    )
else:
    DF["_customer_key"] = (
        "NAME:" + DF["_customer_name"].apply(norm)
    )

DF["_date"] = pd.to_datetime(
    DF[date_col],
    dayfirst=True,
    errors="coerce"
)

DF = DF[
    DF["_date"].notna()
    & DF["_customer_name"].ne("")
].copy()

if DF.empty:
    st.error("Không có ngày chứng từ hợp lệ hoặc tên khách hàng.")
    st.stop()

DF["_date_only"] = DF["_date"].dt.date
DF["_month"] = DF["_date"].dt.to_period("M").astype(str)

DF["_address"] = DF[address_col].apply(clean)
DF["_address_norm"] = DF["_address"].apply(norm)

DF["_warehouse_raw"] = DF[warehouse_col].apply(clean)
DF["_warehouse_code"] = DF["_warehouse_raw"].apply(clean_warehouse)

DF["_method"] = DF[method_col].apply(clean)
DF["_vehicle_raw"] = DF[vehicle_col].apply(clean)
DF["_vehicle_norm"] = DF["_vehicle_raw"].apply(clean_vehicle)

DF["_revenue"] = (
    DF[revenue_col].apply(parse_number)
    if revenue_col else 0.0
)

DF["_quantity"] = (
    DF[quantity_col].apply(parse_number)
    if quantity_col else 0.0
)

DF["_weight"] = (
    DF[weight_col].apply(parse_number)
    if weight_col else 0.0
)


# ============================================================
# 12. PHÂN LOẠI XE KHÁCH HÀNG
# ============================================================

def suggest_method_type(value):
    text = norm(value)

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


method_values = sorted(DF["_method"].dropna().unique())

if not method_values:
    st.error("Không có dữ liệu hình thức vận chuyển.")
    st.stop()

method_df = pd.DataFrame({
    "Hình thức vận chuyển": method_values,
    "Phân loại": [
        suggest_method_type(x)
        for x in method_values
    ]
})

st.markdown(
    '<div class="section-title">KIỂM TRA PHÂN LOẠI PHƯƠNG TIỆN</div>',
    unsafe_allow_html=True
)

method_df = st.data_editor(
    method_df,
    disabled=["Hình thức vận chuyển"],
    hide_index=True,
    use_container_width=True,
    column_config={
        "Phân loại": st.column_config.SelectboxColumn(
            "Phân loại",
            options=METHOD_TYPES,
            required=True
        )
    },
    key="method_table"
)

method_map = dict(
    zip(method_df["Hình thức vận chuyển"], method_df["Phân loại"])
)

DF["_vehicle_type"] = DF["_method"].map(method_map).fillna(
    "Khác / Chưa xác định"
)

# Chỉ xe khách hàng được sử dụng cho phân tích xe và kho.
CUSTOMER_CAR = DF[
    DF["_vehicle_type"] == "Xe khách hàng"
].copy()

FACTORY_CAR = DF[
    DF["_vehicle_type"] == "Xe nhà máy"
].copy()

OUTSIDE_CAR = DF[
    DF["_vehicle_type"] == "Thuê ngoài"
].copy()

UNKNOWN_CAR = DF[
    DF["_vehicle_type"] == "Khác / Chưa xác định"
].copy()


# ============================================================
# 13. CẤU HÌNH VÙNG VÀ MÃ KHO
# ============================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("## 🗺️ DANH SÁCH TỈNH")

    region_text = {}

    for region, default in DEFAULT_REGIONS.items():
        region_text[region] = st.text_area(
            region,
            value=default.strip(),
            height=95,
            key=f"region_{region}"
        )

    st.markdown("## 🏭 MÃ KHO ĐƯỢC PHÉP")

    warehouse_text = {}

    for region, codes in DEFAULT_WAREHOUSES.items():
        warehouse_text[region] = st.text_input(
            region,
            value=", ".join(codes),
            key=f"allowed_{region}"
        )

region_aliases = {}

for region, value in region_text.items():
    region_aliases[region] = sorted(
        {norm(x) for x in split_values(value) if norm(x)},
        key=len,
        reverse=True
    )

allowed_warehouses = {
    region: {
        clean_warehouse(x)
        for x in split_values(value)
        if clean_warehouse(x)
    }
    for region, value in warehouse_text.items()
}


# ============================================================
# 14. XÁC ĐỊNH VÙNG VÀ ĐỐI CHIẾU KHO
# ============================================================

DF["_region"] = DF["_address"].apply(
    lambda x: detect_region(x, region_aliases)
)


def check_warehouse(row):

    code = row["_warehouse_code"]
    region = row["_region"]

    if not code:
        return "Thiếu mã kho"

    if region == "Thiếu địa điểm":
        return "Thiếu địa điểm"

    if region == "Chưa xác định vùng":
        return "Chưa xác định vùng"

    permitted = allowed_warehouses.get(region, set())

    if not permitted:
        return "Chưa cấu hình kho"

    if code in permitted:
        return "Trong danh sách"

    return "Ngoài danh sách"


# Chỉ kiểm tra kho cho xe khách hàng.
CUSTOMER_CAR["_region"] = CUSTOMER_CAR["_address"].apply(
    lambda x: detect_region(x, region_aliases)
)

CUSTOMER_CAR["_warehouse_status"] = CUSTOMER_CAR.apply(
    check_warehouse,
    axis=1
)


# ============================================================
# 15. LỌC THỜI GIAN
# ============================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("## 🔍 BỘ LỌC")

    date_min = DF["_date"].min().date()
    date_max = DF["_date"].max().date()

    date_range = st.date_input(
        "Khoảng thời gian",
        value=(date_min, date_max)
    )

    daily_limit = st.number_input(
        "Số chứng từ/ngày cảnh báo",
        min_value=2,
        max_value=100,
        value=5
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = date_min, date_max

DF = DF[
    (DF["_date"].dt.date >= start_date)
    & (DF["_date"].dt.date <= end_date)
].copy()

CUSTOMER_CAR = CUSTOMER_CAR[
    (CUSTOMER_CAR["_date"].dt.date >= start_date)
    & (CUSTOMER_CAR["_date"].dt.date <= end_date)
].copy()

if DF.empty:
    st.warning("Không có dữ liệu trong thời gian đã chọn.")
    st.stop()


# ============================================================
# 16. ĐỊA CHỈ TRÙNG
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
            Danh_sach_NPP=("_customer_name", unique_names)
        )
        .reset_index()
    )

    ADDRESS_GROUP = ADDRESS_GROUP[
        ADDRESS_GROUP["So_NPP"] >= 2
    ]

    address_map = ADDRESS_GROUP.set_index(
        "_address_norm"
    )["So_NPP"]

    ADDRESS_PAIRS["_npp_count"] = (
        ADDRESS_PAIRS["_address_norm"]
        .map(address_map)
        .fillna(1)
    )

    CUSTOMER_ADDRESS_MAX = (
        ADDRESS_PAIRS.groupby("_customer_key")["_npp_count"].max()
    )

else:
    ADDRESS_GROUP = pd.DataFrame()
    CUSTOMER_ADDRESS_MAX = pd.Series(dtype=float)


# ============================================================
# 17. XE NHIỀU NPP TRONG CÙNG NGÀY
# ============================================================

VEHICLE_DATA = CUSTOMER_CAR[
    CUSTOMER_CAR["_vehicle_norm"].ne("")
].copy()

if not VEHICLE_DATA.empty:

    VEHICLE_DAY_ALL = (
        VEHICLE_DATA.groupby(["_vehicle_norm", "_date_only"])
        .agg(
            Bien_so=("_vehicle_raw", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_names),
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

    per_customer = VEHICLE_DATA.merge(
        VEHICLE_DAY_ALL[
            ["_vehicle_norm", "_date_only", "So_NPP"]
        ],
        on=["_vehicle_norm", "_date_only"],
        how="left"
    )

    CUSTOMER_VEHICLE_DAY_MAX = (
        per_customer.groupby("_customer_key")["So_NPP"].max()
    )

else:
    VEHICLE_DAY_ALL = pd.DataFrame()
    VEHICLE_DAY = pd.DataFrame()
    CUSTOMER_VEHICLE_DAY_MAX = pd.Series(dtype=float)


# ============================================================
# 18. XE NHIỀU NPP TRONG TOÀN KỲ
# ============================================================

if not VEHICLE_DATA.empty:

    VEHICLE_PERIOD_ALL = (
        VEHICLE_DATA.groupby("_vehicle_norm")
        .agg(
            Bien_so=("_vehicle_raw", "first"),
            So_NPP=("_customer_key", "nunique"),
            Danh_sach_NPP=("_customer_name", unique_names),
            So_ngay=("_date_only", "nunique"),
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
    ].copy()

    per_customer = VEHICLE_DATA.merge(
        VEHICLE_PERIOD_ALL[
            ["_vehicle_norm", "So_NPP"]
        ],
        on="_vehicle_norm",
        how="left"
    )

    CUSTOMER_VEHICLE_PERIOD_MAX = (
        per_customer.groupby("_customer_key")["So_NPP"].max()
    )

else:
    VEHICLE_PERIOD_ALL = pd.DataFrame()
    VEHICLE_PERIOD = pd.DataFrame()
    CUSTOMER_VEHICLE_PERIOD_MAX = pd.Series(dtype=float)


# ============================================================
# 19. NPP SỬ DỤNG NHIỀU KHO TRONG CÙNG NGÀY
# ============================================================

if not CUSTOMER_CAR.empty:

    MULTI_WH_DAILY = (
        CUSTOMER_CAR[
            CUSTOMER_CAR["_warehouse_code"].ne("")
        ]
        .groupby(["_customer_key", "_date_only"])
        ["_warehouse_code"]
        .nunique()
    )

    CUSTOMER_MULTI_WH_MAX = MULTI_WH_DAILY.groupby(
        "_customer_key"
    ).max()

else:
    CUSTOMER_MULTI_WH_MAX = pd.Series(dtype=float)


# ============================================================
# 20. TẦN SUẤT CHỨNG TỪ TRONG NGÀY
# ============================================================

if not CUSTOMER_CAR.empty:

    if document_col:

        DAILY = (
            CUSTOMER_CAR.groupby(
                ["_customer_key", "_customer_name", "_date_only"]
            )[document_col]
            .nunique()
            .reset_index(name="So_chung_tu")
        )

    else:

        DAILY = (
            CUSTOMER_CAR.groupby(
                ["_customer_key", "_customer_name", "_date_only"]
            )
            .size()
            .reset_index(name="So_chung_tu")
        )

    CUSTOMER_DAILY_MAX = DAILY.groupby(
        "_customer_key"
    )["So_chung_tu"].max()

else:
    DAILY = pd.DataFrame()
    CUSTOMER_DAILY_MAX = pd.Series(dtype=float)


# ============================================================
# 21. DÒNG DỮ LIỆU NGHI TRÙNG
# ============================================================

if document_col and item_code_col:

    duplicate_keys = [
        "_customer_key",
        "_date_only",
        document_col,
        item_code_col
    ]

    if quantity_col:
        duplicate_keys.append(quantity_col)

    DUPLICATE_ROWS = DF[
        DF.duplicated(
            subset=duplicate_keys,
            keep=False
        )
    ].copy()

else:
    DUPLICATE_ROWS = DF.iloc[0:0].copy()


if not DUPLICATE_ROWS.empty:

    CUSTOMER_DUPLICATE = (
        DUPLICATE_ROWS.groupby("_customer_key").size()
    )

else:
    CUSTOMER_DUPLICATE = pd.Series(dtype=float)


# ============================================================
# 22. SẢN LƯỢNG ĐỘT BIẾN THEO THÁNG
# ============================================================

MONTHLY = (
    DF.groupby(["_customer_key", "_month"])
    .agg(
        Doanh_thu=("_revenue", "sum"),
        San_luong=("_quantity", "sum"),
        Khoi_luong=("_weight", "sum")
    )
    .reset_index()
)

SPIKE_DETAILS = []
SPIKE_CUSTOMERS = set()

for customer_key, group in MONTHLY.groupby("_customer_key"):

    group = group.sort_values("_month").reset_index(drop=True)

    if len(group) < 4:
        continue

    for i in range(3, len(group)):

        history = group.loc[:i - 1, "San_luong"]
        baseline = history.median()
        current = group.loc[i, "San_luong"]

        if baseline > 0 and current >= baseline * 3:

            SPIKE_CUSTOMERS.add(customer_key)

            SPIKE_DETAILS.append({
                "Mã NPP": customer_key,
                "Tháng": group.loc[i, "_month"],
                "Sản lượng tháng": current,
                "Trung vị các tháng trước": baseline,
                "Số lần tăng": round(current / baseline, 2)
            })

SPIKE_TABLE = pd.DataFrame(SPIKE_DETAILS)


# ============================================================
# 23. TỔNG HỢP NPP
# ============================================================

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
        Ti_le_thieu_dia_diem=(
            "_address_norm",
            lambda x: (x == "").mean()
        )
    )
    .reset_index()
)

CUSTOMER["NPP_trung_dia_diem"] = (
    CUSTOMER["_customer_key"]
    .map(CUSTOMER_ADDRESS_MAX)
    .fillna(1)
)

CUSTOMER["NPP_cung_xe_cung_ngay"] = (
    CUSTOMER["_customer_key"]
    .map(CUSTOMER_VEHICLE_DAY_MAX)
    .fillna(1)
)

CUSTOMER["NPP_cung_xe_trong_ky"] = (
    CUSTOMER["_customer_key"]
    .map(CUSTOMER_VEHICLE_PERIOD_MAX)
    .fillna(1)
)

CUSTOMER["Nhieu_kho_cung_ngay"] = (
    CUSTOMER["_customer_key"]
    .map(CUSTOMER_MULTI_WH_MAX)
    .fillna(1)
)

CUSTOMER["Max_chung_tu_ngay"] = (
    CUSTOMER["_customer_key"]
    .map(CUSTOMER_DAILY_MAX)
    .fillna(0)
)

CUSTOMER["Dong_trung"] = (
    CUSTOMER["_customer_key"]
    .map(CUSTOMER_DUPLICATE)
    .fillna(0)
)

CUSTOMER["San_luong_dot_bien"] = (
    CUSTOMER["_customer_key"].isin(SPIKE_CUSTOMERS)
)


# ============================================================
# 24. TỔNG HỢP KHO
# ============================================================

if not CUSTOMER_CAR.empty:

    WH_CUSTOMER = (
        CUSTOMER_CAR.groupby("_customer_key")
        .agg(
            So_giao_dich_xe_KH=("_customer_name", "size"),
            Kho_ngoai_danh_sach=(
                "_warehouse_status",
                lambda x: (x == "Ngoài danh sách").sum()
            ),
            Kho_trong_danh_sach=(
                "_warehouse_status",
                lambda x: (x == "Trong danh sách").sum()
            ),
            Thieu_ma_kho=(
                "_warehouse_status",
                lambda x: (x == "Thiếu mã kho").sum()
            ),
            Chua_xac_dinh_vung=(
                "_warehouse_status",
                lambda x: x.isin([
                    "Chưa xác định vùng",
                    "Thiếu địa điểm",
                    "Chưa cấu hình kho"
                ]).sum()
            )
        )
        .reset_index()
    )

    CUSTOMER = CUSTOMER.merge(
        WH_CUSTOMER,
        on="_customer_key",
        how="left"
    )

else:

    for col in [
        "So_giao_dich_xe_KH",
        "Kho_ngoai_danh_sach",
        "Kho_trong_danh_sach",
        "Thieu_ma_kho",
        "Chua_xac_dinh_vung"
    ]:
        CUSTOMER[col] = 0


CUSTOMER = CUSTOMER.fillna({
    "So_giao_dich_xe_KH": 0,
    "Kho_ngoai_danh_sach": 0,
    "Kho_trong_danh_sach": 0,
    "Thieu_ma_kho": 0,
    "Chua_xac_dinh_vung": 0
})

CUSTOMER["Ti_le_kho_ngoai"] = (
    CUSTOMER["Kho_ngoai_danh_sach"]
    /
    (
        CUSTOMER["Kho_ngoai_danh_sach"]
        + CUSTOMER["Kho_trong_danh_sach"]
    ).replace(0, np.nan)
).fillna(0)


# ============================================================
# 25. ĐIỂM RỦI RO
# Tổng trọng số 100 điểm
# ============================================================

def score_warehouse(row):

    total = (
        row["Kho_ngoai_danh_sach"]
        + row["Kho_trong_danh_sach"]
    )

    if total == 0:
        return 0

    ratio = row["Ti_le_kho_ngoai"]

    if ratio >= 0.50:
        return 25
    if ratio >= 0.20:
        return 18
    if ratio > 0:
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


def score_multi_warehouse(n):
    if n >= 3:
        return 5
    if n == 2:
        return 3
    return 0


CUSTOMER["Diem_kho"] = CUSTOMER.apply(
    score_warehouse,
    axis=1
)

CUSTOMER["Diem_dia_diem"] = (
    CUSTOMER["NPP_trung_dia_diem"].apply(score_address)
)

CUSTOMER["Diem_xe_cung_ngay"] = (
    CUSTOMER["NPP_cung_xe_cung_ngay"].apply(score_vehicle_day)
)

CUSTOMER["Diem_xe_trong_ky"] = (
    CUSTOMER["NPP_cung_xe_trong_ky"].apply(score_vehicle_period)
)

CUSTOMER["Diem_tan_suat"] = np.where(
    CUSTOMER["Max_chung_tu_ngay"] >= daily_limit * 2,
    5,
    np.where(
        CUSTOMER["Max_chung_tu_ngay"] >= daily_limit,
        3,
        0
    )
)

CUSTOMER["Diem_nhieu_kho"] = (
    CUSTOMER["Nhieu_kho_cung_ngay"].apply(score_multi_warehouse)
)

CUSTOMER["Diem_san_luong"] = np.where(
    CUSTOMER["San_luong_dot_bien"],
    5,
    0
)

CUSTOMER["Diem_trung_du_lieu"] = np.where(
    CUSTOMER["Dong_trung"] >= 5,
    3,
    np.where(CUSTOMER["Dong_trung"] > 0, 1, 0)
)

CUSTOMER["Diem_thieu_dia_diem"] = np.where(
    CUSTOMER["Ti_le_thieu_dia_diem"] >= 0.25,
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
    "Diem_san_luong",
    "Diem_trung_du_lieu",
    "Diem_thieu_dia_diem"
]

CUSTOMER["Tong_diem"] = (
    CUSTOMER[SCORE_COLS].sum(axis=1)
).clip(0, 100)

CUSTOMER["Muc_do"] = CUSTOMER["Tong_diem"].apply(risk_level)


# ============================================================
# 26. NHẬN ĐỊNH VÀ GIẢI PHÁP
# ============================================================

def make_reason(row):

    reasons = []

    if row["Diem_kho"] > 0:
        reasons.append(
            f"Có {int(row['Kho_ngoai_danh_sach'])} giao dịch "
            "lấy hàng ngoài danh sách kho vùng."
        )

    if row["Diem_dia_diem"] > 0:
        reasons.append(
            f"Địa điểm có liên quan {int(row['NPP_trung_dia_diem'])} NPP."
        )

    if row["Diem_xe_cung_ngay"] > 0:
        reasons.append(
            f"Một xe phục vụ tối đa "
            f"{int(row['NPP_cung_xe_cung_ngay'])} NPP trong cùng ngày."
        )

    if row["Diem_xe_trong_ky"] > 0:
        reasons.append(
            f"Một xe được sử dụng bởi "
            f"{int(row['NPP_cung_xe_trong_ky'])} NPP trong kỳ."
        )

    if row["Diem_nhieu_kho"] > 0:
        reasons.append(
            f"Sử dụng tối đa {int(row['Nhieu_kho_cung_ngay'])} kho trong ngày."
        )

    if row["Diem_tan_suat"] > 0:
        reasons.append(
            f"Có ngày phát sinh {int(row['Max_chung_tu_ngay'])} chứng từ."
        )

    if row["Diem_san_luong"] > 0:
        reasons.append("Sản lượng có tháng tăng đột biến so với lịch sử.")

    if row["Diem_trung_du_lieu"] > 0:
        reasons.append(
            f"Có {int(row['Dong_trung'])} dòng dữ liệu nghi trùng."
        )

    if row["Diem_thieu_dia_diem"] > 0:
        reasons.append("Thiếu địa điểm ở nhiều giao dịch.")

    return " ".join(reasons) if reasons else "Chưa phát hiện dấu hiệu bất thường."


def make_action(row):

    actions = []

    if row["Diem_kho"] > 0:
        actions.append(
            "Kiểm tra phiếu xuất kho, xác minh lý do lấy hàng ngoài vùng, "
            "đối chiếu phê duyệt ngoại lệ."
        )

    if row["Diem_dia_diem"] > 0:
        actions.append(
            "Kiểm tra hồ sơ pháp lý, địa điểm kinh doanh thực tế, "
            "người đại diện và thông tin liên hệ các NPP."
        )

    if row["Diem_xe_cung_ngay"] > 0 or row["Diem_xe_trong_ky"] > 0:
        actions.append(
            "Đối chiếu biển số xe, chủ xe, người lái, phiếu xuất kho "
            "và xác minh việc dùng chung phương tiện."
        )

    if row["Diem_nhieu_kho"] > 0:
        actions.append(
            "Kiểm tra lý do NPP lấy hàng tại nhiều kho trong ngày, "
            "đối chiếu chứng từ và phê duyệt."
        )

    if row["Diem_tan_suat"] > 0:
        actions.append(
            "Kiểm tra tần suất lấy hàng, việc chia nhỏ đơn và "
            "nhu cầu kinh doanh thực tế."
        )

    if row["Diem_san_luong"] > 0:
        actions.append(
            "Đối chiếu đơn đặt hàng, tồn kho, giao nhận và khả năng tiêu thụ."
        )

    if row["Diem_trung_du_lieu"] > 0:
        actions.append(
            "Đối chiếu số chứng từ gốc và dòng hàng để xác định trùng dữ liệu."
        )

    if row["Diem_thieu_dia_diem"] > 0:
        actions.append("Yêu cầu bổ sung và cập nhật địa điểm NPP.")

    return " ".join(actions) if actions else "Tiếp tục giám sát định kỳ."


CUSTOMER["Nhan_dinh"] = CUSTOMER.apply(make_reason, axis=1)
CUSTOMER["Giai_phap"] = CUSTOMER.apply(make_action, axis=1)

CUSTOMER = CUSTOMER.sort_values(
    "Tong_diem",
    ascending=False
)


# ============================================================
# 27. BẢNG KHO VÀ SẢN PHẨM
# ============================================================

if not CUSTOMER_CAR.empty:

    WAREHOUSE_RESULT = (
        CUSTOMER_CAR.groupby(
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
    WAREHOUSE_RESULT = pd.DataFrame()


product_col = item_name_col or item_code_col

if product_col:

    PRODUCT_RESULT = (
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
    PRODUCT_RESULT = pd.DataFrame()


# ============================================================
# 28. KPI
# ============================================================

TOTAL_REVENUE = DF["_revenue"].sum()
TOTAL_QTY = DF["_quantity"].sum()
TOTAL_WEIGHT = DF["_weight"].sum()

N_CUSTOMER = DF["_customer_key"].nunique()
N_VEHICLE = VEHICLE_DATA["_vehicle_norm"].nunique()

N_HIGH = CUSTOMER["Muc_do"].isin(["Cao", "Rất cao"]).sum()

N_ADDRESS = len(ADDRESS_GROUP)

N_VEHICLE_DAY = len(VEHICLE_DAY)
N_VEHICLE_PERIOD = len(VEHICLE_PERIOD)

N_WAREHOUSE_OUTSIDE = (
    (CUSTOMER_CAR["_warehouse_status"] == "Ngoài danh sách").sum()
    if not CUSTOMER_CAR.empty else 0
)


# ============================================================
# 29. GIAO DIỆN TỔNG QUAN
# ============================================================

st.markdown("---")

st.markdown(
    '<div class="section-title">TỔNG QUAN HOẠT ĐỘNG NPP</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Số NPP", f"{N_CUSTOMER:,}")
c2.metric("Doanh thu", f"{TOTAL_REVENUE:,.0f}")
c3.metric("Sản lượng", f"{TOTAL_QTY:,.0f}")
c4.metric("Khối lượng", f"{TOTAL_WEIGHT:,.0f}")
c5.metric("Xe khách hàng", f"{N_VEHICLE:,}")
c6.metric("NPP rủi ro cao", f"{N_HIGH:,}")

st.caption(
    f"Đã loại {removed_z:,} dòng mã hàng Z và "
    f"{removed_discount:,} dòng hàng chiết khấu."
)

T1, T2, T3, T4, T5, T6 = st.tabs([
    "📊 Tổng quan",
    "🏭 Kho lấy hàng",
    "📍 Địa chỉ",
    "🚚 Xe khách hàng",
    "📦 Doanh thu & Mặt hàng",
    "⚠️ Rủi ro NPP"
])


# ============================================================
# TAB 1 - TỔNG QUAN
# ============================================================

with T1:

    st.markdown(
        '<div class="section-title">PHÂN BỐ MỨC ĐỘ RỦI RO</div>',
        unsafe_allow_html=True
    )

    distribution = (
        CUSTOMER["Muc_do"]
        .value_counts()
        .reindex(LEVELS, fill_value=0)
        .rename_axis("Muc_do")
        .reset_index(name="So_NPP")
    )

    fig = px.bar(
        distribution,
        x="Muc_do",
        y="So_NPP",
        color="Muc_do",
        text="So_NPP",
        color_discrete_map=LEVEL_COLORS
    )

    fig.update_layout(
        paper_bgcolor="#07111e",
        plot_bgcolor="#07111e",
        font_color="#c5d7eb",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    a, b, c, d = st.columns(4)

    a.metric("NPP trùng địa điểm", N_ADDRESS)
    b.metric("Xe nhiều NPP cùng ngày", N_VEHICLE_DAY)
    c.metric("Xe nhiều NPP trong kỳ", N_VEHICLE_PERIOD)
    d.metric("Giao dịch ngoài danh sách kho", N_WAREHOUSE_OUTSIDE)

    st.markdown(
        '<div class="section-title">TOP 20 NPP CẦN KIỂM TRA</div>',
        unsafe_allow_html=True
    )

    st.dataframe(
        CUSTOMER.head(20)[[
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
        '<div class="section-title">ĐỐI CHIẾU KHO THEO ĐỊA ĐIỂM NPP</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Chỉ sử dụng hình thức Xe khách hàng. "
        "Xe nhà máy và xe thuê ngoài không được đưa vào đối chiếu."
    )

    if CUSTOMER_CAR.empty:

        st.warning("Không có giao dịch xe khách hàng.")

    else:

        status_summary = (
            CUSTOMER_CAR["_warehouse_status"]
            .value_counts()
            .rename_axis("Trạng thái")
            .reset_index(name="Số giao dịch")
        )

        st.dataframe(
            status_summary,
            use_container_width=True,
            hide_index=True
        )

        mismatch = CUSTOMER_CAR[
            CUSTOMER_CAR["_warehouse_status"] == "Ngoài danh sách"
        ]

        st.markdown("### Giao dịch kho ngoài danh sách")

        if mismatch.empty:

            st.success("Không có giao dịch ngoài danh sách kho.")

        else:

            st.warning(
                f"Phát hiện {len(mismatch):,} giao dịch cần xác minh."
            )

            st.dataframe(
                mismatch[[
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
                    "_region": "Khu vực",
                    "_warehouse_code": "Mã kho",
                    "_vehicle_raw": "Biển số xe",
                    "_date": "Ngày",
                    "_revenue": "Doanh thu",
                    "_quantity": "Số lượng",
                    "_weight": "Khối lượng"
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Tổng hợp vùng và kho")

        st.dataframe(
            WAREHOUSE_RESULT,
            use_container_width=True,
            hide_index=True
        )

        unknown = CUSTOMER_CAR[
            CUSTOMER_CAR["_warehouse_status"].isin([
                "Chưa xác định vùng",
                "Thiếu địa điểm",
                "Thiếu mã kho",
                "Chưa cấu hình kho"
            ])
        ]

        if not unknown.empty:
            st.warning(
                f"{len(unknown):,} giao dịch chưa đủ dữ liệu "
                "để kết luận đúng hoặc sai kho."
            )

        st.markdown("### Cách xử lý")

        st.write("""
        1. Xác minh địa điểm NPP.
        2. Đối chiếu mã kho xuất hàng với danh sách kho của vùng.
        3. Kiểm tra phiếu xuất kho và biển số xe.
        4. Kiểm tra trường hợp điều chuyển hoặc thay đổi kho được phê duyệt.
        5. Yêu cầu đơn vị kinh doanh giải trình khi không có chứng từ phù hợp.
        """)


# ============================================================
# TAB 3 - ĐỊA CHỈ TRÙNG
# ============================================================

with T3:

    st.markdown(
        '<div class="section-title">CÁC NPP TRÙNG ĐỊA ĐIỂM</div>',
        unsafe_allow_html=True
    )

    if ADDRESS_GROUP.empty:

        st.success("Chưa phát hiện địa điểm trùng.")

    else:

        st.warning(
            f"Phát hiện {len(ADDRESS_GROUP):,} nhóm địa điểm có từ 2 NPP."
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

    st.markdown("### Phương án kiểm tra")

    st.write("""
    - Kiểm tra địa chỉ đăng ký và địa điểm hoạt động thực tế.
    - Kiểm tra giấy phép kinh doanh.
    - Đối chiếu người đại diện pháp luật và người liên hệ.
    - Kiểm tra số điện thoại, email và thông tin người nhận hàng.
    - Xác minh việc sử dụng chung kho, cửa hàng hoặc văn phòng.
    """)


# ============================================================
# TAB 4 - XE KHÁCH HÀNG
# ============================================================

with T4:

    st.markdown(
        '<div class="section-title">MỘT XE PHỤC VỤ NHIỀU NPP TRONG CÙNG NGÀY</div>',
        unsafe_allow_html=True
    )

    if VEHICLE_DAY.empty:

        st.success("Chưa phát hiện trường hợp này.")

    else:

        st.warning(
            f"Có {len(VEHICLE_DAY):,} trường hợp xe phục vụ nhiều NPP."
        )

        st.dataframe(
            VEHICLE_DAY.rename(columns={
                "_date_only": "Ngày",
                "Bien_so": "Biển số",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP",
                "So_dia_diem": "Số địa điểm",
                "So_kho": "Số kho",
                "So_giao_dich": "Số giao dịch"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
        '<div class="section-title">MỘT XE PHỤC VỤ NHIỀU NPP TRONG NHIỀU NGÀY</div>',
        unsafe_allow_html=True
    )

    if VEHICLE_PERIOD.empty:

        st.success("Chưa phát hiện xe dùng chung trong kỳ.")

    else:

        st.warning(
            f"Có {len(VEHICLE_PERIOD):,} xe liên quan nhiều NPP."
        )

        st.dataframe(
            VEHICLE_PERIOD.rename(columns={
                "Bien_so": "Biển số",
                "So_NPP": "Số NPP",
                "Danh_sach_NPP": "Danh sách NPP",
                "So_ngay": "Số ngày hoạt động",
                "So_dia_diem": "Số địa điểm",
                "So_kho": "Số kho",
                "So_giao_dich": "Số giao dịch"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### Phương án kiểm soát")

    st.write("""
    1. Xác minh chủ xe, người điều khiển phương tiện.
    2. Đối chiếu thời điểm lấy hàng của từng NPP.
    3. Kiểm tra phiếu xuất hàng, người nhận hàng.
    4. Xác minh việc dùng chung xe có thỏa thuận hay không.
    5. Kiểm tra mối liên hệ giữa các NPP sử dụng chung phương tiện.
    """)


# ============================================================
# TAB 5 - DOANH THU VÀ SẢN PHẨM
# ============================================================

with T5:

    st.markdown(
        '<div class="section-title">DOANH THU VÀ SẢN LƯỢNG THEO THÁNG</div>',
        unsafe_allow_html=True
    )

    MONTHLY_SUMMARY = (
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

    c1, c2 = st.columns(2)

    with c1:

        fig = px.bar(
            MONTHLY_SUMMARY,
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

    with c2:

        fig = px.line(
            MONTHLY_SUMMARY,
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

    st.markdown("### Phân tích mặt hàng")

    if PRODUCT_RESULT.empty:
        st.info("Không có cột mã hàng hoặc tên hàng.")
    else:
        st.dataframe(
            PRODUCT_RESULT,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### Sản lượng đột biến")

    if SPIKE_TABLE.empty:
        st.success("Chưa phát hiện tháng có sản lượng tăng gấp 3 lần trung vị lịch sử.")
    else:
        st.dataframe(
            SPIKE_TABLE,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 6 - ĐIỂM RỦI RO NPP
# ============================================================

with T6:

    st.markdown(
        '<div class="section-title">BẢNG ĐIỂM RỦI RO NPP</div>',
        unsafe_allow_html=True
    )

    SCORE_TABLE = CUSTOMER[[
        "NPP",
        "Diem_kho",
        "Diem_dia_diem",
        "Diem_xe_cung_ngay",
        "Diem_xe_trong_ky",
        "Diem_tan_suat",
        "Diem_nhieu_kho",
        "Diem_san_luong",
        "Diem_trung_du_lieu",
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
        "Diem_san_luong": "Sản lượng /5",
        "Diem_trung_du_lieu": "Trùng dữ liệu /3",
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

    st.markdown("### Xem chi tiết một NPP")

    selected_npp = st.selectbox(
        "Chọn Nhà Phân Phối",
        CUSTOMER["NPP"].tolist()
    )

    detail = CUSTOMER[
        CUSTOMER["NPP"] == selected_npp
    ].iloc[0]

    st.metric(
        "Điểm rủi ro",
        f"{int(detail['Tong_diem'])}/100",
        delta=detail["Muc_do"]
    )

    css_class = {
        "Thấp": "risk-green",
        "Theo dõi": "risk-yellow",
        "Cao": "risk-orange",
        "Rất cao": "risk-red"
    }[detail["Muc_do"]]

    st.markdown(
        f'<div class="{css_class}">'
        f'<b>NHẬN ĐỊNH:</b> {detail["Nhan_dinh"]}<br><br>'
        f'<b>GIẢI PHÁP:</b> {detail["Giai_phap"]}'
        f'</div>',
        unsafe_allow_html=True
    )

    reason_table = pd.DataFrame({
        "Nhóm rủi ro": [
            "Kho ngoài danh sách",
            "NPP trùng địa điểm",
            "Xe nhiều NPP cùng ngày",
            "Xe nhiều NPP trong kỳ",
            "Tần suất lấy hàng",
            "Nhiều kho trong ngày",
            "Sản lượng đột biến",
            "Dòng dữ liệu trùng",
            "Thiếu địa điểm"
        ],
        "Điểm": [
            detail["Diem_kho"],
            detail["Diem_dia_diem"],
            detail["Diem_xe_cung_ngay"],
            detail["Diem_xe_trong_ky"],
            detail["Diem_tan_suat"],
            detail["Diem_nhieu_kho"],
            detail["Diem_san_luong"],
            detail["Diem_trung_du_lieu"],
            detail["Diem_thieu_dia_diem"]
        ]
    })

    fig = px.bar(
        reason_table,
        x="Điểm",
        y="Nhóm rủi ro",
        orientation="h",
        text="Điểm",
        title="Cơ cấu điểm rủi ro"
    )

    fig.update_layout(
        paper_bgcolor="#07111e",
        plot_bgcolor="#07111e",
        font_color="#c5d7eb"
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 30. XUẤT EXCEL AN TOÀN
# ============================================================

st.markdown("---")
st.markdown(
    '<div class="section-title">XUẤT BÁO CÁO PHÂN TÍCH</div>',
    unsafe_allow_html=True
)

# Chỉ xuất các cột được lựa chọn và các chỉ tiêu đã chuẩn hóa.
# Không xuất giá bán, giá vốn, lợi nhuận hay biên lợi nhuận.

SAFE_SOURCE_COLUMNS = [
    customer_col,
    customer_id_col,
    group_col,
    date_col,
    document_col,
    location_col,
    warehouse_col,
    method_col,
    vehicle_col,
    revenue_col,
    quantity_col,
    weight_col,
    item_code_col,
    item_name_col
]

SAFE_SOURCE_COLUMNS = list(dict.fromkeys(
    c for c in SAFE_SOURCE_COLUMNS
    if c and c in DF.columns
))

SAFE_DETAIL = DF[SAFE_SOURCE_COLUMNS].copy()

SAFE_DETAIL["_Vung"] = DF["_region"]
SAFE_DETAIL["_Ma_kho_chuan_hoa"] = DF["_warehouse_code"]
SAFE_DETAIL["_Loai_xe"] = DF["_vehicle_type"]

SAFE_CAR = CUSTOMER_CAR[
    SAFE_SOURCE_COLUMNS
].copy()

SAFE_CAR["_Vung"] = CUSTOMER_CAR["_region"]
SAFE_CAR["_Trang_thai_kho"] = CUSTOMER_CAR["_warehouse_status"]
SAFE_CAR["_Bien_so_chuan_hoa"] = CUSTOMER_CAR["_vehicle_norm"]

export_file = io.BytesIO()

with pd.ExcelWriter(
    export_file,
    engine="openpyxl"
) as writer:

    CUSTOMER.to_excel(
        writer,
        sheet_name="Tong_hop_rui_ro",
        index=False
    )

    SAFE_DETAIL.to_excel(
        writer,
        sheet_name="Du_lieu_da_loc",
        index=False
    )

    SAFE_CAR.to_excel(
        writer,
        sheet_name="Xe_khach_hang",
        index=False
    )

    WAREHOUSE_RESULT.to_excel(
        writer,
        sheet_name="Tong_hop_kho",
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

    DUPLICATE_ROWS[
        SAFE_SOURCE_COLUMNS
    ].to_excel(
        writer,
        sheet_name="Dong_nghi_trung",
        index=False
    )

    SPIKE_TABLE.to_excel(
        writer,
        sheet_name="San_luong_dot_bien",
        index=False
    )

    PRODUCT_RESULT.to_excel(
        writer,
        sheet_name="Mat_hang",
        index=False
    )

export_file.seek(0)

st.download_button(
    "TẢI BÁO CÁO RỦI RO NPP - EXCEL",
    data=export_file.getvalue(),
    file_name="Bao_cao_rui_ro_NPP.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ============================================================
# 31. THANG MÀU
# ============================================================

st.markdown("---")

st.markdown(
    '<div class="section-title">THANG ĐÁNH GIÁ</div>',
    unsafe_allow_html=True
)

a, b, c, d = st.columns(4)

with a:
    st.markdown(
        '<div class="risk-green"><b>XANH - THẤP</b><br>0–24 điểm</div>',
        unsafe_allow_html=True
    )

with b:
    st.markdown(
        '<div class="risk-yellow"><b>VÀNG - THEO DÕI</b><br>25–44 điểm</div>',
        unsafe_allow_html=True
    )

with c:
    st.markdown(
        '<div class="risk-orange"><b>CAM - CAO</b><br>45–64 điểm</div>',
        unsafe_allow_html=True
    )

with d:
    st.markdown(
        '<div class="risk-red"><b>ĐỎ - RẤT CAO</b><br>65–100 điểm</div>',
        unsafe_allow_html=True
    )

st.caption(
    "Điểm rủi ro là công cụ sàng lọc để ưu tiên kiểm tra, "
    "không phải kết luận vi phạm. Dấu hiệu dùng chung xe hoặc địa điểm "
    "cần được xác minh bằng chứng từ."
)
