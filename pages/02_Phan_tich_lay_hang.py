from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from modules.pickup_analysis import analyze_customer_pickups, norm
from modules.scope_filter import apply_business_scope_filter

st.set_page_config(page_title="Phân tích kho lấy hàng", page_icon="📦", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Be Vietnam Pro',sans-serif;}
[data-testid="stAppViewContainer"] {background:#f6f8fc;color:#172b4d;}
section[data-testid="stSidebar"] {background:#f0f4f9;border-right:1px solid #dce4ef;}
.block-container {max-width:1500px;padding-top:1.2rem;padding-bottom:2rem;}
.page-kicker {font-size:.72rem;font-weight:800;letter-spacing:.12em;color:#64748b;}
.page-title {font-size:1.8rem;font-weight:800;color:#17324d;margin:.15rem 0 .15rem;}
.page-subtitle {color:#64748b;font-size:.92rem;margin-bottom:1.1rem;}
.section-head {font-size:1.08rem;font-weight:800;color:#244c70;margin:.4rem 0 .7rem;}
div[data-testid="stMetric"] {background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px;}
div[data-testid="stDataFrame"] {border:1px solid #e2e8f0;border-radius:10px;}
div[data-testid="stTabs"] button {font-weight:650;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-kicker">HOA SEN GROUP · KIỂM SOÁT KINH DOANH</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Phân tích hoạt động lấy hàng của nhà phân phối</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Lọc đúng phạm vi chứng từ, đối chiếu kho theo địa chỉ NPP, đánh giá xe khách hàng và tự động lập nhận định có căn cứ.</div>', unsafe_allow_html=True)

READ_COLUMNS = {norm(x) for x in [
    "Số chứng từ", "Loại đơn hàng", "Ngày chứng từ", "Mã khách hàng",
    "Tên khách hàng", "Loại khách hàng", "Địa chỉ", "Mã kho2", "Mã kho",
    "Kho lấy hàng", "Shipping method", "Số xe", "Ghi chú2",
    "Thành tiền bán", "Số lượng", "Khối lượng", "Mã hàng", "Tên hàng",
    "Miền2", "NPP/Dự án",
]}


def find_col(frame: pd.DataFrame, aliases: list[str]) -> str | None:
    lookup = {norm(c): c for c in frame.columns}
    for alias in aliases:
        if norm(alias) in lookup:
            return lookup[norm(alias)]
    return None


@st.cache_data(show_spinner="Đang đọc và phân tích workbook...", max_entries=3)
def process_workbook(file_bytes: bytes):
    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    sheet_lookup = {norm(s): s for s in xls.sheet_names}
    tx_sheet = sheet_lookup.get("om 055")
    matrix_sheet = sheet_lookup.get("kho lay hang")
    if not tx_sheet or not matrix_sheet:
        raise ValueError("Không tìm thấy đủ sheet 'om-055' và 'kho lấy hàng'. Các sheet hiện có: " + ", ".join(xls.sheet_names))

    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=tx_sheet, engine="openpyxl", usecols=lambda c: norm(c) in READ_COLUMNS)
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

    required = {"Số chứng từ": document_col, "Loại đơn hàng": order_type_col, "Địa chỉ": address_col,
                "Hình thức vận chuyển": method_col, "Mã kho/Mã kho2": warehouse_code_col}
    missing = [label for label, col in required.items() if not col]
    if missing:
        raise ValueError("Thiếu cột bắt buộc trong OM-055: " + ", ".join(missing))

    raw["_dong_nguon_excel"] = np.arange(len(raw)) + 2
    scoped, excluded = apply_business_scope_filter(raw, document_col=document_col, order_type_col=order_type_col)
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
        detail["Dòng Excel nguồn"] = detail["_source_index"].map(scoped["_dong_nguon_excel"])
    return {"sheet": tx_sheet, "raw": raw, "scoped": scoped, "excluded": excluded,
            "detail": detail, "customer_summary": customer_summary,
            "province_summary": province_summary,
            "columns": {"document": document_col, "order_type": order_type_col}}


def build_ai_findings(result: dict) -> pd.DataFrame:
    detail, scoped, summary, excluded, raw = (
        result["detail"], result["scoped"], result["customer_summary"],
        result["excluded"], result["raw"]
    )
    pn_count = int(excluded["_ly_do_ngoai_pham_vi"].str.startswith("Số chứng từ bắt đầu bằng PN").sum())
    other_excluded = len(excluded) - pn_count
    findings = [{
        "Đầu mục": "1. Phạm vi dữ liệu",
        "Kết quả": f"{len(scoped):,}/{len(raw):,} dòng được giữ lại",
        "Nhận định": f"Đã loại {pn_count:,} chứng từ PN và {other_excluded:,} dòng có loại đơn hàng ngoài bốn nhóm được duyệt.",
        "Mức ưu tiên": "Kiểm soát phạm vi",
        "Đề xuất": "Kiểm tra nhật ký loại trừ trước khi phát hành báo cáo; các dòng PN không tham gia đánh giá.",
    }]
    if detail.empty:
        findings.append({
            "Đầu mục": "2. Kho lấy hàng và xe khách hàng",
            "Kết quả": "Không có giao dịch xe khách hàng đủ điều kiện",
            "Nhận định": "Không đủ dữ liệu để đánh giá tính hợp lý kho trong phạm vi đã lọc.",
            "Mức ưu tiên": "Chưa đủ dữ liệu",
            "Đề xuất": "Kiểm tra nhãn Shipping method và các điều kiện lọc chứng từ.",
        })
        return pd.DataFrame(findings)

    total = len(detail)
    fit = int(detail["Kết quả đối chiếu"].eq("Phù hợp danh mục kho").sum())
    exception = int(detail["Kết quả đối chiếu"].str.startswith(("Ngoài", "Mâu thuẫn")).sum())
    incomplete = total - fit - exception
    rate = fit / (fit + exception) * 100 if fit + exception else np.nan
    flagged = int(summary["Số_ngoài_danh_mục"].gt(0).sum()) if not summary.empty else 0
    findings.append({
        "Đầu mục": "2. Tính hợp lý kho lấy hàng",
        "Kết quả": f"{fit:,}/{total:,} chứng từ phù hợp" + (f" ({rate:.1f}%)" if pd.notna(rate) else ""),
        "Nhận định": f"{exception:,} chứng từ ngoài danh mục/mâu thuẫn; {incomplete:,} chứng từ chưa đủ dữ liệu; {flagged:,} khách hàng có ít nhất một ngoại lệ.",
        "Mức ưu tiên": "Cao" if exception >= 10 or exception / max(total, 1) >= .10 else ("Theo dõi" if exception else ("Bổ sung dữ liệu" if incomplete else "Thấp")),
        "Đề xuất": "Đối chiếu địa chỉ NPP, mã kho được phép, phiếu xuất kho, tồn kho, điều phối vận tải và phê duyệt ngoại lệ. Không kết luận sai phạm chỉ từ ma trận.",
    })
    top = summary.sort_values(["Số_ngoài_danh_mục", "Số_chứng_từ"], ascending=[False, False]).head(5)
    top_text = "; ".join(
        f"{r['Tên khách hàng'] or r['Mã khách hàng']}: {int(r['Số_ngoài_danh_mục'])} chứng từ"
        for _, r in top.iterrows() if int(r["Số_ngoài_danh_mục"]) > 0
    )
    findings.append({
        "Đầu mục": "3. Khách hàng cần ưu tiên",
        "Kết quả": f"{flagged:,} khách hàng có ngoại lệ",
        "Nhận định": top_text or "Chưa có khách hàng ghi nhận chứng từ ngoài danh mục.",
        "Mức ưu tiên": "Cao" if flagged else "Thấp",
        "Đề xuất": "Chọn chứng từ mẫu, yêu cầu giải trình lý do chọn kho và cung cấp chứng từ điều phối/phê duyệt.",
    })
    plates = detail["Biển số xe"].fillna("").astype(str).str.strip()
    valid = plates.ne("") & ~plates.str.lower().isin(["nan", "none"])
    plate_group = detail.loc[valid].assign(_plate=plates[valid].values)
    shared = int((plate_group.groupby("_plate")["Mã khách hàng"].nunique() > 1).sum()) if not plate_group.empty else 0
    missing_plates = int((~valid).sum())
    findings.append({
        "Đầu mục": "4. Xe khách hàng",
        "Kết quả": f"{plates[valid].nunique():,} biển số; {shared:,} biển số xuất hiện ở nhiều NPP",
        "Nhận định": f"{missing_plates:,} chứng từ thiếu biển số. Xe dùng chung là dấu hiệu cần xác minh, không tự động là vi phạm.",
        "Mức ưu tiên": "Theo dõi" if shared or missing_plates else "Thấp",
        "Đề xuất": "Đối chiếu ngày/giờ lấy hàng, tài xế, người nhận, lộ trình và hồ sơ sử dụng xe.",
    })
    findings.append({
        "Đầu mục": "5. Doanh thu và sản lượng lấy hàng",
        "Kết quả": f"Doanh thu {detail['Doanh thu'].sum(min_count=1):,.0f}; số lượng {detail['Số lượng'].sum(min_count=1):,.0f}; khối lượng {detail['Khối lượng'].sum(min_count=1):,.2f}",
        "Nhận định": "Tổng hợp trên các sự kiện đã gộp theo khách hàng và số chứng từ, tránh đếm lặp hóa đơn nhiều dòng hàng.",
        "Mức ưu tiên": "Thông tin",
        "Đề xuất": "So sánh theo kỳ, NPP và mặt hàng để phát hiện biến động bất thường.",
    })
    findings.append({
        "Đầu mục": "6. Chất lượng dữ liệu",
        "Kết quả": f"{incomplete:,} chứng từ chưa đủ căn cứ",
        "Nhận định": "Dòng thiếu địa chỉ/mã kho được tách riêng, không mặc định là phù hợp hoặc rủi ro thấp.",
        "Mức ưu tiên": "Cao" if incomplete else "Thấp",
        "Đề xuất": "Bổ sung địa chỉ chuẩn, mã kho, biển số và hồ sơ chứng từ; theo dõi tỷ lệ hoàn thiện dữ liệu theo đơn vị kinh doanh.",
    })
    return pd.DataFrame(findings)


uploaded = st.file_uploader("Tải workbook Excel (.xlsx)", type=["xlsx"], help="Cần có sheet om-055 và kho lấy hàng.")
if uploaded is None:
    st.info("Tải file Excel để bắt đầu. File gốc không bị thay đổi.")
    st.stop()

try:
    result = process_workbook(uploaded.getvalue())
except Exception as exc:
    st.error(f"Không thể đọc hoặc phân tích workbook: {exc}")
    st.exception(exc)
    st.stop()

raw, scoped, excluded = result["raw"], result["scoped"], result["excluded"]
detail, customer_summary, province_summary = result["detail"], result["customer_summary"], result["province_summary"]
findings = build_ai_findings(result)
pn_count = int(excluded["_ly_do_ngoai_pham_vi"].str.startswith("Số chứng từ bắt đầu bằng PN").sum())
other_excluded = len(excluded) - pn_count

with st.container(border=True):
    st.markdown("#### PHẠM VI DỮ LIỆU")
    st.write("**Giữ:** Đơn hàng nội địa · Đơn hàng nội địa DLPP · Trả hàng hủy HĐ · Trả hàng không hủy HĐ")
    st.write("**Loại:** Chứng từ bắt đầu bằng PN và các loại đơn hàng khác.")
    a, b, c, d = st.columns(4)
    a.metric("Dòng OM-055", f"{len(raw):,}")
    b.metric("Dòng hợp lệ", f"{len(scoped):,}")
    c.metric("Chứng từ PN bị loại", f"{pn_count:,}")
    d.metric("Loại đơn hàng khác", f"{other_excluded:,}")

tabs = st.tabs(["Tổng quan & AI đánh giá", "NPP cần xác minh", "Chi tiết kho lấy hàng", "Xe khách hàng", "Nhật ký lọc"])

with tabs[0]:
    st.markdown('<div class="section-head">BẢN ĐÁNH GIÁ TỰ ĐỘNG</div>', unsafe_allow_html=True)
    if detail.empty:
        st.warning("Không có giao dịch xe khách hàng trong phạm vi đã lọc. Xem Nhật ký lọc để kiểm tra.")
    else:
        total = len(detail)
        fit = int(detail["Kết quả đối chiếu"].eq("Phù hợp danh mục kho").sum())
        exception = int(detail["Kết quả đối chiếu"].str.startswith(("Ngoài", "Mâu thuẫn")).sum())
        incomplete = total - fit - exception
        rate = fit / (fit + exception) * 100 if fit + exception else 0
        flagged = int(customer_summary["Số_ngoài_danh_mục"].gt(0).sum()) if not customer_summary.empty else 0
        a, b, c, d = st.columns(4)
        a.metric("Chứng từ xe khách hàng", f"{total:,}")
        b.metric("Phù hợp ma trận", f"{fit:,}", f"{rate:.1f}% trong nhóm đã đối chiếu")
        c.metric("Ngoài danh mục / mâu thuẫn", f"{exception:,}")
        d.metric("NPP cần xác minh", f"{flagged:,}")
        if exception:
            st.warning(f"Hệ thống ghi nhận {exception:,} chứng từ cần xác minh thuộc {flagged:,} NPP. Đây là cảnh báo sàng lọc, chưa phải kết luận sai phạm.")
        elif incomplete:
            st.info(f"Chưa ghi nhận chứng từ ngoài danh mục, nhưng còn {incomplete:,} chứng từ chưa đủ dữ liệu.")
        else:
            st.success("Chưa ghi nhận chênh lệch theo ma trận kho hiện tại.")
    st.markdown("#### Nhận định theo từng đầu mục")
    for _, row in findings.iterrows():
        with st.container(border=True):
            left, right = st.columns([1, 4])
            left.markdown(f"**{row['Đầu mục']}**")
            left.caption(str(row["Mức ưu tiên"]))
            right.markdown(f"**{row['Kết quả']}**")
            right.write(row["Nhận định"])
            right.caption("Đề xuất kiểm soát: " + row["Đề xuất"])
    if not detail.empty:
        chart = detail["Kết quả đối chiếu"].value_counts().rename_axis("Kết quả").reset_index(name="Số chứng từ")
        st.plotly_chart(px.bar(chart, x="Kết quả", y="Số chứng từ", text="Số chứng từ"), use_container_width=True)

with tabs[1]:
    st.markdown('<div class="section-head">NPP CẦN ƯU TIÊN XÁC MINH</div>', unsafe_allow_html=True)
    if customer_summary.empty:
        st.info("Chưa có dữ liệu tổng hợp NPP.")
    else:
        priority = customer_summary[customer_summary["Số_ngoài_danh_mục"].gt(0)].sort_values(["Số_ngoài_danh_mục", "Số_chứng_từ"], ascending=[False, False])
        if priority.empty:
            st.success("Chưa phát hiện NPP có chứng từ ngoài danh mục theo ma trận.")
        else:
            st.dataframe(priority, use_container_width=True, hide_index=True)
            names = priority["Tên khách hàng"].fillna("").astype(str).tolist()
            selected = st.selectbox("Chọn khách hàng xem chứng từ làm căn cứ", names)
            st.dataframe(detail[detail["Tên khách hàng"].fillna("").astype(str).eq(selected)], use_container_width=True, hide_index=True)

with tabs[2]:
    st.markdown('<div class="section-head">ĐỐI CHIẾU ĐỊA CHỈ NPP VỚI DANH MỤC KHO</div>', unsafe_allow_html=True)
    if detail.empty:
        st.info("Không có giao dịch xe khách hàng để đối chiếu.")
    else:
        statuses = ["Tất cả"] + sorted(detail["Kết quả đối chiếu"].dropna().unique().tolist())
        selected_status = st.selectbox("Lọc kết quả", statuses, key="warehouse_status_filter")
        view = detail if selected_status == "Tất cả" else detail[detail["Kết quả đối chiếu"].eq(selected_status)]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.markdown("#### Tổng hợp theo tỉnh/thành, kho và kết quả")
        st.dataframe(province_summary, use_container_width=True, hide_index=True)

with tabs[3]:
    st.markdown('<div class="section-head">PHÂN TÍCH HÌNH THỨC XE KHÁCH HÀNG</div>', unsafe_allow_html=True)
    st.caption("Xe nhà máy và xe nhà máy thuê ngoài chưa được chấm điểm.")
    if detail.empty:
        st.info("Không có giao dịch xe khách hàng.")
    else:
        plates = detail["Biển số xe"].fillna("").astype(str).str.strip()
        valid = plates.ne("") & ~plates.str.lower().isin(["nan", "none"])
        plate_data = detail.loc[valid].assign(_plate=plates[valid].values)
        shared = int((plate_data.groupby("_plate")["Mã khách hàng"].nunique() > 1).sum()) if not plate_data.empty else 0
        a, b, c = st.columns(3)
        a.metric("Biển số nhận diện", f"{plates[valid].nunique():,}")
        b.metric("Biển số xuất hiện ở nhiều NPP", f"{shared:,}")
        c.metric("Chứng từ thiếu biển số", f"{int((~valid).sum()):,}")
        if not plate_data.empty:
            plate_summary = plate_data.groupby("_plate").agg(
                Số_NPP=("Mã khách hàng", "nunique"),
                Danh_sách_NPP=("Tên khách hàng", lambda s: " | ".join(sorted(set(s.dropna().astype(str))))),
                Số_chứng_từ=("Số chứng từ", "nunique"),
            ).reset_index().rename(columns={"_plate": "Biển số"})
            st.dataframe(plate_summary.sort_values("Số_NPP", ascending=False), use_container_width=True, hide_index=True)
        st.caption("Xe dùng chung là tín hiệu cần đối chiếu ngày/giờ lấy hàng, tài xế, người nhận, lộ trình và hồ sơ sử dụng xe; không tự động kết luận vi phạm.")

with tabs[4]:
    st.markdown('<div class="section-head">NHẬT KÝ LỌC VÀ PHƯƠNG PHÁP</div>', unsafe_allow_html=True)
    st.write(f"**File:** {uploaded.name} · **Sheet:** {result['sheet']}")
    st.write(f"**Dòng nguồn:** {len(raw):,} · **Dòng giữ lại:** {len(scoped):,} · **Dòng bị loại:** {len(excluded):,}")
    if not excluded.empty:
        st.dataframe(excluded[[result["columns"]["document"], result["columns"]["order_type"], "_loai_don_hang_chuan_hoa", "_ly_do_ngoai_pham_vi"]], use_container_width=True, hide_index=True)
    st.markdown(
        "- Loại chứng từ PN trước, bất kể loại đơn hàng.\n"
        "- Bỏ tiền tố ERP HBMC và chuẩn hóa dấu phân cách trước khi nhận diện loại đơn hàng.\n"
        "- Chỉ giữ bốn loại đơn hàng đã duyệt.\n"
        "- Chỉ đánh giá kho với Xe khách hàng; xe nhà máy và xe nhà máy thuê ngoài được tách ra.\n"
        "- Gộp nhiều dòng hàng thành một sự kiện theo Mã khách hàng + Số chứng từ.\n"
        "- Ngoài danh mục, mâu thuẫn và thiếu dữ liệu là ba nhóm riêng; không tự kết luận vi phạm."
    )

if not detail.empty:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        findings.to_excel(writer, sheet_name="AI_Danh_gia", index=False)
        customer_summary.to_excel(writer, sheet_name="Tong_hop_NPP", index=False)
        province_summary.to_excel(writer, sheet_name="Tong_hop_tinh_kho", index=False)
        detail.to_excel(writer, sheet_name="Chi_tiet_xe_khach_hang", index=False)
        excluded.to_excel(writer, sheet_name="Nhat_ky_bi_loai", index=False)
    st.download_button("Tải báo cáo phân tích Excel", data=output.getvalue(),
        file_name="Bao_cao_AI_kho_lay_hang_xe_khach_hang.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
