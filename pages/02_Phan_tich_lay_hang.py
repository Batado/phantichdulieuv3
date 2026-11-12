import io

import pandas as pd
import streamlit as st

from modules.pickup_analysis import analyze_customer_pickups, norm

st.set_page_config(page_title="Phân tích lấy hàng xe khách hàng", page_icon="📦", layout="wide")
st.title("PHÂN TÍCH TÍNH HỢP LÝ KHO LẤY HÀNG")
st.caption(
    "Phiên bản 1 chỉ đánh giá giao dịch có hình thức Xe khách hàng. "
    "Xe nhà máy và xe nhà máy thuê ngoài được tách khỏi kết quả."
)

uploaded = st.file_uploader("Tải workbook Excel có sheet om-055 và kho lấy hàng", type=["xlsx"])
if uploaded is None:
    st.info("Tải file Excel để bắt đầu. Hệ thống cần cả dữ liệu giao dịch và ma trận kho hợp lý.")
    st.stop()

try:
    data = uploaded.getvalue()
    xls = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")
    sheet_lookup = {norm(s): s for s in xls.sheet_names}
    transaction_sheet = sheet_lookup.get("om 055")
    matrix_sheet = sheet_lookup.get("kho lay hang")
    if not transaction_sheet or not matrix_sheet:
        st.error("Không tìm thấy đủ hai sheet. Cần có 'om-055' và 'kho lấy hàng'.")
        st.write("Sheet đang có:", xls.sheet_names)
        st.stop()
    transactions = pd.read_excel(io.BytesIO(data), sheet_name=transaction_sheet, engine="openpyxl")
    matrix = pd.read_excel(io.BytesIO(data), sheet_name=matrix_sheet, engine="openpyxl")
    detail, customer_summary, province_summary = analyze_customer_pickups(transactions, matrix)
except Exception as exc:
    st.exception(exc)
    st.stop()

if detail.empty:
    st.warning("Không tìm thấy giao dịch Xe khách hàng hoặc không đọc được dữ liệu phù hợp.")
    st.stop()

total = len(detail)
matched = int((detail["Kết quả đối chiếu"] == "Phù hợp danh mục kho").sum())
outside = int(detail["Kết quả đối chiếu"].str.startswith(("Ngoài", "Mâu thuẫn")).sum())
unknown = total - matched - outside
c1, c2, c3, c4 = st.columns(4)
c1.metric("Giao dịch xe khách hàng", f"{total:,}")
c2.metric("Phù hợp danh mục", f"{matched:,}")
c3.metric("Ngoài danh mục", f"{outside:,}")
c4.metric("Chưa đủ dữ liệu", f"{unknown:,}")

denom = matched + outside
if denom:
    st.metric("Tỷ lệ phù hợp trong nhóm có thể đối chiếu", f"{matched / denom * 100:.1f}%")
st.caption(
    "Đây là kết quả sàng lọc theo ma trận kho trong workbook, không phải kết luận vi phạm. "
    "Các dòng ngoài danh mục cần kiểm tra phiếu xuất kho, điều phối, chứng từ điều chuyển "
    "và phê duyệt ngoại lệ."
)

st.subheader("1. NPP cần ưu tiên xác minh")
priority = customer_summary[customer_summary["Mức ưu tiên"] == "Cần xác minh"].copy()
if priority.empty:
    st.success("Chưa có NPP có giao dịch ngoài danh mục kho theo ma trận hiện tại.")
else:
    st.dataframe(priority.sort_values("Số_ngoài_danh_mục", ascending=False), use_container_width=True, hide_index=True)

st.subheader("2. Tổng hợp theo tỉnh/thành, kho và kết quả")
st.dataframe(province_summary, use_container_width=True, hide_index=True)

st.subheader("3. Chi tiết giao dịch xe khách hàng")
status_options = ["Tất cả"] + sorted(detail["Kết quả đối chiếu"].dropna().unique().tolist())
selected_status = st.selectbox("Lọc kết quả", status_options)
view = detail if selected_status == "Tất cả" else detail[detail["Kết quả đối chiếu"] == selected_status]
st.dataframe(view.drop(columns=["_source_index"]), use_container_width=True, hide_index=True)

output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    customer_summary.to_excel(writer, sheet_name="Tong_hop_NPP", index=False)
    province_summary.to_excel(writer, sheet_name="Tong_hop_tinh_kho", index=False)
    detail.to_excel(writer, sheet_name="Chi_tiet_xe_khach_hang", index=False)
st.download_button(
    "Tải báo cáo phân tích Excel",
    data=output.getvalue(),
    file_name="Phan_tich_kho_lay_hang_xe_khach_hang.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
