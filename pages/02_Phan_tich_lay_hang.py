from __future__ import annotations

import html
import io

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.pickup_analysis import (
    analyze_customer_pickups,
    classify_customer_vehicle,
    classify_vehicle_type,
    norm,
)
from modules.scope_filter import apply_business_scope_filter

st.set_page_config(
    page_title="Phân tích kho lấy hàng | Business Control",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Be Vietnam Pro',sans-serif;}
[data-testid="stAppViewContainer"] {background:#f4f7fb;color:#172b4d;}
[data-testid="stHeader"] {background:rgba(244,247,251,.92);}
section[data-testid="stSidebar"] {background:#eef3f8;border-right:1px solid #dbe4ef;}
.block-container {max-width:1580px;padding-top:1.1rem;padding-bottom:2.5rem;}
.hero {background:linear-gradient(118deg,#102b46 0%,#174d70 58%,#167c83 100%);padding:25px 28px;border-radius:18px;color:white;margin:8px 0 16px;box-shadow:0 10px 30px rgba(16,43,70,.13);}
.hero-kicker {font-size:10px;letter-spacing:.16em;font-weight:800;opacity:.76;}
.hero-title {font-size:26px;font-weight:800;line-height:1.28;margin:6px 0;}
.hero-sub {font-size:13px;opacity:.9;max-width:1050px;line-height:1.55;}
.section-title {font-size:15px;font-weight:800;color:#214c70;margin:10px 0 9px;letter-spacing:.01em;}
.section-note {color:#64748b;font-size:12px;margin-top:-5px;margin-bottom:10px;}
div[data-testid="stMetric"] {background:#fff;border:1px solid #dce5ef;border-radius:12px;padding:12px 14px;box-shadow:0 2px 8px rgba(15,23,42,.025);}
div[data-testid="stDataFrame"] {border:1px solid #dce5ef;border-radius:11px;overflow:hidden;}
div[data-testid="stTabs"] button {font-weight:700;font-size:12px;}
div[data-testid="stDownloadButton"] button {border-radius:10px;font-weight:800;background:#174d70;color:white;border:0;}
div[data-testid="stPageLink"] a {border-radius:10px;font-weight:700;}
.finding {box-shadow:0 2px 8px rgba(15,23,42,.025);transition:box-shadow .15s ease;}
.finding:hover {box-shadow:0 5px 16px rgba(15,23,42,.07);}
div[data-testid="stMetric"] {background:white;border:1px solid #e2e8f0;border-radius:13px;padding:13px 14px;box-shadow:0 2px 8px rgba(15,23,42,.025);}
div[data-testid="stDataFrame"] {border:1px solid #e2e8f0;border-radius:11px;overflow:hidden;}
div[data-testid="stTabs"] button {font-weight:700;}
div[data-testid="stExpander"] {background:white;border:1px solid #e2e8f0;border-radius:12px;}
.finding {background:white;border:1px solid #e2e8f0;border-radius:13px;padding:14px 16px;margin:8px 0;}
.finding-title {font-size:14px;font-weight:800;color:#244c70;margin-bottom:5px;}
.finding-meta {font-size:11px;font-weight:800;letter-spacing:.04em;color:#64748b;margin-bottom:7px;}
.finding-body {font-size:13px;color:#334155;line-height:1.55;}
.pill {display:inline-block;padding:4px 9px;border-radius:30px;font-size:11px;font-weight:800;background:#eef2f7;color:#475569;}
.pill-high {background:#fee2e2;color:#991b1b;}
.pill-watch {background:#fef3c7;color:#92400e;}
.pill-low {background:#dcfce7;color:#166534;}
div[data-testid="stDownloadButton"] button {border-radius:10px;font-weight:700;}

/* Shared compact charcoal theme */
[data-testid="stAppViewContainer"] {background:#0b0f14!important;color:#e5e7eb!important;}
[data-testid="stHeader"] {background:rgba(11,15,20,.94)!important;}
section[data-testid="stSidebar"] {background:#111820!important;border-right:1px solid #263341!important;}
.block-container {max-width:1480px;padding-top:.9rem;padding-bottom:1.5rem;}
.hero {background:linear-gradient(110deg,#151d27 0%,#202c39 100%);border:1px solid #344253;padding:16px 20px;border-radius:12px;color:#f8fafc;margin:6px 0 12px;box-shadow:none;}
.hero-kicker {font-size:9px;letter-spacing:.14em;font-weight:800;color:#93c5fd;}
.hero-title {font-size:20px;font-weight:800;line-height:1.2;margin:5px 0;}
.hero-sub {font-size:11px;color:#cbd5e1;max-width:1000px;line-height:1.45;}
.section-title {font-size:13px;font-weight:800;color:#cbd5e1;margin:8px 0;letter-spacing:.04em;}
.section-note {color:#94a3b8;font-size:11px;margin-top:-4px;margin-bottom:8px;}
div[data-testid="stMetric"] {background:#151d27!important;border:1px solid #2b3948!important;border-radius:9px!important;padding:9px 11px!important;box-shadow:none!important;}
div[data-testid="stMetricLabel"] {color:#94a3b8!important;font-size:10px!important;}
div[data-testid="stMetricValue"] {color:#f8fafc!important;font-size:1.55rem!important;}
div[data-testid="stDataFrame"],div[data-testid="stTable"] {border:1px solid #2b3948;border-radius:9px;overflow:hidden;}
div[data-testid="stTabs"] button {font-weight:700;font-size:11px;color:#aab7c6;}
div[data-testid="stTabs"] button[aria-selected="true"] {color:#93c5fd!important;}
div[data-testid="stExpander"] {background:#131b24;border:1px solid #2b3948;border-radius:9px;}
div[data-testid="stDownloadButton"] button,div[data-testid="stButton"] button {border-radius:8px;font-weight:700;}
div[data-testid="stFileUploader"] section {background:#151d27;border:1px dashed #425366;border-radius:9px;}
.finding {background:#151d27;border:1px solid #2b3948;border-radius:10px;padding:11px 13px;margin:6px 0;box-shadow:none;}
.finding-title {font-size:12px;font-weight:800;color:#e5edf6;margin-bottom:4px;}
.finding-meta {font-size:10px;font-weight:700;letter-spacing:.03em;color:#94a3b8;margin-bottom:6px;}
.finding-body {font-size:11px;color:#cbd5e1;line-height:1.5;}
.pill {display:inline-block;padding:3px 8px;border-radius:20px;font-size:10px;font-weight:800;background:#263341;color:#cbd5e1;}
.pill-high {background:#4a2228;color:#fecaca;}
.pill-watch {background:#49391e;color:#fde68a;}
.pill-low {background:#183d31;color:#bbf7d0;}
hr {border-color:#293746!important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">HOA SEN GROUP  /  CONTROL & ANALYTICS</div>
  <div class="hero-title">PHÂN TÍCH TÍNH HỢP LÝ KHO LẤY HÀNG</div>
  <div class="hero-sub">Đối chiếu địa chỉ Nhà phân phối với ma trận kho · Phân tích xe khách hàng · Tách riêng xe nhà máy và xe nhà máy thuê ngoài · Cảnh báo có căn cứ, có thể giải trình</div>
</div>
""", unsafe_allow_html=True)

ALLOWED_LABELS = [
    "Đơn hàng nội địa",
    "Đơn hàng nội địa DLPP",
    "Trả hàng hủy HĐ",
    "Trả hàng không hủy HĐ",
]
READ_COLUMNS = {norm(x) for x in [
    "Số chứng từ", "Loại đơn hàng", "Ngày chứng từ", "Mã khách hàng",
    "Tên khách hàng", "Loại khách hàng", "Địa chỉ", "Mã kho2", "Mã kho",
    "Kho lấy hàng", "Shipping method", "Hình thức vận chuyển",
    "Số xe", "Biển số xe", "Ghi chú2", "Thành tiền bán", "Số lượng",
    "Khối lượng", "Mã hàng", "Tên hàng", "Miền2", "NPP/Dự án",
]}


def find_col(frame: pd.DataFrame, aliases: list[str]) -> str | None:
    lookup = {norm(c): c for c in frame.columns}
    for alias in aliases:
        if norm(alias) in lookup:
            return lookup[norm(alias)]
    return None


@st.cache_data(show_spinner="Đang đọc workbook và chạy kiểm tra dữ liệu...", max_entries=3)
def process_workbook(file_bytes: bytes) -> dict:
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    sheet_lookup = {norm(s): s for s in xls.sheet_names}
    tx_sheet = sheet_lookup.get("om 055")
    matrix_sheet = sheet_lookup.get("kho lay hang")
    if not tx_sheet or not matrix_sheet:
        raise ValueError(
            "Không tìm thấy đủ sheet 'om-055' và 'kho lấy hàng'. "
            "Sheet hiện có: " + ", ".join(xls.sheet_names)
        )

    raw = pd.read_excel(
        io.BytesIO(file_bytes), sheet_name=tx_sheet, engine="openpyxl",
        usecols=lambda col: norm(col) in READ_COLUMNS,
    )
    matrix = pd.read_excel(io.BytesIO(file_bytes), sheet_name=matrix_sheet, engine="openpyxl")
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.dropna(how="all").copy()

    document_col = find_col(raw, ["Số chứng từ", "Số CT", "Số phiếu"])
    order_type_col = find_col(raw, ["Loại đơn hàng", "Loại giao dịch", "Transaction Type", "Order Type"])
    address_col = find_col(raw, ["Địa chỉ", "Địa chỉ khách hàng", "Địa chỉ KH"])
    method_col = find_col(raw, ["Shipping method", "Hình thức vận chuyển", "Phương thức vận chuyển"])
    warehouse_code_col = find_col(raw, ["Mã kho2", "Mã kho", "Mã kho xuất"])
    warehouse_name_col = find_col(raw, ["Kho lấy hàng", "Kho xuất", "Tên kho"])
    plate_col = find_col(raw, ["Số xe", "Biển số xe", "Biển kiểm soát"])
    customer_id_col = find_col(raw, ["Mã khách hàng", "Mã KH"])
    customer_name_col = find_col(raw, ["Tên khách hàng", "Tên KH", "Khách hàng"])
    date_col = find_col(raw, ["Ngày chứng từ", "Ngày xuất"])
    note_col = find_col(raw, ["Ghi chú2", "Ghi chú", "Diễn giải"])
    revenue_col = find_col(raw, ["Thành tiền bán", "Doanh thu", "Thành tiền"])
    quantity_col = find_col(raw, ["Số lượng", "SL"])
    weight_col = find_col(raw, ["Khối lượng", "KL", "Trọng lượng"])

    required = {
        "Số chứng từ": document_col,
        "Loại đơn hàng": order_type_col,
        "Địa chỉ khách hàng": address_col,
        "Hình thức vận chuyển": method_col,
        "Mã kho/Mã kho2": warehouse_code_col,
    }
    missing = [name for name, col in required.items() if not col]
    if missing:
        raise ValueError("Thiếu cột bắt buộc trong OM-055: " + ", ".join(missing))

    raw["_dong_nguon_excel"] = np.arange(len(raw)) + 2
    scoped, excluded = apply_business_scope_filter(
        raw, document_col=document_col, order_type_col=order_type_col
    )

    method_values = (
        scoped[method_col].fillna("").astype(str).str.strip()
        .replace("", "(Trống)").value_counts().rename_axis("Hình thức vận chuyển")
        .reset_index(name="Số dòng")
    )
    scoped["_loai_xe_phan_nhom"] = scoped[method_col].map(classify_vehicle_type)
    customer_vehicle_mask = scoped["_loai_xe_phan_nhom"].eq("Xe khách hàng")
    factory_vehicle_mask = scoped["_loai_xe_phan_nhom"].eq("Xe nhà máy")
    outsourced_vehicle_mask = scoped["_loai_xe_phan_nhom"].eq("Xe nhà máy thuê ngoài")
    customer_vehicle_source = scoped.loc[customer_vehicle_mask].copy()
    factory_vehicle_source = scoped.loc[factory_vehicle_mask].copy()
    outsourced_vehicle_source = scoped.loc[outsourced_vehicle_mask].copy()
    vehicle_type_summary = (
        scoped["_loai_xe_phan_nhom"].value_counts(dropna=False)
        .rename_axis("Nhóm phương tiện").reset_index(name="Số dòng")
    )

    detail, customer_summary, province_summary = analyze_customer_pickups(
        scoped, matrix,
        address_col=address_col,
        warehouse_code_col=warehouse_code_col,
        document_col=document_col,
        method_col=method_col,
        warehouse_name_col=warehouse_name_col or "Kho lấy hàng",
        plate_col=plate_col or "Số xe",
        customer_id_col=customer_id_col or "Mã khách hàng",
        customer_name_col=customer_name_col or "Tên khách hàng",
        date_col=date_col or "Ngày chứng từ",
        order_type_col=order_type_col,
        note_col=note_col or "Ghi chú2",
        revenue_col=revenue_col or "Thành tiền bán",
        quantity_col=quantity_col or "Số lượng",
        weight_col=weight_col or "Khối lượng",
    )
    if not detail.empty:
        source_line_map = scoped["_dong_nguon_excel"]
        detail["Dòng Excel nguồn"] = detail["_source_index"].map(source_line_map)

    return {
        "sheet": tx_sheet, "matrix_sheet": matrix_sheet,
        "raw": raw, "scoped": scoped, "excluded": excluded,
        "detail": detail, "customer_summary": customer_summary,
        "province_summary": province_summary, "method_values": method_values,
        "customer_vehicle_source": customer_vehicle_source,
        "factory_vehicle_source": factory_vehicle_source,
        "outsourced_vehicle_source": outsourced_vehicle_source,
        "vehicle_type_summary": vehicle_type_summary,
        "columns": {
            "document": document_col, "order_type": order_type_col,
            "method": method_col, "address": address_col,
            "warehouse": warehouse_code_col,
        },
    }


def risk_level(exception_count: int, incomplete_count: int, total: int) -> str:
    if total <= 0:
        return "Chưa đủ dữ liệu"
    ratio = exception_count / total
    if exception_count >= 10 or ratio >= 0.15:
        return "Cao"
    if exception_count > 0 or incomplete_count > 0:
        return "Theo dõi"
    return "Thấp"


def build_ai_findings(result: dict) -> pd.DataFrame:
    raw, scoped, excluded = result["raw"], result["scoped"], result["excluded"]
    detail, customers = result["detail"], result["customer_summary"]
    pn = int(excluded["_ly_do_ngoai_pham_vi"].str.startswith("Số chứng từ bắt đầu bằng PN").sum())
    other = len(excluded) - pn
    vehicle_summary = result.get("vehicle_type_summary", pd.DataFrame())
    vehicle_counts = dict(zip(vehicle_summary.get("Nhóm phương tiện", []), vehicle_summary.get("Số dòng", [])))
    factory_count = int(vehicle_counts.get("Xe nhà máy", 0))
    outsourced_count = int(vehicle_counts.get("Xe nhà máy thuê ngoài", 0))
    findings: list[dict] = [{
        "Biểu tượng": "🧾",
        "Đầu mục đánh giá": "01 · Phạm vi và tính đầy đủ dữ liệu",
        "Mức ưu tiên": "Kiểm soát đầu vào",
        "Kết quả": f"{len(scoped):,}/{len(raw):,} dòng được đưa vào phân tích",
        "Nhận định tự động": (
            f"Đã loại {pn:,} dòng có số chứng từ bắt đầu bằng PN (hàng gửi kho) "
            f"và {other:,} dòng thuộc loại đơn hàng ngoài bốn nhóm được duyệt. "
            "Phạm vi này được áp dụng trước khi chấm điểm rủi ro."
        ),
        "Căn cứ": "Số chứng từ + Loại đơn hàng trong OM-055.",
        "Đề xuất kiểm soát": "Lưu nhật ký dòng bị loại; đối chiếu tổng số dòng nguồn, dòng giữ lại và dòng loại trước khi phát hành báo cáo.",
    }]

    type_counts = scoped["_loai_don_hang_chuan_hoa"].value_counts()
    type_text = "; ".join(
        f"{label}: {int(type_counts.get(key, 0)):,}"
        for key, label in zip(
            ["don hang noi dia", "don hang noi dia dlpp", "tra hang huy hd", "tra hang khong huy hd"],
            ALLOWED_LABELS,
        )
    )
    findings.append({
        "Biểu tượng": "📑",
        "Đầu mục đánh giá": "02 · Cơ cấu loại đơn hàng",
        "Mức ưu tiên": "Thông tin",
        "Kết quả": f"{len(scoped):,} dòng thuộc 4 loại đơn được duyệt",
        "Nhận định tự động": type_text + ".",
        "Căn cứ": "Loại đơn hàng đã chuẩn hóa, không phân biệt hoa/thường, dấu tiếng Việt và tiền tố HBMC.",
        "Đề xuất kiểm soát": "Định kỳ rà soát loại đơn mới phát sinh; không tự động đưa loại mới vào phạm vi khi chưa được phê duyệt.",
    })

    findings.extend([
        {
            "Biểu tượng": "🏭",
            "Đầu mục đánh giá": "08 · Phương tiện xe nhà máy",
            "Mức ưu tiên": "Chưa đủ dữ liệu",
            "Kết quả": f"{factory_count:,} dòng giao dịch được nhận diện",
            "Nhận định tự động": "Đã tách riêng giao dịch xe nhà máy, chưa chấm tính hợp lý kho hoặc biển số trong phiên bản này để tránh suy luận khi chưa có danh mục xe và quy tắc kiểm soát được duyệt.",
            "Căn cứ": "Giá trị hình thức vận chuyển trong OM-055 sau khi lọc PN và loại đơn hàng.",
            "Đề xuất kiểm soát": "Bổ sung biển số xe nhà máy, danh mục xe/đơn vị quản lý, lệnh điều xe và thời gian xuất kho trước khi bật đánh giá tự động.",
        },
        {
            "Biểu tượng": "🚛",
            "Đầu mục đánh giá": "09 · Phương tiện xe nhà máy thuê ngoài",
            "Mức ưu tiên": "Chưa đủ dữ liệu",
            "Kết quả": f"{outsourced_count:,} dòng giao dịch được nhận diện",
            "Nhận định tự động": "Đã tách riêng giao dịch xe nhà máy thuê ngoài. Chưa đánh giá biển số, nhà vận tải, hợp đồng và chi phí khi chưa có dữ liệu xác thực.",
            "Căn cứ": "Giá trị hình thức vận chuyển trong OM-055 sau khi lọc phạm vi.",
            "Đề xuất kiểm soát": "Bổ sung biển số, nhà vận tải, hợp đồng/đơn thuê xe, lệnh điều xe, phiếu xuất kho và chứng từ chi phí vận chuyển.",
        },
    ])

    if detail.empty:
        method_col = result["columns"]["method"]
        method_text = "; ".join(
            f"{r['Hình thức vận chuyển']}: {int(r['Số dòng']):,}"
            for _, r in result["method_values"].head(12).iterrows()
        ) or "Không có dữ liệu hình thức vận chuyển."
        findings.append({
            "Biểu tượng": "🚚",
            "Đầu mục đánh giá": "03 · Xe khách hàng và tính hợp lý kho",
            "Mức ưu tiên": "Chưa đủ dữ liệu",
            "Kết quả": "Chưa nhận diện được giao dịch xe khách hàng",
            "Nhận định tự động": (
                "Bộ lọc phạm vi vẫn hoạt động, nhưng không có giá trị ở cột hình thức vận chuyển "
                "được nhận diện là 'Xe khách hàng'. Các giá trị đọc được: " + method_text
            ),
            "Căn cứ": f"Cột hình thức vận chuyển: {method_col}.",
            "Đề xuất kiểm soát": "Kiểm tra danh mục giá trị Shipping method trong OM-055 và chuẩn hóa nhãn xe khách hàng. Không kết luận kho hợp lý khi chưa có giao dịch để kiểm tra.",
        })
        return pd.DataFrame(findings)

    total = len(detail)
    status = detail["Kết quả đối chiếu"].fillna("")
    fit = int(status.eq("Phù hợp danh mục kho").sum())
    exception = int(status.str.startswith(("Ngoài", "Mâu thuẫn")).sum())
    incomplete = total - fit - exception
    compared = fit + exception
    fit_rate = fit / compared * 100 if compared else np.nan
    affected_customers = int(customers["Số_ngoài_danh_mục"].gt(0).sum()) if not customers.empty else 0
    findings.append({
        "Biểu tượng": "🏭",
        "Đầu mục đánh giá": "03 · Tính hợp lý kho lấy hàng",
        "Mức ưu tiên": risk_level(exception, incomplete, total),
        "Kết quả": f"{fit:,}/{total:,} chứng từ phù hợp" + (f" · {fit_rate:.1f}%" if pd.notna(fit_rate) else ""),
        "Nhận định tự động": (
            f"Ghi nhận {exception:,} chứng từ ngoài danh mục hoặc có mâu thuẫn; "
            f"{incomplete:,} chứng từ chưa đủ dữ liệu; {affected_customers:,} NPP có ít nhất một ngoại lệ. "
            "Tỷ lệ phù hợp chỉ tính trên nhóm có thể đối chiếu."
        ),
        "Căn cứ": "Địa chỉ khách hàng → tỉnh/thành trong sheet kho lấy hàng → mã kho thực tế; đối chiếu thêm Ghi chú2.",
        "Đề xuất kiểm soát": "Xác minh chứng từ ngoài danh mục bằng phiếu xuất kho, tồn kho tại thời điểm xuất, điều phối, lộ trình và phê duyệt ngoại lệ. Ma trận là tiêu chí sàng lọc, không phải kết luận vi phạm.",
    })

    top = customers.sort_values(
        ["Số_ngoài_danh_mục", "Số_chưa_đủ_dữ_liệu", "Số_chứng_từ"],
        ascending=[False, False, False],
    ).head(5)
    top_lines = []
    for _, row in top.iterrows():
        if int(row["Số_ngoài_danh_mục"]) or int(row["Số_chưa_đủ_dữ_liệu"]):
            label = row["Tên khách hàng"] or row["Mã khách hàng"] or "Chưa rõ NPP"
            top_lines.append(
                f"{label}: {int(row['Số_ngoài_danh_mục'])} ngoại lệ, "
                f"{int(row['Số_chưa_đủ_dữ_liệu'])} thiếu dữ liệu"
            )
    findings.append({
        "Biểu tượng": "🔎",
        "Đầu mục đánh giá": "04 · NPP cần ưu tiên xác minh",
        "Mức ưu tiên": "Cao" if affected_customers else ("Theo dõi" if incomplete else "Thấp"),
        "Kết quả": f"{affected_customers:,} NPP có ngoại lệ theo ma trận",
        "Nhận định tự động": "; ".join(top_lines) if top_lines else "Chưa ghi nhận NPP có ngoại lệ kho theo ma trận hiện tại.",
        "Căn cứ": "Số chứng từ ngoài danh mục, mâu thuẫn và dữ liệu chưa đủ theo từng NPP.",
        "Đề xuất kiểm soát": "Chọn mẫu theo NPP có số ngoại lệ lớn và tỷ lệ ngoại lệ cao; yêu cầu giải trình từng chứng từ, không chỉ giải trình tổng hợp.",
    })

    plates = detail["Biển số xe"].fillna("").astype(str).str.strip()
    has_plate = plates.ne("") & ~plates.str.lower().isin(["nan", "none", "null"])
    plate_rows = detail.loc[has_plate].copy()
    plate_rows["_plate_key"] = plates[has_plate].str.upper().str.replace(r"[^A-Z0-9]", "", regex=True).values
    if not plate_rows.empty:
        plate_rows["_npp_key"] = plate_rows["Mã khách hàng"].fillna("").astype(str).str.strip()
        blank_npp = plate_rows["_npp_key"].eq("")
        plate_rows.loc[blank_npp, "_npp_key"] = plate_rows.loc[blank_npp, "Tên khách hàng"].map(norm)
        plate_customer_counts = plate_rows.groupby("_plate_key")["_npp_key"].nunique()
        shared_plates = int(plate_customer_counts.gt(1).sum())
        top_shared = plate_customer_counts[plate_customer_counts.gt(1)].sort_values(ascending=False).head(5)
        shared_text = ", ".join(f"{plate}: {int(count)} NPP" for plate, count in top_shared.items())
    else:
        shared_plates, shared_text = 0, "Chưa có biển số để đối chiếu."
    missing_plates = int((~has_plate).sum())
    findings.append({
        "Biểu tượng": "🚛",
        "Đầu mục đánh giá": "05 · Xe khách hàng và dấu hiệu sử dụng chung",
        "Mức ưu tiên": "Theo dõi" if shared_plates or missing_plates else "Thấp",
        "Kết quả": f"{shared_plates:,} biển số xuất hiện ở nhiều NPP · {missing_plates:,} chứng từ thiếu biển số",
        "Nhận định tự động": (
            f"Biển số dùng chung ghi nhận: {shared_text}. "
            "Việc một xe xuất hiện ở nhiều NPP chỉ là dấu hiệu cần kiểm tra, chưa đủ căn cứ kết luận bất thường."
        ),
        "Căn cứ": "Biển số xe được chuẩn hóa; đếm số mã NPP khác nhau sử dụng cùng biển số.",
        "Đề xuất kiểm soát": "Đối chiếu ngày/giờ xuất hàng, tài xế, người nhận, lộ trình, giấy tờ xe và quan hệ giữa các NPP.",
    })

    missing_address = int(detail["Địa chỉ khách hàng"].fillna("").astype(str).str.strip().eq("").sum())
    missing_warehouse = int(detail["Mã kho thực tế"].fillna("").astype(str).str.strip().eq("").sum())
    missing_note = int(detail["Ghi chú gốc"].fillna("").astype(str).str.strip().eq("").sum())
    findings.append({
        "Biểu tượng": "🧩",
        "Đầu mục đánh giá": "06 · Chất lượng dữ liệu và hồ sơ",
        "Mức ưu tiên": "Cao" if missing_address or missing_warehouse else ("Theo dõi" if missing_plates or missing_note else "Thấp"),
        "Kết quả": f"{missing_address:,} thiếu địa chỉ · {missing_warehouse:,} thiếu mã kho · {missing_note:,} thiếu ghi chú",
        "Nhận định tự động": "Thiếu dữ liệu làm giảm khả năng xác minh và có thể khiến kết quả đối chiếu chưa đầy đủ. Hệ thống giữ riêng nhóm chưa đủ căn cứ, không tự xếp là phù hợp.",
        "Căn cứ": "Địa chỉ khách hàng, mã kho thực tế, Ghi chú2 và biển số xe.",
        "Đề xuất kiểm soát": "Yêu cầu đơn vị kinh doanh hoàn thiện trường dữ liệu bắt buộc; theo dõi tỷ lệ thiếu theo NPP và người lập chứng từ.",
    })

    findings.append({
        "Biểu tượng": "📈",
        "Đầu mục đánh giá": "07 · Doanh thu và sản lượng liên quan",
        "Mức ưu tiên": "Thông tin",
        "Kết quả": (
            f"Doanh thu {detail['Doanh thu'].sum(min_count=1):,.0f} · "
            f"Số lượng {detail['Số lượng'].sum(min_count=1):,.2f} · "
            f"Khối lượng {detail['Khối lượng'].sum(min_count=1):,.2f}"
        ),
        "Nhận định tự động": "Tổng hợp theo sự kiện khách hàng + số chứng từ, không cộng lặp dòng hàng của cùng một chứng từ.",
        "Căn cứ": "Thành tiền bán, số lượng và khối lượng trên các giao dịch xe khách hàng trong phạm vi được duyệt.",
        "Đề xuất kiểm soát": "Đối chiếu doanh thu và sản lượng với kỳ trước, tần suất lấy hàng và quy mô NPP; kiểm tra riêng giao dịch trả hàng.",
    })
    return pd.DataFrame(findings)


uploaded = st.file_uploader(
    "📂 Tải workbook Excel (.xlsx)",
    type=["xlsx"],
    help="Bắt buộc có sheet om-055 và kho lấy hàng. Workbook gốc không bị thay đổi.",
)
if uploaded is None:
    st.info("Tải workbook để chạy phân tích. Hệ thống chỉ đọc dữ liệu, không sửa file gốc.")
    st.stop()

try:
    result = process_workbook(uploaded.getvalue())
except Exception as exc:
    st.error(f"Không thể đọc hoặc phân tích workbook: {exc}")
    with st.expander("Chi tiết lỗi kỹ thuật"):
        st.exception(exc)
    st.stop()

raw, scoped, excluded = result["raw"], result["scoped"], result["excluded"]
detail = result["detail"]
customers = result["customer_summary"]
province_summary = result["province_summary"]
findings = build_ai_findings(result)
pn_count = int(excluded["_ly_do_ngoai_pham_vi"].str.startswith("Số chứng từ bắt đầu bằng PN").sum())
other_excluded = len(excluded) - pn_count

st.markdown('<div class="section-title">01  /  TỔNG QUAN PHẠM VI DỮ LIỆU</div>', unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Tổng dòng OM-055", f"{len(raw):,}")
k2.metric("Dòng được giữ", f"{len(scoped):,}", help="Chỉ gồm 4 loại đơn hàng được phê duyệt và không có số chứng từ PN.")
k3.metric("Chứng từ PN bị loại", f"{pn_count:,}")
k4.metric("Loại đơn hàng khác bị loại", f"{other_excluded:,}")

with st.expander("🧾 Quy tắc lọc đang áp dụng", expanded=False):
    st.write("**Giữ lại:** " + " · ".join(ALLOWED_LABELS))
    st.write("**Loại:** tất cả số chứng từ bắt đầu bằng PN, không phụ thuộc loại đơn; mọi loại đơn hàng ngoài bốn nhóm trên.")
    st.caption("Tiền tố ERP như HBMC được chuẩn hóa trước khi so sánh. Không phân biệt chữ hoa/chữ thường, dấu tiếng Việt và dấu phân cách.")

tabs = st.tabs([
    "01  🧠  AI đánh giá",
    "02  🎯  NPP xác minh",
    "03  🏬  Đối chiếu kho",
    "04  🚚  Xe khách hàng",
    "05  🏭  Xe nhà máy",
    "06  🚛  Thuê ngoài",
    "07  🗂  Nhật ký",
])

with tabs[0]:
    st.markdown('<div class="section-title">🧠 NHẬN ĐỊNH TỰ ĐỘNG THEO TỪNG ĐẦU MỤC</div>', unsafe_allow_html=True)
    st.caption("Đánh giá có thể giải trình: mỗi nhận định đi kèm số liệu, căn cứ và đề xuất. Đây là bộ máy quy tắc phân tích, không tự kết luận có gian lận hoặc sai phạm.")
    if detail.empty:
        st.warning("Chưa có giao dịch xe khách hàng được nhận diện. Xem tab 'Xe khách hàng' để kiểm tra phân bố giá trị hình thức vận chuyển.")
    else:
        status = detail["Kết quả đối chiếu"].fillna("")
        fit = int(status.eq("Phù hợp danh mục kho").sum())
        exception = int(status.str.startswith(("Ngoài", "Mâu thuẫn")).sum())
        incomplete = len(detail) - fit - exception
        fit_rate = fit / (fit + exception) * 100 if (fit + exception) else 0
        affected = int(customers["Số_ngoài_danh_mục"].gt(0).sum()) if not customers.empty else 0
        a, b, c, d = st.columns(4)
        a.metric("Chứng từ xe khách hàng", f"{len(detail):,}")
        b.metric("Phù hợp danh mục kho", f"{fit:,}", f"{fit_rate:.1f}% nhóm đã đối chiếu")
        c.metric("Ngoài danh mục / mâu thuẫn", f"{exception:,}")
        d.metric("NPP có ngoại lệ", f"{affected:,}")
        if exception:
            st.error(f"⚠️ Có {exception:,} chứng từ cần xác minh tại {affected:,} NPP. Đây là cảnh báo sàng lọc, chưa phải kết luận vi phạm.")
        elif incomplete:
            st.warning(f"⚠️ Chưa thấy ngoại lệ theo ma trận, nhưng còn {incomplete:,} chứng từ chưa đủ căn cứ.")
        else:
            st.success("✓ Chưa ghi nhận chênh lệch theo ma trận kho hiện tại.")

    for _, row in findings.iterrows():
        level = str(row["Mức ưu tiên"])
        pill_class = "pill-high" if level == "Cao" else ("pill-watch" if level in {"Theo dõi", "Chưa đủ dữ liệu"} else "pill-low")
        icon = html.escape(str(row["Biểu tượng"]))
        heading = html.escape(str(row["Đầu mục đánh giá"]))
        result_text = html.escape(str(row["Kết quả"]))
        assessment = html.escape(str(row["Nhận định tự động"]))
        evidence = html.escape(str(row["Căn cứ"]))
        recommendation = html.escape(str(row["Đề xuất kiểm soát"]))
        safe_level = html.escape(level)
        st.markdown(
            f'''<div class="finding">
              <div class="finding-title">{icon} &nbsp; {heading}</div>
              <div class="finding-meta"><span class="pill {pill_class}">{safe_level}</span> &nbsp; {result_text}</div>
              <div class="finding-body"><b>Nhận định:</b> {assessment}<br/>
              <b>Căn cứ:</b> {evidence}<br/>
              <b>Đề xuất:</b> {recommendation}</div>
            </div>''',
            unsafe_allow_html=True,
        )

    if not detail.empty:
        chart = detail["Kết quả đối chiếu"].value_counts().rename_axis("Kết quả").reset_index(name="Số chứng từ")
        fig = px.bar(chart, x="Kết quả", y="Số chứng từ", color="Kết quả", text_auto=True, title="Phân bố kết quả đối chiếu kho")
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=55, b=10), plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.markdown('<div class="section-title">🔎 DANH SÁCH NPP CẦN ƯU TIÊN XÁC MINH</div>', unsafe_allow_html=True)
    if customers.empty:
        st.info("Chưa có dữ liệu NPP để tổng hợp.")
    else:
        priority = customers[
            customers["Số_ngoài_danh_mục"].gt(0) | customers["Số_chưa_đủ_dữ_liệu"].gt(0)
        ].sort_values(
            ["Số_ngoài_danh_mục", "Số_chưa_đủ_dữ_liệu", "Số_chứng_từ"],
            ascending=[False, False, False],
        )
        if priority.empty:
            st.success("Chưa phát hiện NPP có ngoại lệ hoặc thiếu dữ liệu theo các tiêu chí hiện tại.")
        else:
            st.caption(f"{len(priority):,} NPP cần xem xét. Bảng hiển thị tối đa 1.500 dòng để tránh treo trình duyệt; báo cáo Excel vẫn xuất đầy đủ.")
            st.dataframe(priority.head(1500), use_container_width=True, hide_index=True)
            selected_customer = st.selectbox(
                "Chọn NPP để xem chứng từ làm căn cứ",
                priority.apply(lambda r: f"{r['Mã khách hàng']} · {r['Tên khách hàng']}", axis=1).tolist(),
            )
            selected_key = selected_customer.split(" · ", 1)[0]
            customer_detail = detail[detail["Mã khách hàng"].astype(str).eq(selected_key)]
            st.dataframe(customer_detail.head(1500), use_container_width=True, hide_index=True)

with tabs[2]:
    st.markdown('<div class="section-title">🏭 ĐỐI CHIẾU ĐỊA CHỈ NPP VỚI MA TRẬN KHO</div>', unsafe_allow_html=True)
    if detail.empty:
        st.info("Không có giao dịch xe khách hàng để đối chiếu.")
    else:
        statuses = ["Tất cả"] + sorted(detail["Kết quả đối chiếu"].dropna().unique().tolist())
        chosen_status = st.selectbox("Lọc kết quả đối chiếu", statuses, key="filter_warehouse_status")
        view = detail if chosen_status == "Tất cả" else detail[detail["Kết quả đối chiếu"].eq(chosen_status)]
        st.caption(f"{len(view):,} chứng từ trong kết quả lọc. Hiển thị tối đa 2.000 dòng; tải Excel để xem toàn bộ.")
        st.dataframe(view.head(2000), use_container_width=True, hide_index=True)
        st.markdown("**Tổng hợp theo tỉnh/thành, kho và kết quả**")
        st.dataframe(province_summary, use_container_width=True, hide_index=True)

with tabs[3]:
    st.markdown('<div class="section-title">🚚 PHÂN TÍCH HÌNH THỨC XE KHÁCH HÀNG</div>', unsafe_allow_html=True)
    st.caption("Chỉ xe khách hàng được đối chiếu ma trận kho ở giai đoạn này. Xe nhà máy và xe nhà máy thuê ngoài có khu vực riêng, đang chờ dữ liệu biển số.")
    method_col = result["columns"]["method"]
    st.markdown("**Phân bố giá trị gốc của cột hình thức vận chuyển trong phạm vi đã lọc**")
    st.dataframe(result["vehicle_type_summary"], use_container_width=True, hide_index=True)
    st.dataframe(result["method_values"], use_container_width=True, hide_index=True)
    if detail.empty:
        st.warning("Chưa nhận diện được dòng nào là Xe khách hàng. Đối chiếu chính xác nhãn đang có trong bảng trên; nếu nhãn khác, cần bổ sung quy tắc nhận diện.")
    else:
        plates = detail["Biển số xe"].fillna("").astype(str).str.strip()
        has_plate = plates.ne("") & ~plates.str.lower().isin(["nan", "none", "null"])
        plate_data = detail.loc[has_plate].copy()
        plate_data["_bien_so_chuan"] = plates[has_plate].str.upper().str.replace(r"[^A-Z0-9]", "", regex=True).values
        shared = (
            plate_data.groupby("_bien_so_chuan")["Mã khách hàng"].nunique()
            .loc[lambda s: s.gt(1)].sort_values(ascending=False)
        ) if not plate_data.empty else pd.Series(dtype="int64")
        x, y, z = st.columns(3)
        x.metric("Biển số nhận diện", f"{plate_data['_bien_so_chuan'].nunique() if not plate_data.empty else 0:,}")
        y.metric("Biển số có nhiều NPP", f"{len(shared):,}")
        z.metric("Chứng từ thiếu biển số", f"{int((~has_plate).sum()):,}")
        if not shared.empty:
            st.markdown("**Biển số xuất hiện tại nhiều NPP**")
            st.dataframe(shared.rename("Số NPP").reset_index().rename(columns={"_bien_so_chuan": "Biển số"}), use_container_width=True, hide_index=True)
        st.caption("Biển số dùng chung cần kiểm tra thêm thời gian lấy hàng, tài xế, người nhận và lộ trình; không tự động kết luận vi phạm.")

with tabs[4]:
    st.markdown('<div class="section-title">🏢 XE NHÀ MÁY · KHU VỰC CHỜ BỔ SUNG DỮ LIỆU</div>', unsafe_allow_html=True)
    factory = result["factory_vehicle_source"]
    st.caption("Nhóm này được tách riêng, chưa chấm điểm tính hợp lý kho hoặc xe cho đến khi có danh mục biển số và quy tắc kiểm soát.")
    f1, f2, f3 = st.columns(3)
    f1.metric("Dòng xe nhà máy", f"{len(factory):,}")
    f2.metric("Số chứng từ", f"{factory[result['columns']['document']].nunique():,}" if not factory.empty else "0")
    plate_col = find_col(factory, ["Số xe", "Biển số xe", "Biển kiểm soát"]) if not factory.empty else None
    f3.metric("Có biển số", f"{factory[plate_col].fillna('').astype(str).str.strip().ne('').sum():,}" if plate_col else "0")
    if factory.empty:
        st.info("Không có giao dịch xe nhà máy trong phạm vi lọc hiện tại.")
    else:
        st.dataframe(factory.head(1500), use_container_width=True, hide_index=True)
        st.caption("Khi cập nhật biển số, cần bổ sung danh mục xe nhà máy, đơn vị quản lý, lệnh điều xe và thời gian lấy hàng để hệ thống đối chiếu.")

with tabs[5]:
    st.markdown('<div class="section-title">🚛 XE NHÀ MÁY THUÊ NGOÀI · KHU VỰC CHỜ BỔ SUNG DỮ LIỆU</div>', unsafe_allow_html=True)
    outsourced = result["outsourced_vehicle_source"]
    st.caption("Tách riêng khỏi xe nhà máy và xe khách hàng. Chưa đánh giá nhà vận tải/biển số/chi phí cho đến khi có dữ liệu.")
    o1, o2, o3 = st.columns(3)
    o1.metric("Dòng xe thuê ngoài", f"{len(outsourced):,}")
    o2.metric("Số chứng từ", f"{outsourced[result['columns']['document']].nunique():,}" if not outsourced.empty else "0")
    plate_col = find_col(outsourced, ["Số xe", "Biển số xe", "Biển kiểm soát"]) if not outsourced.empty else None
    o3.metric("Có biển số", f"{outsourced[plate_col].fillna('').astype(str).str.strip().ne('').sum():,}" if plate_col else "0")
    if outsourced.empty:
        st.info("Không có giao dịch xe nhà máy thuê ngoài trong phạm vi lọc hiện tại.")
    else:
        st.dataframe(outsourced.head(1500), use_container_width=True, hide_index=True)
        st.caption("Khi cập nhật dữ liệu, bổ sung biển số, nhà vận tải, hợp đồng/đơn thuê xe, lệnh điều xe, phiếu xuất kho và chứng từ chi phí.")

with tabs[6]:
    st.markdown('<div class="section-title">🧹 NHẬT KÝ LỌC, CHẤT LƯỢNG VÀ PHƯƠNG PHÁP</div>', unsafe_allow_html=True)
    st.write(f"**File:** {uploaded.name} · **Sheet giao dịch:** {result['sheet']} · **Sheet ma trận:** {result['matrix_sheet']}")
    st.write(f"**Dòng nguồn:** {len(raw):,} · **Dòng giữ:** {len(scoped):,} · **Dòng loại:** {len(excluded):,}")
    if not excluded.empty:
        doc_col = result["columns"]["document"]
        type_col = result["columns"]["order_type"]
        excluded_cols = [c for c in [doc_col, type_col, "_loai_don_hang_chuan_hoa", "_ly_do_ngoai_pham_vi"] if c in excluded.columns]
        st.caption(f"{len(excluded):,} dòng bị loại. Hiển thị tối đa 1.500 dòng; danh sách đầy đủ nằm trong file Excel tải xuống.")
        st.dataframe(excluded[excluded_cols].head(1500), use_container_width=True, hide_index=True)
    st.markdown("**Phương pháp**")
    st.markdown(
        "- Loại chứng từ PN trước, bất kể loại đơn hàng.\n"
        "- Chuẩn hóa tiền tố ERP HBMC và dấu phân cách.\n"
        "- Chỉ giữ đúng bốn loại đơn hàng đã duyệt.\n"
        "- Chỉ chấm điểm Xe khách hàng; hai nhóm xe nhà máy chưa chấm điểm.\n"
        "- Đối chiếu địa chỉ NPP với mã kho trong sheet kho lấy hàng.\n"
        "- Gộp các dòng hàng cùng khách hàng + số chứng từ thành một sự kiện.\n"
        "- Ngoại lệ, mâu thuẫn và thiếu dữ liệu là các nhóm riêng biệt."
    )

output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    findings.to_excel(writer, sheet_name="AI_Danh_gia", index=False)
    if not customers.empty:
        customers.to_excel(writer, sheet_name="Tong_hop_NPP", index=False)
    if not province_summary.empty:
        province_summary.to_excel(writer, sheet_name="Tong_hop_tinh_kho", index=False)
    if not detail.empty:
        detail.to_excel(writer, sheet_name="Chi_tiet_xe_khach_hang", index=False)
    excluded.to_excel(writer, sheet_name="Nhat_ky_bi_loai", index=False)
    result["method_values"].to_excel(writer, sheet_name="Thong_ke_hinh_thuc", index=False)
    result["vehicle_type_summary"].to_excel(writer, sheet_name="Thong_ke_nhom_xe", index=False)
    result["factory_vehicle_source"].to_excel(writer, sheet_name="Xe_nha_may_cho_du_lieu", index=False)
    result["outsourced_vehicle_source"].to_excel(writer, sheet_name="Xe_thue_ngoai_cho_du_lieu", index=False)

st.download_button(
    "⬇️ Tải báo cáo phân tích và nhận định tự động",
    data=output.getvalue(),
    file_name="Bao_cao_AI_kho_lay_hang.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
