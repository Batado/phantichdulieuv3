from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from modules.pickup_analysis import analyze_customer_pickups, norm
from modules.scope_filter import apply_business_scope_filter

st.set_page_config(
    page_title="Phân tích kho lấy hàng",
    page_icon="📦",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px;}
    .page-kicker {color:#64748b; font-size:.78rem; letter-spacing:.08em; font-weight:700;}
    .page-title {font-size:1.8rem; font-weight:800; color:#17324d; margin:.15rem 0 .2rem;}
    .page-subtitle {color:#64748b; margin-bottom:1.1rem;}
    div[data-testid="stMetric"] {background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="page-kicker">HOA SEN GROUP · KIỂM SOÁT KINH DOANH</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Phân tích tính hợp lý kho lấy hàng</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Đánh giá xe khách hàng theo địa chỉ NPP và ma trận kho được duyệt. '
    'Xe nhà máy và xe nhà máy thuê ngoài chưa được chấm điểm trong phiên bản này.</div>',
    unsafe_allow_html=True,
)

@st.cache_data(show_spinner="Đang đọc workbook Excel...", max_entries=3)
def read_workbook(file_bytes: bytes):
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    sheet_lookup = {norm(s): s for s in xls.sheet_names}
    transaction_sheet = sheet_lookup.get("om 055")
    matrix_sheet = sheet_lookup.get("kho lay hang")
    if not transaction_sheet or not matrix_sheet:
        raise ValueError(
            "Workbook phải có hai sheet 'om-055' và 'kho lấy hàng'. "
            f"Sheet hiện có: {', '.join(xls.sheet_names)}"
        )
    transactions = pd.read_excel(
        io.BytesIO(file_bytes), sheet_name=transaction_sheet, engine="openpyxl"
    )
    matrix = pd.read_excel(
        io.BytesIO(file_bytes), sheet_name=matrix_sheet, engine="openpyxl"
    )
    return transaction_sheet, transactions, matrix, xls.sheet_names


def find_col(frame: pd.DataFrame, aliases: list[str]) -> str | None:
    lookup = {norm(c): c for c in frame.columns}
    for alias in aliases:
        if norm(alias) in lookup:
            return lookup[norm(alias)]
    return None


@st.cache_data(show_spinner="Đang phân tích dữ liệu kho...", max_entries=3)
def analyze_cached(transactions, matrix, address_col, warehouse_code_col, document_col,
                   method_col, warehouse_name_col, plate_col):
    return analyze_customer_pickups(
        transactions,
        matrix,
        address_col=address_col,
        warehouse_code_col=warehouse_code_col,
        document_col=document_col,
        method_col=method_col,
        warehouse_name_col=warehouse_name_col,
        plate_col=plate_col,
    )


uploaded = st.file_uploader(
    "Tải workbook Excel (.xlsx)",
    type=["xlsx"],
    help="Cần có sheet om-055 và sheet kho lấy hàng.",
)
if uploaded is None:
    st.info("Tải workbook để bắt đầu. Dữ liệu gốc không bị chỉnh sửa.")
    st.stop()

try:
    file_bytes = uploaded.getvalue()
    transaction_sheet, transactions_raw, matrix, sheet_names = read_workbook(file_bytes)
    document_col = find_col(transactions_raw, ["Số chứng từ", "Số CT", "Số phiếu"])
    order_type_col = find_col(transactions_raw, ["Loại đơn hàng", "Loại giao dịch", "Transaction Type", "Order Type"])
    address_col = find_col(transactions_raw, ["Địa chỉ", "Địa chỉ khách hàng", "Địa chỉ KH"])
    method_col = find_col(transactions_raw, ["Shipping method", "Hình thức vận chuyển", "Phương thức vận chuyển"])
    warehouse_code_col = find_col(transactions_raw, ["Mã kho2", "Mã kho", "Mã kho xuất"])
    warehouse_name_col = find_col(transactions_raw, ["Kho lấy hàng", "Kho xuất", "Tên kho"])
    plate_col = find_col(transactions_raw, ["Số xe", "Biển số xe", "Biển kiểm soát"])
    required = {
        "Số chứng từ": document_col,
        "Loại đơn hàng": order_type_col,
        "Địa chỉ khách hàng": address_col,
        "Hình thức vận chuyển": method_col,
        "Mã kho thực tế": warehouse_code_col,
    }
    missing = [label for label, col in required.items() if not col]
    if missing:
        raise ValueError("Thiếu cột bắt buộc: " + ", ".join(missing))
    transactions, excluded = apply_business_scope_filter(
        transactions_raw,
        document_col=document_col,
        order_type_col=order_type_col,
    )
    detail, customer_summary, province_summary = analyze_cached(
        transactions,
        matrix,
        address_col,
        warehouse_code_col,
        document_col,
        method_col,
        warehouse_name_col or "Kho lấy hàng",
        plate_col or "Số xe",
    )
except Exception as exc:
    st.error(f"Không thể đọc hoặc phân tích workbook: {exc}")
    st.stop()

pn_excluded = int(excluded["_ly_do_ngoai_pham_vi"].str.startswith("Số chứng từ bắt đầu bằng PN").sum())
other_excluded = len(excluded) - pn_excluded
k1, k2, k3, k4 = st.columns(4)
k1.metric("Dòng nguồn OM-055", f"{len(transactions_raw):,}")
k2.metric("Trong phạm vi", f"{len(transactions):,}")
k3.metric("Loại chứng từ PN", f"{pn_excluded:,}")
k4.metric("Loại đơn hàng khác", f"{other_excluded:,}")

st.caption(
    "Phạm vi gồm: Đơn hàng nội địa, Đơn hàng nội địa DLPP, Trả hàng hủy HĐ, "
    "Trả hàng không hủy HĐ. Chứng từ bắt đầu bằng PN bị loại trước khi phân tích."
)

if detail.empty:
    st.warning("Không có giao dịch xe khách hàng đủ điều kiện sau khi lọc phạm vi.")
    with st.expander("Kiểm tra các dòng bị loại"):
        st.dataframe(excluded, use_container_width=True, hide_index=True)
    st.stop()

total = len(detail)
matched = int((detail["Kết quả đối chiếu"] == "Phù hợp danh mục kho").sum())
outside = int(detail["Kết quả đối chiếu"].str.startswith(("Ngoài", "Mâu thuẫn")).sum())
unknown = total - matched - outside
denom = matched + outside
fit_rate = matched / denom * 100 if denom else None

tabs = st.tabs(["Tổng quan đánh giá", "NPP cần xác minh", "Chi tiết chứng từ", "Nhật ký lọc & phương pháp"])

with tabs[0]:
    st.subheader("Kết quả sàng lọc xe khách hàng")
    a, b, c, d = st.columns(4)
    a.metric("Sự kiện/chứng từ", f"{total:,}")
    b.metric("Phù hợp ma trận", f"{matched:,}")
    c.metric("Ngoài danh mục / mâu thuẫn", f"{outside:,}")
    d.metric("Chưa đủ dữ liệu", f"{unknown:,}")
    if fit_rate is not None:
        st.metric("Tỷ lệ phù hợp trong nhóm có thể đối chiếu", f"{fit_rate:.1f}%")

    st.subheader("AI hỗ trợ tự đánh giá")
    st.caption(
        "Đây là đánh giá tự động theo quy tắc và dữ liệu định lượng trong workbook, "
        "không phải mô hình AI tự suy đoán hay kết luận vi phạm."
    )
    if outside:
        st.warning(
            f"Phát hiện {outside:,} sự kiện ngoài danh mục hoặc có mâu thuẫn. "
            "Ưu tiên kiểm tra địa chỉ NPP, mã kho, phiếu xuất kho, điều phối và phê duyệt ngoại lệ."
        )
    elif unknown:
        st.info(
            f"Có {unknown:,} sự kiện chưa đủ căn cứ. Cần bổ sung địa chỉ hoặc mã kho trước khi đánh giá."
        )
    else:
        st.success("Chưa ghi nhận sự kiện ngoài danh mục theo ma trận kho được cung cấp.")
    st.dataframe(province_summary, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("NPP cần ưu tiên xác minh")
    priority = customer_summary[customer_summary["Mức ưu tiên"] == "Cần xác minh"].copy()
    if priority.empty:
        st.success("Chưa có NPP có giao dịch ngoài danh mục theo ma trận hiện tại.")
    else:
        st.dataframe(
            priority.sort_values("Số_ngoài_danh_mục", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

with tabs[2]:
    st.subheader("Chi tiết chứng từ xe khách hàng")
    statuses = ["Tất cả"] + sorted(detail["Kết quả đối chiếu"].dropna().unique().tolist())
    selected_status = st.selectbox("Kết quả đối chiếu", statuses)
    view = detail if selected_status == "Tất cả" else detail[detail["Kết quả đối chiếu"] == selected_status]
    st.dataframe(view.drop(columns=["_source_index", "_event_key"], errors="ignore"), use_container_width=True, hide_index=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        customer_summary.to_excel(writer, sheet_name="Tong_hop_NPP", index=False)
        province_summary.to_excel(writer, sheet_name="Tong_hop_tinh_kho", index=False)
        detail.to_excel(writer, sheet_name="Chi_tiet_xe_khach_hang", index=False)
        excluded.to_excel(writer, sheet_name="Nhat_ky_dong_bi_loai", index=False)
    st.download_button(
        "Tải báo cáo phân tích Excel",
        data=output.getvalue(),
        file_name="Phan_tich_kho_lay_hang_xe_khach_hang.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with tabs[3]:
    st.subheader("Nhật ký lọc dữ liệu")
    st.write(f"Tên file: **{uploaded.name}** · Sheet giao dịch: **{transaction_sheet}**")
    st.write(f"Số sheet trong workbook: {len(sheet_names)} · Số dòng bị loại: {len(excluded):,}")
    if excluded.empty:
        st.success("Không có dòng bị loại.")
    else:
        st.dataframe(
            excluded[[document_col, order_type_col, "_ly_do_ngoai_pham_vi"]],
            use_container_width=True,
            hide_index=True,
        )
    st.subheader("Quy tắc đánh giá")
    st.markdown(
        "- Chỉ xét các chứng từ trong bốn loại đơn hàng được duyệt.\n"
        "- Loại mọi chứng từ có số bắt đầu bằng PN (hàng gửi kho).\n"
        "- Chỉ chấm tính hợp lý kho đối với hình thức Xe khách hàng.\n"
        "- Đối chiếu mã kho thực tế với sheet kho lấy hàng theo tỉnh/thành trong địa chỉ.\n"
        "- Xe nhà máy và xe nhà máy thuê ngoài được để ngoài phạm vi đánh giá ở phiên bản này.\n"
        "- Ngoài danh mục là tín hiệu cần xác minh, không tự động kết luận sai phạm."
    )
