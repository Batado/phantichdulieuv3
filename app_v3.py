import io
import re
import unicodedata
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from modules.control_center import render_control_center


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

# Quy tắc địa chỉ -> nhóm khu vực -> danh sách mã kho chấp nhận.
# Danh sách được giữ đúng theo ma trận người dùng cung cấp; không tự mở rộng kho.
ADDRESS_WAREHOUSE_RULES = {
    "Miền Bắc": {
        "keywords": [
            "hai phong", "thanh pho hai phong", "ha noi", "thanh pho ha noi",
            "hung yen", "bac ninh", "quang ninh", "ninh binh", "thanh hoa",
            "nghe an", "ha tinh", "tuyen quang", "phu tho", "thai nguyen",
            "lao cai", "lai chau", "son la", "dien bien", "xa nghia dan",
            "xa kim anh", "phuong tam thanh", "phuong quyet thang", "phuong minh xuan"
        ],
        "warehouses": {"261", "291"},
    },
    "Miền Trung - Huế và Quảng Trị": {
        "keywords": ["hue", "thua thien hue", "quang tri"],
        "warehouses": {"251", "261", "263"},
    },
    "Miền Trung - Đà Nẵng": {
        "keywords": ["da nang", "thanh pho da nang"],
        "warehouses": {"251", "263"},
    },
    "Miền Trung - Khánh Hòa và Quảng Ngãi": {
        "keywords": ["khanh hoa", "quang ngai"],
        "warehouses": {"251", "263", "053", "284"},
    },
    "Miền Trung - Tây Nguyên": {
        "keywords": [
            "dak lak", "daklak", "gia lai", "lam dong", "xa duc lap",
            "xa cat tien 2", "xa cat tien", "xa nam ban lam ha", "xa quang lap",
            "xa duc trong", "phuong lam vien da lat"
        ],
        "warehouses": {"251", "252", "263", "053", "054", "284"},
    },
    "Miền Nam - Đông Nam Bộ": {
        "keywords": [
            "dong nai", "thanh pho dong nai", "ho chi minh", "thanh pho ho chi minh",
            "tay ninh", "binh duong", "ba ria vung tau", "ba ria vung tau",
            "quan thu duc", "phuong thong nhat"
        ],
        "warehouses": {"053", "054", "281", "284"},
    },
    "Miền Nam - Tây Nam Bộ": {
        "keywords": ["an giang", "dong thap", "vinh long", "can tho", "thanh pho can tho", "ca mau"],
        "warehouses": {"053", "054", "281", "284"},
    },
}
# Dùng Miền2 chỉ khi địa chỉ không đủ thông tin để nhận diện tỉnh/thành.
# Tây Nguyên được gộp vào Miền Trung - Tây Nguyên, tuyệt đối không gán Miền Bắc.
BROAD_REGION_RULES = {
    "Miền Bắc": {"261", "291"},
    "Miền Trung": {"251", "261", "263", "053", "284"},
    "Miền Trung - Tây Nguyên": {"251", "252", "263", "053", "054", "284"},
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
    "warehouse_region_file": ["Kho lấy hàng vùng miền", "Kho lấy hàng theo vùng miền", "Kho vùng miền", "Danh sách kho hợp lý theo vùng"],
    "warehouse_note_file": [
        "Ghi chú hợp lý hoặc không hợp lý", "Ghi chú hợp lý/không hợp lý",
        "Ghi chú hợp lý hay không hợp lý", "Ghi chú kho", "Đánh giá kho",
        "Nhận xét kho", "Kết luận kho", "Nhận định kho lấy hàng"
    ],
    "method": ["Hình thức vận chuyển", "Phương thức vận chuyển", "Loại vận chuyển", "Shipping Method"],
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
    """
    Xác định vùng theo TỈNH/THÀNH PHỐ ghi trong địa chỉ trước.
    Chỉ dùng Miền2 gốc làm dự phòng khi địa chỉ không có tỉnh/thành nhận diện được.

    Lý do: tên xã/phường có thể trùng tên tỉnh cũ hoặc tỉnh khác
    (ví dụ Xã Tuyên Quang thuộc Tỉnh Lâm Đồng). Không được dò chuỗi
    toàn địa chỉ rồi chọn từ khóa dài nhất vì sẽ gán nhầm địa bàn.
    """
    raw_address = clean(address)
    address_norm = norm(raw_address)

    # Tỉnh/thành phố là cấp địa giới có độ tin cậy cao nhất trong địa chỉ.
    # Tách theo dấu phẩy để không nhầm tên xã/phường với tên tỉnh.
    province_region = {
        "ha noi": "Miền Bắc",
        "hai phong": "Miền Bắc",
        "hung yen": "Miền Bắc",
        "bac ninh": "Miền Bắc",
        "quang ninh": "Miền Bắc",
        "ninh binh": "Miền Bắc",
        "thanh hoa": "Miền Bắc",
        "nghe an": "Miền Bắc",
        "ha tinh": "Miền Bắc",
        "tuyen quang": "Miền Bắc",
        "phu tho": "Miền Bắc",
        "thai nguyen": "Miền Bắc",
        "lao cai": "Miền Bắc",
        "lai chau": "Miền Bắc",
        "son la": "Miền Bắc",
        "dien bien": "Miền Bắc",

        "hue": "Miền Trung - Huế và Quảng Trị",
        "thua thien hue": "Miền Trung - Huế và Quảng Trị",
        "quang tri": "Miền Trung - Huế và Quảng Trị",
        "da nang": "Miền Trung - Đà Nẵng",
        "khanh hoa": "Miền Trung - Khánh Hòa và Quảng Ngãi",
        "quang ngai": "Miền Trung - Khánh Hòa và Quảng Ngãi",
        "dak lak": "Miền Trung - Tây Nguyên",
        "daklak": "Miền Trung - Tây Nguyên",
        "gia lai": "Miền Trung - Tây Nguyên",
        "lam dong": "Miền Trung - Tây Nguyên",

        "dong nai": "Miền Nam - Đông Nam Bộ",
        "ho chi minh": "Miền Nam - Đông Nam Bộ",
        "tay ninh": "Miền Nam - Đông Nam Bộ",
        "binh duong": "Miền Nam - Đông Nam Bộ",
        "ba ria vung tau": "Miền Nam - Đông Nam Bộ",

        "an giang": "Miền Nam - Tây Nam Bộ",
        "dong thap": "Miền Nam - Tây Nam Bộ",
        "vinh long": "Miền Nam - Tây Nam Bộ",
        "can tho": "Miền Nam - Tây Nam Bộ",
        "ca mau": "Miền Nam - Tây Nam Bộ",
    }

    province_segments = []
    for segment in re.split(r"[,;|]", raw_address):
        seg = norm(segment).strip()
        if seg.startswith("tinh "):
            province_segments.append(seg[len("tinh "):].strip())
        elif seg.startswith("thanh pho "):
            province_segments.append(seg[len("thanh pho "):].strip())

    # Ưu tiên tỉnh/thành được ghi rõ; kiểm tra từ cuối địa chỉ về đầu
    # để ưu tiên phần địa giới hành chính chính thức gần cuối địa chỉ.
    for province in reversed(province_segments):
        if province in province_region:
            return province_region[province]

    # Dự phòng cho địa chỉ không ghi tiền tố "Tỉnh/Thành phố".
    # Chỉ dò từng thành phần địa chỉ, không dò chuỗi toàn địa chỉ.
    address_keywords = {
        "Miền Bắc": [
            "hai phong", "ha noi", "hung yen", "bac ninh", "quang ninh",
            "ninh binh", "thanh hoa", "nghe an", "ha tinh", "phu tho",
            "thai nguyen", "lao cai", "lai chau", "son la", "dien bien",
            "xa nghia dan", "xa kim anh", "phuong tam thanh",
            "phuong quyet thang", "phuong minh xuan"
        ],
        "Miền Trung - Huế và Quảng Trị": ["hue", "thua thien hue", "quang tri"],
        "Miền Trung - Đà Nẵng": ["da nang"],
        "Miền Trung - Khánh Hòa và Quảng Ngãi": ["khanh hoa", "quang ngai"],
        "Miền Trung - Tây Nguyên": [
            "dak lak", "daklak", "gia lai", "lam dong", "xa duc lap",
            "xa cat tien 2", "xa cat tien", "xa nam ban lam ha",
            "xa quang lap", "xa duc trong", "phuong lam vien da lat"
        ],
        "Miền Nam - Đông Nam Bộ": [
            "dong nai", "ho chi minh", "tay ninh", "binh duong",
            "ba ria vung tau", "quan thu duc", "phuong thong nhat"
        ],
        "Miền Nam - Tây Nam Bộ": ["an giang", "dong thap", "vinh long", "can tho", "ca mau"],
    }
    address_parts = [norm(x).strip() for x in re.split(r"[,;|]", raw_address) if norm(x).strip()]
    for group, keywords in address_keywords.items():
        for part in address_parts:
            for keyword in keywords:
                key = norm(keyword)
                if part == key or part.endswith(" " + key) or part.startswith(key + " "):
                    return group

    # Không suy đoán từ tên xã/phường nếu tỉnh/thành đã không nhận diện được.
    # Dùng Miền2 gốc làm dự phòng và chuẩn hóa Tây Nguyên về Miền Trung - Tây Nguyên.
    r = norm(region_value)
    if "tay nguyen" in r:
        return "Miền Trung - Tây Nguyên"
    if "mien bac" in r or r == "bac":
        return "Miền Bắc"
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


def extract_warehouse_codes(value):
    """Trích mã kho 3 chữ số từ cột kho lấy hàng vùng miền trong workbook."""
    return set(re.findall(r"(?<!\d)(\d{3})(?!\d)", clean(value)))


def classify_workbook_note(value):
    """Ghi chú gốc là nguồn tham khảo bổ sung, không thay thế kiểm tra theo địa chỉ."""
    text = norm(value)
    if not text:
        return "Không có ghi chú trong file"
    if any(x in text for x in ["khong hop ly", "khong hop le", "khong phu hop", "bat hop ly", "sai kho"]):
        return "File ghi chú: không hợp lý"
    if any(x in text for x in ["hop ly", "phu hop", "dung kho"]):
        return "File ghi chú: hợp lý"
    return "Ghi chú khác - cần đọc nội dung"


def combine_warehouse_review(base_status, warehouse, file_region_text, file_note):
    """Đối chiếu độc lập theo địa chỉ, danh sách kho vùng miền và ghi chú có sẵn."""
    listed_codes = extract_warehouse_codes(file_region_text)
    note_status = classify_workbook_note(file_note)
    if warehouse in SPECIAL_WAREHOUSES:
        return WAREHOUSE_STATUS_SPECIAL
    if listed_codes and warehouse and warehouse not in listed_codes:
        return "Không khớp danh sách kho vùng miền trong file"
    if note_status == "File ghi chú: không hợp lý":
        if base_status in {"Phù hợp địa chỉ/khu vực", WAREHOUSE_STATUS_FALLBACK}:
            return "Mâu thuẫn: thuật toán phù hợp nhưng file ghi không hợp lý"
        return "Theo ghi chú file: không hợp lý - cần xác minh"
    if note_status == "File ghi chú: hợp lý" and base_status == WAREHOUSE_STATUS_OUTSIDE:
        return "Mâu thuẫn: file ghi hợp lý nhưng kho ngoài vùng địa chỉ"
    return base_status


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
    st.info("Tải báo cáo Excel để bắt đầu phân tích mới. Bạn vẫn có thể truy cập hồ sơ kiểm soát và sổ phát hiện đã lưu ở bên dưới.")
    render_control_center(data_ready=False)
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
df["_kho_vung_file"] = get_col("warehouse_region_file").map(clean)
df["_ghi_chu_kho_file"] = get_col("warehouse_note_file").map(clean)
df["_ghi_chu_kho_chuan_hoa"] = df["_ghi_chu_kho_file"].map(classify_workbook_note)
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
df["_doi_chieu_kho_tong_hop"] = [
    combine_warehouse_review(base, code, file_region, file_note)
    for base, code, file_region, file_note in zip(
        df["_doi_chieu_kho"], df["_ma_kho"],
        df["_kho_vung_file"], df["_ghi_chu_kho_file"]
    )
]
df["_kho_hop_ly_theo_dia_chi"] = [
    ", ".join(sorted(allowed_warehouses_for_region(region)[0]))
    if allowed_warehouses_for_region(region)[0] else ""
    for region in df["_vung"]
]
df["_ly_do_doi_chieu_kho"] = [
    (
        f"Địa chỉ thuộc {region}; kho thực tế {code} - {warehouse_name(code)}; "
        f"kho chấp nhận: {', '.join(sorted(allowed_warehouses_for_region(region)[0]))}."
        if allowed_warehouses_for_region(region)[0] and code in WAREHOUSE_NAMES
        else (
            f"Chưa xác định được khu vực từ địa chỉ/miền; mã kho chứng từ: {code or 'trống'}."
            if not allowed_warehouses_for_region(region)[0]
            else f"Không trích xuất được mã kho hợp lệ từ số chứng từ: {code or 'trống'}."
        )
    )
    for region, code in zip(df["_vung"], df["_ma_kho"])
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
    regions_found = sorted(x for x in npp["_vung"].unique() if x)
    selected_regions = st.multiselect("Vùng / nhóm địa chỉ", regions_found, default=regions_found)
    customers_found = sorted(npp["_ten_kh"].dropna().unique().tolist())
    selected_customers = st.multiselect(
        "NPP (để trống = tất cả)",
        customers_found,
        default=[],
    )

# Base population keeps all available dates for historical behavior analysis.
history_filtered = npp.copy()
if selected_regions:
    history_filtered = history_filtered[history_filtered["_vung"].isin(selected_regions)]
if selected_customers:
    history_filtered = history_filtered[history_filtered["_ten_kh"].isin(selected_customers)]

valid_dates = history_filtered["_ngay"].dropna()
if valid_dates.empty:
    st.warning("Không có ngày chứng từ hợp lệ. Hệ thống chỉ có thể hiển thị dữ liệu chưa nhận diện.")
    st.stop()

st.markdown('<div class="section-title">KỲ BÁO CÁO</div>', unsafe_allow_html=True)
period_col, value_col, previous_col, next_col = st.columns([1.1, 2.2, 0.7, 0.7])
with period_col:
    report_period_type = st.radio(
        "Chu kỳ",
        ["Tuần", "Tháng", "Năm"],
        horizontal=True,
        key="business_report_period_type",
    )

if report_period_type == "Tuần":
    period_values = sorted(valid_dates.dt.strftime("%G-W%V").unique().tolist())
elif report_period_type == "Tháng":
    period_values = sorted(valid_dates.dt.strftime("%Y-%m").unique().tolist())
else:
    period_values = sorted(valid_dates.dt.strftime("%Y").unique().tolist())

period_select_key = f"business_report_period_{report_period_type}"
if period_select_key not in st.session_state or st.session_state[period_select_key] not in period_values:
    st.session_state[period_select_key] = period_values[-1]

current_idx = period_values.index(st.session_state[period_select_key])
with previous_col:
    if st.button("◀ Kỳ trước", use_container_width=True, disabled=current_idx == 0):
        st.session_state[period_select_key] = period_values[current_idx - 1]
with next_col:
    if st.button("Kỳ sau ▶", use_container_width=True, disabled=current_idx >= len(period_values) - 1):
        st.session_state[period_select_key] = period_values[current_idx + 1]

with value_col:
    selected_period_value = st.selectbox(
        "Kỳ đang đánh giá",
        period_values,
        index=period_values.index(st.session_state[period_select_key]),
        key=period_select_key,
        format_func=lambda x: (
            f"Tuần {x.split('-W')[-1]}/{x.split('-W')[0]}"
            if report_period_type == "Tuần"
            else (
                f"Tháng {x[5:7]}/{x[:4]}"
                if report_period_type == "Tháng"
                else f"Năm {x}"
            )
        ),
    )

if report_period_type == "Tuần":
    iso_year, iso_week = [int(x) for x in selected_period_value.split("-W")]
    report_start = date.fromisocalendar(iso_year, iso_week, 1)
    report_end = report_start + timedelta(days=6)
    previous_start = report_start - timedelta(days=7)
    previous_end = report_start - timedelta(days=1)
elif report_period_type == "Tháng":
    selected_month = pd.Period(selected_period_value, freq="M")
    previous_month = selected_month - 1
    report_start = selected_month.start_time.date()
    report_end = selected_month.end_time.date()
    previous_start = previous_month.start_time.date()
    previous_end = previous_month.end_time.date()
else:
    selected_year = int(selected_period_value)
    report_start = date(selected_year, 1, 1)
    report_end = date(selected_year, 12, 31)
    previous_start = date(selected_year - 1, 1, 1)
    previous_end = date(selected_year - 1, 12, 31)

period_scope = history_filtered.copy()
filtered = period_scope[
    period_scope["_ngay"].notna()
    & (period_scope["_ngay"].dt.date >= report_start)
    & (period_scope["_ngay"].dt.date <= report_end)
].copy()
comparison_filtered = period_scope[
    period_scope["_ngay"].notna()
    & (period_scope["_ngay"].dt.date >= previous_start)
    & (period_scope["_ngay"].dt.date <= previous_end)
].copy()

if filtered.empty:
    st.warning(
        f"Không có giao dịch trong kỳ {report_start:%d/%m/%Y} – {report_end:%d/%m/%Y}. "
        "Hãy chọn kỳ khác hoặc kiểm tra dữ liệu ngày chứng từ."
    )
    st.stop()

# Product Z-prefix rows are discount rows and excluded from revenue/product analytics.
sales = filtered[~filtered["_ma_hang_z"]].copy()
history_sales = history_filtered[~history_filtered["_ma_hang_z"]].copy()
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
warehouse_evidence_statuses = {
    WAREHOUSE_STATUS_OUTSIDE,
    "Không khớp danh sách kho vùng miền trong file",
    "Theo ghi chú file: không hợp lý - cần xác minh",
    "Mâu thuẫn: thuật toán phù hợp nhưng file ghi không hợp lý",
    "Mâu thuẫn: file ghi hợp lý nhưng kho ngoài vùng địa chỉ",
    "Không khớp danh sách kho vùng miền trong file",
}
warehouse_evidence = customer_vehicle[
    customer_vehicle["_doi_chieu_kho_tong_hop"].isin(warehouse_evidence_statuses)
].copy()
warehouse_special = customer_vehicle[
    customer_vehicle["_doi_chieu_kho_tong_hop"] == WAREHOUSE_STATUS_SPECIAL
].copy()
warehouse_unknown = customer_vehicle[
    customer_vehicle["_doi_chieu_kho_tong_hop"].isin([
        "Không trích xuất được mã kho từ số chứng từ",
        "Mã kho chưa có trong danh mục",
        "Chưa đủ dữ liệu địa chỉ/vùng",
        "Chưa xác định vùng",
    ])
].copy()
warehouse_counts = (
    customer_vehicle.groupby("_doi_chieu_kho_tong_hop")
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

# ============================================================
# MONTHLY CUSTOMER BEHAVIOR / BUSINESS SHIFT ANALYSIS
# ============================================================

valid_sales_dates = history_sales["_ngay"].dropna() if "_ngay" in history_sales.columns else pd.Series(dtype="datetime64[ns]")
month_list = (
    pd.period_range(
        valid_sales_dates.min().to_period("M"),
        valid_sales_dates.max().to_period("M"),
        freq="M"
    ).astype(str).tolist()
    if not valid_sales_dates.empty else []
)
monthly_customer = (
    history_sales[history_sales["_thang"].ne("")]
    .groupby(["_customer_key", "_ten_kh", "_thang"], as_index=False)
    .agg(
        Doanh_thu=("_doanh_thu", "sum"),
        San_luong=("_san_luong", "sum"),
        So_chung_tu=("_chung_tu", "nunique"),
    )
)

# Monthly panel inserts zero-sales months so inactivity is visible.
if month_list:
    customer_index = sales[["_customer_key", "_ten_kh"]].drop_duplicates()
    panel_index = customer_index.assign(_join=1).merge(
        pd.DataFrame({"_thang": month_list, "_join": 1}),
        on="_join"
    ).drop(columns="_join")
    monthly_panel = panel_index.merge(
        monthly_customer,
        on=["_customer_key", "_ten_kh", "_thang"],
        how="left"
    )
    for metric in ["Doanh_thu", "San_luong", "So_chung_tu"]:
        monthly_panel[metric] = monthly_panel[metric].fillna(0)
else:
    monthly_panel = pd.DataFrame()

# User selects a break month: before/after comparison mirrors business review periods,
# e.g. Jan-May versus Jun-Nov. Default is the midpoint of available months.
if len(month_list) >= 2:
    default_cut_index = max(0, min(len(month_list) - 2, 4))
    with st.sidebar:
        st.markdown("## 5. SO SÁNH BIẾN ĐỘNG")
        split_month = st.selectbox(
            "Tháng kết thúc kỳ trước",
            options=month_list[:-1],
            index=default_cut_index,
            help="Ví dụ chọn tháng 05 để so sánh bình quân tháng 01-05 với tháng 06-11."
        )
        decline_threshold = st.slider(
            "Ngưỡng giảm doanh thu/sản lượng (%)",
            min_value=20, max_value=90, value=50, step=5
        )
        growth_threshold = st.slider(
            "Ngưỡng tăng doanh thu/sản lượng (%)",
            min_value=50, max_value=300, value=100, step=25
        )
        shift_materiality = st.slider(
            "Tỷ trọng tối thiểu để xem xét dịch chuyển mặt hàng (%)",
            min_value=1, max_value=20, value=5, step=1,
            help="Chỉ ghép cặp khi mức giảm/tăng của từng NPP có ý nghĩa so với tổng sản lượng mã hàng trong cùng vùng."
        )
    split_index = month_list.index(split_month)
    prior_months = month_list[:split_index + 1]
    later_months = month_list[split_index + 1:]
else:
    split_month = month_list[0] if month_list else ""
    prior_months = month_list
    later_months = []
    decline_threshold = 50
    growth_threshold = 100
    shift_materiality = 5

# Compare averages per calendar month, not only active months.
# This makes the "active before, quiet later" pattern visible.
period_rows = []
if not monthly_panel.empty and prior_months and later_months:
    for key, group in monthly_panel.groupby(["_customer_key", "_ten_kh"], sort=False):
        before = group[group["_thang"].isin(prior_months)]
        after = group[group["_thang"].isin(later_months)]
        before_rev = float(before["Doanh_thu"].sum())
        after_rev = float(after["Doanh_thu"].sum())
        before_qty = float(before["San_luong"].sum())
        after_qty = float(after["San_luong"].sum())
        before_rev_avg = before_rev / len(prior_months)
        after_rev_avg = after_rev / len(later_months)
        before_qty_avg = before_qty / len(prior_months)
        after_qty_avg = after_qty / len(later_months)

        rev_change = (
            (after_rev_avg / before_rev_avg - 1) * 100
            if before_rev_avg > 0 else np.nan
        )
        qty_change = (
            (after_qty_avg / before_qty_avg - 1) * 100
            if before_qty_avg > 0 else np.nan
        )
        prior_active = int((before["San_luong"] > 0).sum())
        later_active = int((after["San_luong"] > 0).sum())

        if before_qty > 0 and after_qty == 0:
            pattern = "Ngừng lấy hàng trong kỳ sau"
        elif before_qty_avg > 0 and (
            (pd.notna(qty_change) and qty_change <= -decline_threshold)
            or (pd.notna(rev_change) and rev_change <= -decline_threshold)
        ):
            pattern = "Giảm mạnh so với kỳ trước"
        elif before_qty == 0 and after_qty > 0:
            pattern = "Mới phát sinh / quay lại mua hàng"
        elif before_qty_avg > 0 and (
            (pd.notna(qty_change) and qty_change >= growth_threshold)
            or (pd.notna(rev_change) and rev_change >= growth_threshold)
        ):
            pattern = "Tăng mạnh so với kỳ trước"
        else:
            pattern = "Tương đối ổn định"

        period_rows.append({
            "_customer_key": key[0],
            "NPP": key[1],
            "Tháng kết thúc kỳ trước": split_month,
            "Số tháng kỳ trước": len(prior_months),
            "Số tháng kỳ sau": len(later_months),
            "Doanh thu kỳ trước": before_rev,
            "Doanh thu kỳ sau": after_rev,
            "DT bình quân/tháng trước": before_rev_avg,
            "DT bình quân/tháng sau": after_rev_avg,
            "Biến động doanh thu %": rev_change,
            "Sản lượng kỳ trước": before_qty,
            "Sản lượng kỳ sau": after_qty,
            "SL bình quân/tháng trước": before_qty_avg,
            "SL bình quân/tháng sau": after_qty_avg,
            "Biến động sản lượng %": qty_change,
            "Số tháng có lấy hàng kỳ trước": prior_active,
            "Số tháng có lấy hàng kỳ sau": later_active,
            "Mẫu hình": pattern,
        })

customer_monthly_review = pd.DataFrame(period_rows)

# Same product + same region: identify potential offsetting volume changes
# between distributors. This is only a review lead, not proof of customer transfer.
product_shift_rows = []
if not monthly_panel.empty and prior_months and later_months and not sales.empty:
    p = history_sales[
        history_sales["_ma_hang"].ne("")
        & sales["_ma_hang_z"].eq(False)
        & sales["_vung"].ne("Chưa xác định vùng")
    ].copy()

    if not p.empty:
        sku_period = (
            p.groupby(
                ["_vung", "_ma_hang", "_ten_hang", "_customer_key", "_ten_kh", "_thang"],
                as_index=False
            )["_san_luong"].sum()
        )
        sku_period["_ky"] = np.where(
            sku_period["_thang"].isin(prior_months), "Trước",
            np.where(sku_period["_thang"].isin(later_months), "Sau", "Ngoài kỳ")
        )
        sku_period = sku_period[sku_period["_ky"].isin(["Trước", "Sau"])]
        sku_compare = (
            sku_period.groupby(
                ["_vung", "_ma_hang", "_ten_hang", "_customer_key", "_ten_kh", "_ky"],
                as_index=False
            )["_san_luong"].sum()
        )
        sku_pivot = sku_compare.pivot_table(
            index=["_vung", "_ma_hang", "_ten_hang", "_customer_key", "_ten_kh"],
            columns="_ky", values="_san_luong", aggfunc="sum", fill_value=0
        ).reset_index()
        if "Trước" not in sku_pivot.columns:
            sku_pivot["Trước"] = 0.0
        if "Sau" not in sku_pivot.columns:
            sku_pivot["Sau"] = 0.0

        sku_pivot["Chênh lệch SL"] = sku_pivot["Sau"] - sku_pivot["Trước"]
        sku_pivot["Tỷ lệ biến động %"] = np.where(
            sku_pivot["Trước"] > 0,
            (sku_pivot["Sau"] / sku_pivot["Trước"] - 1) * 100,
            np.nan
        )
        sku_pivot["_tong_truoc_ma_vung"] = sku_pivot.groupby(
            ["_vung", "_ma_hang"]
        )["Trước"].transform("sum")
        sku_pivot["_tong_sau_ma_vung"] = sku_pivot.groupby(
            ["_vung", "_ma_hang"]
        )["Sau"].transform("sum")
        sku_pivot["_ty_trong_giam"] = np.where(
            sku_pivot["_tong_truoc_ma_vung"] > 0,
            (sku_pivot["Trước"] - sku_pivot["Sau"]) / sku_pivot["_tong_truoc_ma_vung"] * 100,
            0
        )
        sku_pivot["_ty_trong_tang"] = np.where(
            sku_pivot["_tong_sau_ma_vung"] > 0,
            (sku_pivot["Sau"] - sku_pivot["Trước"]) / sku_pivot["_tong_sau_ma_vung"] * 100,
            0
        )
        decreases = sku_pivot[
            (sku_pivot["Trước"] > 0)
            & (sku_pivot["Sau"] <= sku_pivot["Trước"] * (1 - decline_threshold / 100))
            & (sku_pivot["_ty_trong_giam"] >= shift_materiality)
        ].copy()
        increases = sku_pivot[
            (sku_pivot["Sau"] > 0)
            & (
                (sku_pivot["Trước"] == 0)
                | (sku_pivot["Sau"] >= sku_pivot["Trước"] * (1 + growth_threshold / 100))
            )
            & (sku_pivot["_ty_trong_tang"] >= shift_materiality)
        ].copy()

        # Keep only the strongest 5 decreases and 5 increases per region/SKU
        # to bound join size and keep Streamlit responsive on larger workbooks.
        if not decreases.empty:
            decreases = (
                decreases.assign(_drop_qty=decreases["Trước"] - decreases["Sau"])
                .sort_values("_drop_qty", ascending=False)
                .groupby(["_vung", "_ma_hang"], group_keys=False)
                .head(5)
                .drop(columns="_drop_qty")
            )
        if not increases.empty:
            increases = (
                increases.assign(_rise_qty=increases["Sau"] - increases["Trước"])
                .sort_values("_rise_qty", ascending=False)
                .groupby(["_vung", "_ma_hang"], group_keys=False)
                .head(5)
                .drop(columns="_rise_qty")
            )

        # Limit the number of pairs and work only within the same region/SKU.
        if not decreases.empty and not increases.empty:
            pairs = decreases.merge(
                increases,
                on=["_vung", "_ma_hang"],
                suffixes=("_A", "_B"),
                how="inner"
            )
            pairs = pairs[pairs["_customer_key_A"] != pairs["_customer_key_B"]].copy()
            if not pairs.empty:
                pairs["Sản lượng NPP A giảm"] = pairs["Trước_A"] - pairs["Sau_A"]
                pairs["Sản lượng NPP B tăng"] = pairs["Sau_B"] - pairs["Trước_B"]
                pairs["Mức bù trừ tương đối %"] = np.where(
                    pairs["Sản lượng NPP A giảm"] > 0,
                    np.minimum(
                        pairs["Sản lượng NPP B tăng"] / pairs["Sản lượng NPP A giảm"],
                        1.0
                    ) * 100,
                    0
                )
                pairs = pairs.sort_values(
                    ["Mức bù trừ tương đối %", "Sản lượng NPP A giảm"],
                    ascending=False
                ).head(500)

                for _, row in pairs.iterrows():
                    product_shift_rows.append({
                        "_customer_key_A": row["_customer_key_A"],
                        "_customer_key_B": row["_customer_key_B"],
                        "Vùng": row["_vung"],
                        "Mã hàng": row["_ma_hang"],
                        "Tên hàng": row["_ten_hang_A"] or row["_ten_hang_B"],
                        "NPP giảm": row["_ten_kh_A"],
                        "NPP tăng": row["_ten_kh_B"],
                        "SL NPP giảm kỳ trước": row["Trước_A"],
                        "SL NPP giảm kỳ sau": row["Sau_A"],
                        "SL NPP tăng kỳ trước": row["Trước_B"],
                        "SL NPP tăng kỳ sau": row["Sau_B"],
                        "SL giảm của A": row["Sản lượng NPP A giảm"],
                        "SL tăng của B": row["Sản lượng NPP B tăng"],
                        "Mức bù trừ tương đối %": row["Mức bù trừ tương đối %"],
                        "Nhận định": "Cùng mặt hàng và vùng có NPP giảm mạnh trong khi NPP khác tăng/mới phát sinh; cần kiểm tra phân bổ thị trường, điều chuyển khách hàng và chương trình kinh doanh.",
                    })

product_shift_review = pd.DataFrame(product_shift_rows)

# Month-level abrupt changes against the median of up to 3 preceding months.
# Requiring prior activity avoids treating a new NPP as a sudden spike.
monthly_anomaly_rows = []
if not monthly_panel.empty and len(month_list) >= 4:
    for (customer_key, customer_name), group in monthly_panel.groupby(
        ["_customer_key", "_ten_kh"], sort=False
    ):
        group = group.sort_values("_thang").reset_index(drop=True)
        for i in range(3, len(group)):
            history = group.iloc[max(0, i - 3):i]
            current = group.iloc[i]
            q_base = float(history["San_luong"].median())
            r_base = float(history["Doanh_thu"].median())
            q_now = float(current["San_luong"])
            r_now = float(current["Doanh_thu"])
            q_change = ((q_now / q_base) - 1) * 100 if q_base > 0 else np.nan
            r_change = ((r_now / r_base) - 1) * 100 if r_base > 0 else np.nan

            anomaly = ""
            if q_base > 0 and q_now <= q_base * 0.20:
                anomaly = "Sản lượng giảm đột ngột so với 3 tháng trước"
            elif r_base > 0 and r_now <= r_base * 0.20:
                anomaly = "Doanh thu giảm đột ngột so với 3 tháng trước"
            elif q_base > 0 and q_now >= q_base * 3:
                anomaly = "Sản lượng tăng đột biến so với 3 tháng trước"
            elif r_base > 0 and r_now >= r_base * 3:
                anomaly = "Doanh thu tăng đột biến so với 3 tháng trước"

            if anomaly:
                monthly_anomaly_rows.append({
                    "_customer_key": customer_key,
                    "NPP": customer_name,
                    "Tháng bất thường": current["_thang"],
                    "Loại bất thường": anomaly,
                    "Sản lượng tháng": q_now,
                    "Trung vị sản lượng 3 tháng trước": q_base,
                    "Biến động sản lượng %": q_change,
                    "Doanh thu tháng": r_now,
                    "Trung vị doanh thu 3 tháng trước": r_base,
                    "Biến động doanh thu %": r_change,
                })

monthly_anomalies = pd.DataFrame(monthly_anomaly_rows)

# Summarize monthly risk signals by distributor.
if not customer_monthly_review.empty:
    customer_monthly_review["Co_giam_manh"] = customer_monthly_review["Mẫu hình"].isin([
        "Giảm mạnh so với kỳ trước", "Ngừng lấy hàng trong kỳ sau"
    ])
    customer_monthly_review["Co_tang_manh_hoac_quay_lai"] = customer_monthly_review["Mẫu hình"].isin([
        "Tăng mạnh so với kỳ trước", "Mới phát sinh / quay lại mua hàng"
    ])
    monthly_decline_map = customer_monthly_review.set_index("_customer_key")["Co_giam_manh"]
    monthly_growth_map = customer_monthly_review.set_index("_customer_key")["Co_tang_manh_hoac_quay_lai"]
else:
    monthly_decline_map = pd.Series(dtype=bool)
    monthly_growth_map = pd.Series(dtype=bool)

if not product_shift_review.empty:
    shift_key_set = set(product_shift_review["_customer_key_A"].dropna()) | set(
        product_shift_review["_customer_key_B"].dropna()
    )
else:
    shift_key_set = set()

monthly_anomaly_count = (
    monthly_anomalies.groupby("_customer_key").size()
    if not monthly_anomalies.empty else pd.Series(dtype=float)
)

# Unrecognized data are isolated and not treated as confirmed risk.
unknown_parts = []
for label, mask, reason in [
    ("Thiếu ngày chứng từ", filtered["_ngay"].isna(), "Không nhận diện được ngày chứng từ"),
    ("Thiếu địa chỉ", filtered["_dia_chi"].eq(""), "Thiếu địa chỉ NPP"),
    ("Chưa xác định vùng", filtered["_vung"].eq("Chưa xác định vùng"), "Không xác định được vùng từ Miền2/địa chỉ"),
    ("Không trích xuất được mã kho", filtered["_ma_kho"].eq(""), "Không lấy được 3 số đầu từ Số chứng từ"),
    ("Mã kho chưa có trong danh mục", filtered["_ma_kho"].ne("") & ~filtered["_ma_kho"].isin(WAREHOUSE_NAMES), "Mã kho trích từ chứng từ chưa có trong danh mục mã kho"),
    ("Thiếu danh sách kho vùng miền trong file", filtered["_kho_vung_file"].eq(""), "Không có danh sách kho vùng miền ở dòng dữ liệu này"),
    ("Thiếu ghi chú đánh giá kho trong file", filtered["_ghi_chu_kho_file"].eq(""), "Không có ghi chú hợp lý/không hợp lý ở dòng dữ liệu này"),
    ("Chưa xác định hình thức vận chuyển", filtered["_loai_xe"].eq("Chưa xác định"), "Không phân loại được hình thức vận chuyển"),
    ("Thiếu/không chuẩn biển số", (filtered["_loai_xe"] == "Xe khách hàng") & (~filtered["_bien_so_hop_le"]), "Xe khách hàng thiếu hoặc biển số không đạt định dạng sàng lọc"),
]:
    part = filtered.loc[mask].copy()
    if not part.empty:
        part["_ly_do_chua_nhan_dien"] = reason
        part["_nhom_chua_nhan_dien"] = label
        unknown_parts.append(part)
unrecognized = pd.concat(unknown_parts, ignore_index=True).drop_duplicates("_dong_nguon") if unknown_parts else pd.DataFrame()
missing_date_rows = history_filtered[history_filtered["_ngay"].isna()].copy()
if not missing_date_rows.empty:
    missing_date_rows["_nhom_chua_nhan_dien"] = "Thiếu ngày chứng từ"
    missing_date_rows["_ly_do_chua_nhan_dien"] = "Không có ngày hợp lệ nên không thể gán vào kỳ báo cáo."
    unrecognized = pd.concat([unrecognized, missing_date_rows], ignore_index=True).drop_duplicates("_dong_nguon")

# Risk points are transparent screening weights, not legal conclusions.
# Count distinct business events, not item rows, to avoid inflating risk
# when one invoice contains several product lines.
warehouse_by_customer = (
    warehouse_evidence.groupby("_customer_key")["_chung_tu"].nunique()
    if not warehouse_evidence.empty else pd.Series(dtype=float)
)
vehicle_day_events = (
    vehicle_valid.merge(
        vehicle_day_shared[["_bien_so", "_ngay_only"]],
        on=["_bien_so", "_ngay_only"], how="inner"
    )[["_customer_key", "_bien_so", "_ngay_only"]].drop_duplicates()
    if not vehicle_day_shared.empty else pd.DataFrame()
)
vehicle_day_by_customer = (
    vehicle_day_events.groupby("_customer_key").size()
    if not vehicle_day_events.empty else pd.Series(dtype=float)
)
vehicle_period_events = (
    vehicle_valid.merge(
        vehicle_period_shared[["_bien_so"]],
        on="_bien_so", how="inner"
    )[["_customer_key", "_bien_so"]].drop_duplicates()
    if not vehicle_period_shared.empty else pd.DataFrame()
)
vehicle_period_by_customer = (
    vehicle_period_events.groupby("_customer_key").size()
    if not vehicle_period_events.empty else pd.Series(dtype=float)
)
address_by_customer = (
    address_pairs.merge(address_shared[["_dia_chi_norm"]], on="_dia_chi_norm", how="inner")
    .groupby("_customer_key")["_dia_chi_norm"].nunique()
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
    monthly_row = (
        customer_monthly_review[customer_monthly_review["_customer_key"] == key].iloc[0]
        if not customer_monthly_review.empty and (customer_monthly_review["_customer_key"] == key).any()
        else None
    )
    monthly_pattern = monthly_row["Mẫu hình"] if monthly_row is not None else "Chưa đủ tháng để so sánh"
    monthly_decline = bool(monthly_row["Co_giam_manh"]) if monthly_row is not None and "Co_giam_manh" in monthly_row.index else False
    monthly_growth = bool(monthly_row["Co_tang_manh_hoac_quay_lai"]) if monthly_row is not None and "Co_tang_manh_hoac_quay_lai" in monthly_row.index else False
    product_shift = key in shift_key_set
    month_anomaly_n = int(monthly_anomaly_count.get(key, 0))
    # Transparent screening score. A single sales trend alone is not fraud evidence.
    points_warehouse = min(25, wh_n * 5)
    points_vehicle_same_day = min(15, day_n * 5)
    points_vehicle_period = min(15, period_n * 3)
    points_shared_address = min(10, addr_n * 5)
    points_monthly_decline = 10 if monthly_decline else 0
    points_monthly_growth = 5 if monthly_growth else 0
    points_product_shift = 15 if product_shift else 0
    points_monthly_spikes = min(5, month_anomaly_n * 2)
    score = min(100, sum([
        points_warehouse,
        points_vehicle_same_day,
        points_vehicle_period,
        points_shared_address,
        points_monthly_decline,
        points_monthly_growth,
        points_product_shift,
        points_monthly_spikes,
    ]))
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
    npp_vehicle_rows = (
        customer_vehicle[customer_vehicle["_customer_key"] == key]
        if not customer_vehicle.empty else pd.DataFrame()
    )
    has_customer_vehicle_data = not npp_vehicle_rows.empty
    has_valid_vehicle_data = (
        bool(npp_vehicle_rows["_bien_so_hop_le"].any())
        if has_customer_vehicle_data else False
    )
    comparable_warehouse_statuses = {
        "Phù hợp địa chỉ/khu vực",
        WAREHOUSE_STATUS_FALLBACK,
        WAREHOUSE_STATUS_OUTSIDE,
        "Không khớp danh sách kho vùng miền trong file",
        "Theo ghi chú file: không hợp lý - cần xác minh",
        "Mâu thuẫn: thuật toán phù hợp nhưng file ghi không hợp lý",
        "Mâu thuẫn: file ghi hợp lý nhưng kho ngoài vùng địa chỉ",
        WAREHOUSE_STATUS_SPECIAL,
    }
    has_warehouse_evidence = (
        bool(npp_vehicle_rows["_doi_chieu_kho_tong_hop"].isin(comparable_warehouse_statuses).any())
        if has_customer_vehicle_data else False
    )
    # A distributor is not rated green simply because its vehicle/warehouse
    # evidence is missing or its plate cannot be validated.
    enough = (
        has_critical_fields
        and coverage >= 0.75
        and has_valid_vehicle_data
        and has_warehouse_evidence
    )
    level = make_risk_label(score, enough)
    reasons = []
    actions = []
    if not enough:
        reasons.append(
            "Chưa đủ bằng chứng vận hành để kết luận mức rủi ro thấp/cao; "
            "cần hoàn thiện giao dịch xe khách hàng có biển số hợp lệ và thông tin đối chiếu kho."
        )
        actions.append(
            "Bổ sung biển số, hình thức vận chuyển, địa điểm NPP, số chứng từ và mã kho; "
            "chỉ đánh giá lại sau khi dữ liệu đủ điều kiện."
        )
    if wh_n:
        reasons.append(f"{wh_n} dòng xe khách hàng có mã kho không khớp ma trận địa chỉ hoặc có mâu thuẫn với ghi chú/danh sách kho trong file.")
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
    if monthly_decline:
        reasons.append(
            f"Biến động kinh doanh: {monthly_pattern}; doanh thu kỳ trước {monthly_row['Doanh thu kỳ trước']:,.0f}, "
            f"kỳ sau {monthly_row['Doanh thu kỳ sau']:,.0f}; sản lượng kỳ trước {monthly_row['Sản lượng kỳ trước']:,.0f}, "
            f"kỳ sau {monthly_row['Sản lượng kỳ sau']:,.0f}."
        )
        actions.append("Kiểm tra nguyên nhân sụt giảm: thay đổi địa bàn, mất khách, tồn kho, công nợ, nguồn cung, chính sách bán hàng hoặc thay đổi nhà phân phối.")
    elif monthly_growth:
        reasons.append(
            f"Biến động kinh doanh: {monthly_pattern}; doanh thu kỳ trước {monthly_row['Doanh thu kỳ trước']:,.0f}, "
            f"kỳ sau {monthly_row['Doanh thu kỳ sau']:,.0f}; sản lượng kỳ trước {monthly_row['Sản lượng kỳ trước']:,.0f}, "
            f"kỳ sau {monthly_row['Sản lượng kỳ sau']:,.0f}."
        )
        actions.append("Kiểm tra năng lực tiêu thụ, tồn kho, đơn đặt hàng, hạn mức công nợ và tính bền vững của mức tăng.")
    if product_shift:
        reasons.append("Có mặt trong nhóm cặp NPP cùng vùng/cùng mặt hàng nhưng biến động sản lượng trái chiều.")
        actions.append("Đối chiếu khu vực phụ trách, khách hàng cuối, chính sách bán hàng và khả năng chuyển dịch đơn hàng giữa các NPP.")
    if month_anomaly_n:
        reasons.append(f"Có {month_anomaly_n} tháng phát sinh biến động đột ngột về doanh thu hoặc sản lượng so với 3 tháng liền trước.")
        actions.append("Kiểm tra đơn hàng, chứng từ, tồn kho, tiến độ giao hàng, công nợ và nguyên nhân biến động theo từng tháng.")
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
        "Điểm kho": points_warehouse,
        "Điểm xe cùng ngày": points_vehicle_same_day,
        "Điểm xe nhiều ngày": points_vehicle_period,
        "Điểm địa chỉ trùng": points_shared_address,
        "Điểm giảm/ngừng mua": points_monthly_decline,
        "Điểm tăng/quay lại": points_monthly_growth,
        "Điểm dịch chuyển mặt hàng": points_product_shift,
        "Điểm biến động từng tháng": points_monthly_spikes,
        "Dòng kho ngoài danh sách": wh_n,
        "Dòng xe dùng chung cùng ngày": day_n,
        "Dòng xe dùng chung nhiều ngày": period_n,
        "Dòng địa chỉ trùng": addr_n,
        "Mẫu hình doanh thu/sản lượng": monthly_pattern,
        "Biến động kinh doanh cần kiểm tra": monthly_decline or monthly_growth,
        "Liên quan dịch chuyển mặt hàng": product_shift,
        "Số tháng biến động đột ngột": month_anomaly_n,
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

tab_overview, tab_sales, tab_monthly, tab_warehouse, tab_vehicle, tab_risk, tab_control, tab_unknown = st.tabs([
    "Tổng quan", "Doanh thu & mặt hàng", "Biến động theo tháng",
    "Kho lấy hàng", "Xe khách hàng", "Đánh giá rủi ro",
    "Quản lý kiểm soát", "Chưa nhận diện"
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
            risk_summary[["NPP", "Điểm sàng lọc", "Mức độ", "Dòng kho ngoài danh sách", "Dòng xe dùng chung cùng ngày", "Dòng xe dùng chung nhiều ngày", "Mẫu hình doanh thu/sản lượng", "Liên quan dịch chuyển mặt hàng", "Số tháng biến động đột ngột", "Nhận định"]],
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

with tab_monthly:
    st.markdown('<div class="section-title">BIẾN ĐỘNG DOANH THU VÀ SẢN LƯỢNG THEO NPP</div>', unsafe_allow_html=True)
    if not prior_months or not later_months or customer_monthly_review.empty:
        st.info("Cần ít nhất hai tháng dữ liệu và chọn được mốc chia kỳ để so sánh.")
    else:
        st.caption(
            f"Kỳ trước: {prior_months[0]} đến {prior_months[-1]} | "
            f"Kỳ sau: {later_months[0]} đến {later_months[-1]}. "
            "So sánh bình quân theo tháng, bao gồm cả tháng không mua hàng."
        )
        n_decline = int(customer_monthly_review["Mẫu hình"].isin([
            "Giảm mạnh so với kỳ trước", "Ngừng lấy hàng trong kỳ sau"
        ]).sum())
        n_growth = int(customer_monthly_review["Mẫu hình"].isin([
            "Tăng mạnh so với kỳ trước", "Mới phát sinh / quay lại mua hàng"
        ]).sum())
        k1, k2, k3 = st.columns(3)
        k1.metric("NPP giảm mạnh / ngừng mua", f"{n_decline:,}")
        k2.metric("NPP tăng mạnh / quay lại", f"{n_growth:,}")
        k3.metric("Cặp dịch chuyển cùng mặt hàng", f"{len(product_shift_review):,}")

        st.markdown("### Danh sách NPP biến động đáng chú ý")
        review_view = customer_monthly_review[
            customer_monthly_review["Mẫu hình"] != "Tương đối ổn định"
        ].copy()
        if review_view.empty:
            st.success("Chưa phát hiện NPP biến động vượt ngưỡng đã chọn.")
        else:
            review_view = review_view.sort_values(
                ["Biến động sản lượng %", "Biến động doanh thu %"],
                ascending=True,
                na_position="last"
            )
            st.dataframe(
                review_view[[
                    "NPP", "Mẫu hình",
                    "Doanh thu kỳ trước", "Doanh thu kỳ sau",
                    "Biến động doanh thu %",
                    "Sản lượng kỳ trước", "Sản lượng kỳ sau",
                    "Biến động sản lượng %",
                    "Số tháng có lấy hàng kỳ trước",
                    "Số tháng có lấy hàng kỳ sau"
                ]],
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Diễn biến từng tháng của NPP")
        monthly_customer_options = sorted(
            monthly_panel["_ten_kh"].dropna().unique().tolist()
        ) if not monthly_panel.empty else []
        selected_monthly_customers = st.multiselect(
            "Chọn NPP để xem xu hướng tháng",
            monthly_customer_options,
            default=monthly_customer_options[:5],
            key="monthly_customer_chart"
        )
        if selected_monthly_customers:
            chart_data = monthly_panel[
                monthly_panel["_ten_kh"].isin(selected_monthly_customers)
            ].copy()
            chart_metric = st.radio(
                "Chỉ tiêu biểu đồ",
                ["Doanh thu", "Sản lượng"],
                horizontal=True,
                key="monthly_chart_metric"
            )
            y_col = "Doanh_thu" if chart_metric == "Doanh thu" else "San_luong"
            fig = px.line(
                chart_data,
                x="_thang",
                y=y_col,
                color="_ten_kh",
                markers=True,
                title=f"{chart_metric} theo tháng của NPP được chọn"
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                chart_data[["_ten_kh", "_thang", "Doanh_thu", "San_luong", "So_chung_tu"]].rename(
                    columns={
                        "_ten_kh": "NPP", "_thang": "Tháng",
                        "Doanh_thu": "Doanh thu", "San_luong": "Sản lượng",
                        "So_chung_tu": "Số chứng từ"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Bất thường tăng/giảm đột ngột trong từng tháng")
        if monthly_anomalies.empty:
            st.success("Chưa phát hiện tháng có doanh thu/sản lượng biến động từ 3 lần hoặc giảm xuống 20% trở xuống so với trung vị 3 tháng trước.")
        else:
            st.dataframe(
                monthly_anomalies[[
                    "NPP", "Tháng bất thường", "Loại bất thường",
                    "Sản lượng tháng", "Trung vị sản lượng 3 tháng trước",
                    "Biến động sản lượng %", "Doanh thu tháng",
                    "Trung vị doanh thu 3 tháng trước", "Biến động doanh thu %"
                ]],
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### Dấu hiệu dịch chuyển sản lượng cùng mặt hàng và khu vực")
        st.caption(
            "Đây là danh sách cặp cần xác minh khi một NPP giảm mạnh, NPP khác tăng/mới phát sinh "
            "trên cùng mã hàng và cùng vùng. Không tự động kết luận khách hàng đã chuyển giao."
        )
        if product_shift_review.empty:
            st.success("Chưa phát hiện cặp NPP có biến động trái chiều vượt ngưỡng trên cùng mặt hàng và vùng.")
        else:
            st.warning(f"Có {len(product_shift_review):,} cặp dấu hiệu cần đối chiếu.")
            st.dataframe(
                product_shift_review,
                use_container_width=True,
                hide_index=True
            )
            st.write(
                "Cách xác minh: kiểm tra thay đổi địa bàn phụ trách, khách hàng cuối, "
                "đơn hàng, chương trình bán hàng, tồn kho, chính sách chiết khấu và quyết định "
                "điều chuyển NPP trong cùng thời kỳ."
            )

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
            "_doi_chieu_kho", "_doi_chieu_kho_tong_hop", "_kho_hop_ly_theo_dia_chi",
            "_ly_do_doi_chieu_kho", "_kho_vung_file", "_ghi_chu_kho_file", "_ngay", "_bien_so_goc"
        ]].rename(columns={
            "_ten_kh": "NPP", "_dia_chi": "Địa chỉ", "_mien_goc": "Miền2 gốc",
            "_vung": "Vùng/nhóm địa chỉ", "_ma_kho": "Mã kho từ 3 số đầu chứng từ",
            "_ten_kho": "Tên kho theo danh mục", "_doi_chieu_kho": "Đối chiếu theo địa chỉ",
            "_doi_chieu_kho_tong_hop": "Kết quả tổng hợp",
            "_kho_hop_ly_theo_dia_chi": "Kho được chấp nhận theo địa chỉ",
            "_ly_do_doi_chieu_kho": "Lý do đánh giá",
            "_kho_vung_file": "Kho vùng miền ghi trong file",
            "_ghi_chu_kho_file": "Ghi chú gốc trong file", "_ngay": "Ngày",
            "_chung_tu": "Chứng từ", "_bien_so_goc": "Số xe gốc"
        }), use_container_width=True, hide_index=True)
    st.markdown("### Kho hàng gửi tại HS Home của HSN Phú Mỹ")
    if warehouse_special.empty:
        st.info("Không có giao dịch thuộc mã kho HS Home (282/292).")
    else:
        st.warning("Không xếp 282/292 vào nhóm phù hợp vùng thông thường. Cần kiểm tra vị trí lưu hàng, phiếu nhập/xuất và đơn vị quản lý kho.")
        st.dataframe(warehouse_special[[
            "_ten_kh", "_dia_chi", "_vung", "_chung_tu", "_ma_kho", "_ten_kho",
            "_doi_chieu_kho", "_doi_chieu_kho_tong_hop", "_kho_vung_file",
            "_ghi_chu_kho_file", "_ngay", "_bien_so_goc"
        ]].rename(columns={
            "_ten_kh": "NPP", "_dia_chi": "Địa chỉ", "_vung": "Vùng",
            "_chung_tu": "Chứng từ", "_ma_kho": "Mã kho",
            "_ten_kho": "Tên kho", "_doi_chieu_kho": "Đối chiếu theo địa chỉ",
            "_doi_chieu_kho_tong_hop": "Kết quả tổng hợp",
            "_kho_vung_file": "Kho vùng miền ghi trong file",
            "_ghi_chu_kho_file": "Ghi chú gốc trong file",
            "_ngay": "Ngày", "_bien_so_goc": "Biển số xe"
        }), use_container_width=True, hide_index=True)

    st.markdown("### Giao dịch chưa đủ dữ liệu")
    if warehouse_unknown.empty:
        st.success("Không có giao dịch kho thiếu thông tin.")
    else:
        st.dataframe(warehouse_unknown[[
            "_ten_kh", "_dia_chi", "_mien_goc", "_vung", "_chung_tu",
            "_ma_kho", "_ten_kho", "_doi_chieu_kho", "_doi_chieu_kho_tong_hop",
            "_kho_vung_file", "_ghi_chu_kho_file", "_ngay"
        ]], use_container_width=True, hide_index=True)
    st.markdown("### Cách xử lý đề xuất")
    st.write(
        "1. Xác minh địa chỉ NPP và vùng địa lý thực tế. "
        "2. Lấy 3 số đầu của Số chứng từ (ví dụ 263.18067094 -> 263), rồi tra tên kho trong danh mục. "
        "3. So sánh mã kho với ma trận địa chỉ cụ thể; nếu ngoài danh sách, kiểm tra tuyến đường, khoảng cách, tồn kho và lý do điều phối. "
        "4. Đối chiếu thêm cột Kho lấy hàng vùng miền và Ghi chú hợp lý/không hợp lý trong workbook. Nếu ghi chú trái với kết quả theo địa chỉ, đưa vào nhóm mâu thuẫn để xác minh, không tự động tin một nguồn. "
        "5. Mã 282/292 là kho hàng gửi HS Home, cần kiểm tra riêng địa điểm lưu hàng, phiếu nhập/xuất và đơn vị quản lý. "
        "6. Chỉ kết luận bất thường sau khi đối chiếu hồ sơ, giải trình và phê duyệt ngoại lệ."
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
    st.caption("Điểm là mức ưu tiên sàng lọc theo các tín hiệu quan sát được; không phải kết luận vi phạm. Bảng hiển thị riêng điểm từng nhóm để có thể truy nguyên lý do.")
    st.info(
        "Trọng số tối đa: kho không phù hợp 25 điểm; xe nhiều NPP cùng ngày 15; "
        "xe nhiều NPP trong kỳ 15; địa chỉ trùng 10; giảm/ngừng mua 10; "
        "tăng/quay lại 5; dịch chuyển cùng mặt hàng và vùng 15; biến động đột ngột từng tháng 5. "
        "Tổng tối đa 100 điểm. Một dấu hiệu đơn lẻ không đủ để kết luận vi phạm."
    )
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
            monthly_detail = customer_monthly_review[
                customer_monthly_review["_customer_key"] == detail["Mã khách hàng"]
            ] if not customer_monthly_review.empty else pd.DataFrame()
            if not monthly_detail.empty:
                st.markdown("### So sánh hai kỳ kinh doanh")
                st.dataframe(
                    monthly_detail[[
                        "Tháng kết thúc kỳ trước", "Doanh thu kỳ trước", "Doanh thu kỳ sau",
                        "Biến động doanh thu %", "Sản lượng kỳ trước", "Sản lượng kỳ sau",
                        "Biến động sản lượng %", "Mẫu hình"
                    ]],
                    use_container_width=True,
                    hide_index=True
                )
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

with tab_control:
    control_data = {
        "filtered": filtered,
        "risk_summary": risk_summary,
        "warehouse_evidence": warehouse_evidence,
        "customer_vehicle": customer_vehicle,
        "vehicle_day_shared": vehicle_day_shared,
        "vehicle_period_shared": vehicle_period_shared,
        "address_pairs": address_pairs,
        "address_shared": address_shared,
        "customer_monthly_review": customer_monthly_review,
        "monthly_anomalies": monthly_anomalies,
        "product_shift_review": product_shift_review,
        "monthly_sales": monthly_sales,
        "revenue": total_revenue,
        "quantity": total_qty,
        "sheet_name": selected_sheet,
    }
    render_control_center(
        data_ready=True,
        file_name=uploaded.name,
        file_bytes=file_bytes,
        data=control_data,
    )

# ============================================================
# EXPORT
# ============================================================

st.markdown("---")
st.markdown('<div class="section-title">TẢI KẾT QUẢ PHÂN TÍCH</div>', unsafe_allow_html=True)

export_rows = filtered.copy()
sensitive_value_columns = [
    col for col in export_rows.columns
    if any(token in norm(col) for token in [
        "gia ban", "don gia", "gia von", "loi nhuan",
        "bien loi nhuan", "profit", "unit price", "cost price"
    ])
]
if sensitive_value_columns:
    export_rows = export_rows.drop(columns=sensitive_value_columns, errors="ignore")

export_sheets = {
    "Tong_hop_rui_ro": risk_summary,
    "Doanh_thu_mat_hang": product_summary,
    "Theo_thang": monthly_sales,
    "Bien_dong_NPP_theo_thang": customer_monthly_review,
    "Cap_NPP_dich_chuyen_mat_hang": product_shift_review,
    "Thang_bien_dong_dot_ngot": monthly_anomalies,
    "Bang_panel_NPP_thang": monthly_panel,
    "Kho_can_xac_minh": warehouse_evidence,
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
