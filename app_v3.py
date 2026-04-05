import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Phân tích KH – Hoa Sen", layout="wide", page_icon="📊")

st.markdown("""
<style>
.risk-high   { background:#4a1010; border-left:4px solid #e74c3c; padding:10px 14px; border-radius:6px; margin:6px 0; color:#fff; }
.risk-medium { background:#3d2e10; border-left:4px solid #f39c12; padding:10px 14px; border-radius:6px; margin:6px 0; color:#fff; }
.risk-low    { background:#0f3020; border-left:4px solid #26c281; padding:10px 14px; border-radius:6px; margin:6px 0; color:#fff; }
.section-title { font-size:17px; font-weight:700; color:#e0e0e0; margin:20px 0 10px 0;
                 padding-bottom:6px; border-bottom:1px solid #2e3350; }
.info-box { background:#1a2035; border-radius:8px; padding:14px; margin:8px 0; color:#ccc; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════════
st.sidebar.markdown("## 📂 Upload dữ liệu")
uploaded_files = st.sidebar.file_uploader(
    "Upload file Excel báo cáo bán hàng",
    type=["xlsx"], accept_multiple_files=True
)

if not uploaded_files:
    st.markdown("## 👈 Upload file Excel để bắt đầu phân tích")
    st.info("Hỗ trợ định dạng báo cáo OM_RPT_055 (Hoa Sen). Header tự động nhận diện.")
    st.stop()

# ══════════════════════════════════════════════════════════════
#  HÀM TIỆN ÍCH
# ══════════════════════════════════════════════════════════════

# Tất cả tên cột có thể gặp → chuẩn hoá về 1 tên duy nhất
COL_ALIASES = {
    "Tên khách hàng": ["Tên khách hàng", "Tên KH", "Khách hàng", "Tên khách", "ten_kh", "customer_name"],
    "Ngày chứng từ":  ["Ngày chứng từ", "Ngày CT", "Ngày", "ngay_ct", "date"],
    "Số chứng từ":    ["Số chứng từ", "Số CT", "so_ct", "voucher_no"],
    "Tên hàng":       ["Tên hàng", "Tên mã hàng", "Tên SP", "product_name"],
    "Mã hàng":        ["Mã hàng", "Mã SP", "product_code"],
    "Khối lượng":     ["Khối lượng", "KL", "weight"],
    "Số lượng":       ["Số lượng", "SL", "qty", "quantity"],
    "Thành tiền bán": ["Thành tiền bán", "Doanh thu", "revenue", "amount"],
    "Thành tiền vốn": ["Thành tiền vốn", "Giá vốn hàng bán", "cost"],
    "Lợi nhuận":      ["Lợi nhuận", "Profit", "profit"],
    "Giá bán":        ["Giá bán", "Đơn giá", "unit_price"],
    "Giá vốn":        ["Giá vốn", "cost_price"],
    "Nơi giao hàng":  ["Nơi giao hàng", "Địa chỉ giao hàng", "delivery_address"],
    "Freight Terms":  ["Freight Terms", "Điều kiện giao hàng", "freight"],
    "Shipping method":["Shipping method", "Phương tiện", "shipping"],
    "Biển số xe":     ["Số xe", "Biển số xe", "Biển xe", "plate_no"],
    "Tài Xế":         ["Tài Xế", "Tài xế", "Driver", "driver"],
    "Tên ĐVVC":       ["Tên ĐVVC", "Đơn vị vận chuyển", "carrier"],
    "Ghi chú":        ["Ghi chú", "Note", "Ghi Chú", "notes"],
    "Khu vực":        ["Khu vực", "Region", "region"],
    "Mã nhóm hàng":   ["Mã nhóm hàng", "Nhóm hàng", "product_group"],
    "Đơn giá vận chuyển": ["Đơn giá vận chuyển", "Chi phí vận chuyển", "freight_cost"],
    "Đơn giá quy đổi":    ["Đơn giá quy đổi", "converted_price"],
}


def normalize_columns(df):
    """Đổi tên cột về chuẩn, dùng COL_ALIASES. Không raise lỗi nếu không tìm thấy."""
    rename_map = {}
    cols_lower = {c.strip().lower(): c for c in df.columns}
    for standard, aliases in COL_ALIASES.items():
        if standard in df.columns:
            continue  # đã đúng tên
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = standard
                break
            if alias.strip().lower() in cols_lower:
                rename_map[cols_lower[alias.strip().lower()]] = standard
                break
    df.rename(columns=rename_map, inplace=True)
    return df


def safe_col(df, col, default=0):
    """Trả về Series nếu cột tồn tại, ngược lại trả về Series zeros."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0)
    return pd.Series([default] * len(df), index=df.index)


def find_header_row(file_bytes):
    """Tìm dòng header. Trả về index dòng, hoặc 0 nếu không tìm thấy."""
    try:
        df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None,
                               engine="openpyxl", nrows=40)
    except Exception:
        return 0

    # Tất cả keyword có thể xuất hiện ở dòng header
    kws = ["khách hàng", "khach hang", "tên kh", "ten kh",
           "số chứng từ", "so chung tu", "mã khách", "ma khach",
           "ngày chứng từ", "ngay chung tu", "tên hàng", "ten hang"]

    for i in range(df_raw.shape[0]):
        row_vals = [
            "" if (isinstance(v, float) and pd.isna(v)) else str(v)
            for v in df_raw.iloc[i].tolist()
        ]
        row_text = " ".join(row_vals).lower()
        # Yêu cầu ít nhất 2 keyword khớp để tránh nhận nhầm dòng metadata
        matched = sum(1 for kw in kws if kw in row_text)
        if matched >= 2:
            return i
    return 0


# ══════════════════════════════════════════════════════════════
#  LOAD & PROCESS DATA
# ══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Đang xử lý dữ liệu…")
def load_all(file_data):
    """file_data: list of (name, bytes)"""
    frames = []
    errors = []

    for name, fb in file_data:
        try:
            hr = find_header_row(fb)
            df = pd.read_excel(io.BytesIO(fb), header=hr, engine="openpyxl")

            # Làm sạch tên cột: strip whitespace, bỏ ký tự xuống dòng
            df.columns = [str(c).strip().replace("\n", " ").replace("\r", "") for c in df.columns]

            # Bỏ các cột "Unnamed"
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

            # Bỏ dòng toàn NaN
            df.dropna(how="all", inplace=True)

            normalize_columns(df)
            df["Nguồn file"] = name
            frames.append(df)

        except Exception as e:
            errors.append(f"`{name}`: {e}")

    if errors:
        for err in errors:
            st.warning(f"⚠️ Lỗi đọc file {err}")

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # ── Cột bắt buộc: kiểm tra sau khi gộp ──
    if "Ngày chứng từ" not in df.columns:
        st.error("❌ Không tìm thấy cột 'Ngày chứng từ'. Kiểm tra lại file hoặc header.")
        return pd.DataFrame()
    if "Tên khách hàng" not in df.columns:
        st.error("❌ Không tìm thấy cột 'Tên khách hàng'. Kiểm tra lại file.")
        return pd.DataFrame()

    # ── Ngày ──
    df["Ngày chứng từ"] = pd.to_datetime(
        df["Ngày chứng từ"], dayfirst=True, errors="coerce"
    )
    # Bỏ dòng không parse được ngày (thường là dòng tổng cộng cuối file)
    df = df[df["Ngày chứng từ"].notna()].copy()

    df["Tháng"] = df["Ngày chứng từ"].dt.to_period("M").astype(str)
    df["Quý"]   = df["Ngày chứng từ"].dt.to_period("Q").astype(str)

    # ── Số ──
    num_cols = ["Thành tiền bán", "Thành tiền vốn", "Lợi nhuận",
                "Khối lượng", "Số lượng", "Giá bán", "Giá vốn",
                "Đơn giá vận chuyển", "Đơn giá quy đổi"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    # ── Loại giao dịch ──
    ghi_chu = df["Ghi chú"].astype(str).str.upper() if "Ghi chú" in df.columns else pd.Series([""] * len(df))
    df["Loại GD"] = "Xuất bán"
    df.loc[ghi_chu.str.contains(r"NHẬP TRẢ|TRẢ HÀNG", na=False, regex=True), "Loại GD"] = "Trả hàng"
    df.loc[ghi_chu.str.contains(r"BỔ SUNG|THAY THẾ", na=False, regex=True), "Loại GD"] = "Xuất bổ sung"

    # ── Nhóm sản phẩm ──
    ten = df["Tên hàng"].astype(str) if "Tên hàng" in df.columns else pd.Series([""] * len(df))
    df["Nhóm SP"] = "Khác"
    mapping = [
        ("Ống HDPE",         r"HDPE"),
        ("Ống PVC nước",     r"PVC.*(?:nước|nong dài|nong trơn|thoát)"),
        ("Ống PVC bơm cát",  r"PVC.*(?:cát|bơm cát)"),
        ("Ống PPR",          r"PPR"),
        ("Lõi PVC",          r"(?:Lơi|Lõi|lori)"),
        ("Phụ kiện & Keo",   r"(?:Nối|Co |Tê |Van |Keo |Măng sông|Bít đầu)"),
    ]
    for label, pattern in mapping:
        df.loc[ten.str.contains(pattern, case=False, regex=True, na=False), "Nhóm SP"] = label

    return df


# Build cache key (bytes content, not file object)
file_data = []
for uf in uploaded_files:
    raw = uf.read()
    file_data.append((uf.name, raw))

df_all = load_all(file_data)

if df_all.empty:
    st.error("Không có dữ liệu hợp lệ. Vui lòng kiểm tra file và thử lại.")
    st.stop()

# ══════════════════════════════════════════════════════════════
#  SIDEBAR FILTERS
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  SIDEBAR FILTERS
# ══════════════════════════════════════════════════════════════
st.sidebar.markdown("---")
st.sidebar.markdown("## 🔍 Bộ lọc")

# Bộ lọc Phòng Kinh Doanh (Mã nhóm KH)
if "Mã nhóm KH" in df_all.columns:
    phong_list = sorted(df_all["Mã nhóm KH"].dropna().astype(str).unique())
    phong_chon = st.sidebar.multiselect("🏢 Phòng Kinh Doanh (Mã nhóm KH)", phong_list, default=phong_list)
else:
    phong_chon = []

# Bộ lọc Khu vực
if "Khu vực" in df_all.columns:
    kv_list = sorted(df_all["Khu vực"].dropna().astype(str).unique())
    kv_chon = st.sidebar.multiselect("🌍 Khu vực", kv_list, default=kv_list)
else:
    kv_chon = []

# Bộ lọc Tên Khách Hàng
kh_list = sorted(df_all["Tên khách hàng"].dropna().astype(str).unique())
kh = st.sidebar.selectbox("👤 Khách hàng", kh_list)

# Bộ lọc Quý
quy_list = sorted(df_all["Quý"].dropna().unique())
quy_chon = st.sidebar.multiselect("📅 Quý", quy_list, default=quy_list)

# Áp dụng tất cả bộ lọc
df = df_all.copy()
if phong_chon:
    df = df[df["Mã nhóm KH"].astype(str).isin(phong_chon)]
if kv_chon:
    df = df[df["Khu vực"].astype(str).isin(kv_chon)]
df = df[(df["Tên khách hàng"].astype(str) == kh) & (df["Quý"].isin(quy_chon))].copy()

# Tạo df_ban cho các tab phân tích
df_ban = df[df["Loại GD"] == "Xuất bán"].copy()
if df_ban.empty:
    st.warning("Không có dữ liệu xuất bán cho bộ lọc đã chọn.")
    st.stop()

# ══════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📦 Thói quen & Sản phẩm",
    "📈 Doanh thu & Sản lượng",
    "💹 Lợi nhuận & Chính sách",
    "🚚 Giao hàng",
    "🔁 Tần suất mua hàng",
    "⚠️ Rủi ro & BCCN",
])

# ══════════════════════════════════════════════════════════════
#  TAB 1
# ══════════════════════════════════════════════════════════════
with tab1:
    if "Nhóm SP" not in df_ban.columns or df_ban.empty:
        st.warning("Không có dữ liệu Nhóm SP để phân tích.")
        st.stop()

    df_nhom = (df_ban.groupby("Nhóm SP")
               .agg(So_lan=("Nhóm SP", "count"),
                    KL_tan=("Khối lượng", lambda x: round(x.sum() / 1000, 2)),
                    DT=("Thành tiền bán", "sum"))
               .reset_index().sort_values("DT", ascending=False)) 
            
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(df_nhom, x="Nhóm SP", y="DT", color="Nhóm SP", text_auto=".3s",
                     title="Doanh thu theo nhóm SP",
                     labels={"DT": "Doanh thu (VNĐ)", "Nhóm SP": ""})
        fig.update_layout(showlegend=False, height=360)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.pie(df_nhom, names="Nhóm SP", values="So_lan",
                      title="Tỷ trọng số lần mua", hole=0.45)
        fig2.update_layout(height=360)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">🏆 Top 15 sản phẩm theo doanh thu</div>', unsafe_allow_html=True)
    df_top = (df_ban.groupby("Tên hàng")
              .agg(So_lan=("Tên hàng", "count"),
                   KL_tan=("Khối lượng", lambda x: round(x.sum() / 1000, 2)),
                   SL=("Số lượng", "sum"),
                   DT=("Thành tiền bán", "sum"))
              .reset_index().sort_values("DT", ascending=False).head(15))
    df_top_show = df_top.rename(columns={"Tên hàng": "Sản phẩm", "So_lan": "Số lần",
                                          "KL_tan": "KL (tấn)", "SL": "SL (cái)", "DT": "DT (VNĐ)"})
    df_top_show["DT (VNĐ)"] = df_top_show["DT (VNĐ)"].map("{:,.0f}".format)
    st.dataframe(df_top_show, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">🎯 Nhận định mục đích sử dụng</div>', unsafe_allow_html=True)
    nhom_set = set(df_nhom["Nhóm SP"].tolist())
    insight_map = {
        "Ống HDPE":        "🔵 **Ống HDPE** (đường kính lớn): dùng cho **dự án hạ tầng, cấp thoát nước công trình lớn**.",
        "Ống PVC nước":    "🟢 **Ống PVC cấp thoát nước**: dùng cho **xây dựng dân dụng, công nghiệp, nông nghiệp**.",
        "Ống PVC bơm cát": "🟡 **Ống PVC bơm cát**: phục vụ **thuỷ lợi, nông nghiệp, nuôi trồng thuỷ sản**.",
        "Ống PPR":         "🟠 **Ống PPR**: dùng cho **hệ thống nước nóng/lạnh nội thất, dân dụng**.",
        "Lõi PVC":         "⚪ **Lõi PVC**: KH có thể là **đại lý hoặc nhà sản xuất thứ cấp**, mua nguyên liệu.",
        "Phụ kiện & Keo":  "🔴 **Phụ kiện & Keo**: mua kèm → KH **tự thi công hoặc bán lại trọn gói**.",
    }
    found = False
    for k, v in insight_map.items():
        if k in nhom_set:
            st.markdown(f'<div class="risk-low">{v}</div>', unsafe_allow_html=True)
            found = True
    if not found:
        st.info("Không đủ dữ liệu để suy luận.")

# ══════════════════════════════════════════════════════════════
#  TAB 2
# ══════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">📈 Biến động doanh thu, KL (tấn) & số lượng theo tháng</div>', unsafe_allow_html=True)

    df_m = (df_ban.groupby("Tháng")
            .agg(DT=("Thành tiền bán", "sum"),
                 KL=("Khối lượng", lambda x: round(x.sum() / 1000, 3)),
                 SL=("Số lượng", "sum"),
                 So_CT=("Số chứng từ", "nunique") if "Số chứng từ" in df_ban.columns else ("Thành tiền bán", "count"))
            .reset_index().sort_values("Tháng"))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Doanh thu (VNĐ) & Khối lượng (tấn)",
                                        "Số lượng (cái) & Số chứng từ"),
                        vertical_spacing=0.14)
    fig.add_trace(go.Bar(x=df_m["Tháng"], y=df_m["DT"], name="Doanh thu",
                         marker_color="#4e79d4", opacity=0.85), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_m["Tháng"], y=df_m["KL"], name="KL (tấn)",
                             mode="lines+markers", line=dict(color="#f0a500", width=2),
                             yaxis="y2"), row=1, col=1)
    fig.add_trace(go.Bar(x=df_m["Tháng"], y=df_m["SL"], name="Số lượng",
                         marker_color="#26c281", opacity=0.85), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_m["Tháng"], y=df_m["So_CT"], name="Số CT",
                             mode="lines+markers", line=dict(color="#e74c3c", width=2)), row=2, col=1)
    fig.update_layout(height=520, legend=dict(orientation="h", y=-0.12))
    st.plotly_chart(fig, use_container_width=True)

    df_m_show = df_m.copy()
    df_m_show["DT"] = df_m_show["DT"].map("{:,.0f}".format)
    df_m_show.columns = ["Tháng", "Doanh thu (VNĐ)", "KL (tấn)", "SL (cái)", "Số CT"]
    st.dataframe(df_m_show, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">📊 Tổng hợp theo Quý</div>', unsafe_allow_html=True)
    df_q = (df_ban.groupby("Quý")
            .agg(DT=("Thành tiền bán", "sum"),
                 KL=("Khối lượng", lambda x: round(x.sum() / 1000, 2)),
                 LN=("Lợi nhuận", "sum"),
                 So_CT=("Số chứng từ", "nunique") if "Số chứng từ" in df_ban.columns else ("Thành tiền bán", "count"))
            .reset_index())
    df_q["Biên LN (%)"] = (df_q["LN"] / df_q["DT"].replace(0, float("nan")) * 100).round(1).fillna(0)
    df_q["DT"] = df_q["DT"].map("{:,.0f}".format)
    df_q["LN"] = df_q["LN"].map("{:,.0f}".format)
    df_q.columns = ["Quý", "Doanh thu (VNĐ)", "KL (tấn)", "Lợi nhuận (VNĐ)", "Số CT", "Biên LN (%)"]
    st.dataframe(df_q, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
#  TAB 3
# ══════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">💹 Biến động lợi nhuận & phát hiện chính sách</div>', unsafe_allow_html=True)

    df_ln = (df_ban.groupby("Tháng")
             .agg(DT=("Thành tiền bán", "sum"),
                  Von=("Thành tiền vốn", "sum"),
                  LN=("Lợi nhuận", "sum"))
             .reset_index().sort_values("Tháng"))
    df_ln["Biên (%)"] = (df_ln["LN"] / df_ln["DT"].replace(0, float("nan")) * 100).round(2).fillna(0)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Doanh thu / Vốn / Lợi nhuận (VNĐ)", "Biên lợi nhuận (%)"),
                        vertical_spacing=0.14)
    fig.add_trace(go.Bar(x=df_ln["Tháng"], y=df_ln["DT"],  name="Doanh thu",  marker_color="#4e79d4"), row=1, col=1)
    fig.add_trace(go.Bar(x=df_ln["Tháng"], y=df_ln["Von"], name="Giá vốn",    marker_color="#e05c5c"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ln["Tháng"], y=df_ln["LN"], name="LN",
                             mode="lines+markers", line=dict(color="#26c281", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ln["Tháng"], y=df_ln["Biên (%)"], name="Biên LN (%)",
                             mode="lines+markers+text",
                             text=[f"{v:.1f}%" for v in df_ln["Biên (%)"]],
                             textposition="top center",
                             line=dict(color="#f0a500", width=2)), row=2, col=1)
    fig.update_layout(height=520, barmode="group")
    st.plotly_chart(fig, use_container_width=True)

    # Phát hiện tháng bất thường
    if len(df_ln) >= 2:
        mean_b = df_ln["Biên (%)"].mean()
        std_b  = df_ln["Biên (%)"].std()
        anom   = df_ln[df_ln["Biên (%)"] < mean_b - max(std_b, 1)]
        st.markdown('<div class="section-title">🔍 Tháng nghi có chiết khấu / chính sách đặc biệt</div>', unsafe_allow_html=True)
        if not anom.empty:
            for _, r in anom.iterrows():
                st.markdown(
                    f'<div class="risk-medium">⚠️ Tháng <b>{r["Tháng"]}</b>: Biên LN = <b>{r["Biên (%)"]:.1f}%</b> '
                    f'(TB = {mean_b:.1f}%) → khả năng có chiết khấu, KM, hoặc giá đặc biệt</div>',
                    unsafe_allow_html=True)
        else:
            st.markdown('<div class="risk-low">✅ Không phát hiện tháng bất thường về biên lợi nhuận.</div>', unsafe_allow_html=True)

    # Hàng trả lại
    df_tra = df[df["Loại GD"] == "Trả hàng"]
    if not df_tra.empty:
        st.markdown('<div class="section-title">↩️ Đơn hàng trả lại</div>', unsafe_allow_html=True)
        show = [c for c in ["Số chứng từ", "Ngày chứng từ", "Tên hàng",
                             "Khối lượng", "Thành tiền bán", "Ghi chú"] if c in df_tra.columns]
        df_tra_s = df_tra[show].copy()
        if "Thành tiền bán" in df_tra_s.columns:
            df_tra_s["Thành tiền bán"] = df_tra_s["Thành tiền bán"].map("{:,.0f}".format)
        st.dataframe(df_tra_s, use_container_width=True, hide_index=True)
        st.error(f"Tổng giá trị trả hàng: **{abs(df_tra['Thành tiền bán'].sum()):,.0f} VNĐ**")

    with st.expander("📋 Chi tiết giá bán từng giao dịch"):
        show2 = [c for c in ["Số chứng từ", "Ngày chứng từ", "Tên hàng",
                              "Giá bán", "Đơn giá quy đổi", "Thành tiền bán",
                              "Lợi nhuận", "Ghi chú"] if c in df_ban.columns]
        st.dataframe(df_ban[show2].sort_values("Ngày chứng từ"), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
#  TAB 4
# ══════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">🚚 Hình thức & địa điểm giao hàng</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if "Freight Terms" in df_ban.columns:
            df_ft = df_ban["Freight Terms"].value_counts().reset_index()
            df_ft.columns = ["Hình thức", "Số lần"]
            fig_ft = px.pie(df_ft, names="Hình thức", values="Số lần",
                            title="Điều kiện giao hàng (Freight Terms)", hole=0.4)
            st.plotly_chart(fig_ft, use_container_width=True)
        else:
            st.info("Không có dữ liệu Freight Terms.")

    with c2:
        if "Shipping method" in df_ban.columns:
            df_sm = df_ban["Shipping method"].value_counts().reset_index()
            df_sm.columns = ["Phương tiện", "Số lần"]
            fig_sm = px.pie(df_sm, names="Phương tiện", values="Số lần",
                            title="Phương tiện vận chuyển", hole=0.4)
            st.plotly_chart(fig_sm, use_container_width=True)
        else:
            st.info("Không có dữ liệu Shipping method.")

    st.markdown('<div class="section-title">📍 Địa điểm giao hàng</div>', unsafe_allow_html=True)
    if "Nơi giao hàng" in df_ban.columns:
        df_noi = (df_ban.groupby("Nơi giao hàng")
                  .agg(So_lan=("Nơi giao hàng", "count"),
                       KL=("Khối lượng", lambda x: round(x.sum() / 1000, 2)),
                       DT=("Thành tiền bán", "sum"))
                  .reset_index().sort_values("DT", ascending=False))
        df_noi["DT"] = df_noi["DT"].map("{:,.0f}".format)
        df_noi.columns = ["Địa điểm", "Số lần", "KL (tấn)", "DT (VNĐ)"]
        st.dataframe(df_noi, use_container_width=True, hide_index=True)
    else:
        st.info("Không có dữ liệu Nơi giao hàng.")

    with st.expander("🚛 Danh sách xe & tài xế"):
        xe_cols = [c for c in ["Biển số xe", "Tài Xế", "Tên ĐVVC", "Shipping method",
                                "Ngày chứng từ", "Nơi giao hàng"] if c in df_ban.columns]
        if xe_cols:
            st.dataframe(df_ban[xe_cols].drop_duplicates().sort_values("Ngày chứng từ"),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Không có dữ liệu xe/tài xế.")

# ══════════════════════════════════════════════════════════════
#  TAB 5
# ══════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-title">🔁 Tần suất mua hàng – Heatmap mã hàng × Tháng</div>', unsafe_allow_html=True)

    if "Tên hàng" in df_ban.columns:
        df_freq = (df_ban.groupby(["Tên hàng", "Tháng"])
                   .size().reset_index(name="Số lần"))
        df_piv = df_freq.pivot(index="Tên hàng", columns="Tháng", values="Số lần").fillna(0)
        top_items = df_piv.sum(axis=1).nlargest(min(20, len(df_piv))).index
        df_piv_top = df_piv.loc[top_items]

        if not df_piv_top.empty:
            fig_h = px.imshow(df_piv_top,
                              labels=dict(x="Tháng", y="Sản phẩm", color="Số lần"),
                              title="Top sản phẩm mua nhiều nhất × Tháng",
                              color_continuous_scale="Blues", aspect="auto")
            fig_h.update_layout(height=max(380, len(top_items) * 24))
            st.plotly_chart(fig_h, use_container_width=True)

        st.markdown('<div class="section-title">📋 Chi tiết theo Quý (ghi rõ từng tháng)</div>', unsafe_allow_html=True)
        for quy_val in sorted(df_ban["Quý"].dropna().unique()):
            df_q = df_ban[df_ban["Quý"] == quy_val]
            st.markdown(f"**📅 {quy_val}**")
            agg_q = (df_q.groupby(["Tên hàng", "Tháng"])
                     .agg(So_lan=("Tên hàng", "count"),
                          KL=("Khối lượng", lambda x: round(x.sum() / 1000, 2)),
                          DT=("Thành tiền bán", "sum"))
                     .reset_index().sort_values("DT", ascending=False))
            agg_q["DT"] = agg_q["DT"].map("{:,.0f}".format)
            agg_q.columns = ["Sản phẩm", "Tháng", "Số lần", "KL (tấn)", "DT (VNĐ)"]
            st.dataframe(agg_q, use_container_width=True, hide_index=True)
    else:
        st.info("Không có dữ liệu cột Tên hàng.")

# ══════════════════════════════════════════════════════════════
#  TAB 6 – RỦI RO & BCCN
# ══════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-title">📄 BCCN – Phân tích thanh toán & công nợ</div>', unsafe_allow_html=True)

    ghi_chu_s = df["Ghi chú"].astype(str).str.upper() if "Ghi chú" in df.columns else pd.Series([""] * len(df))
    df_po   = df[ghi_chu_s.str.contains(r"PO|B[0-9]{3}|HỢP ĐỒNG", na=False, regex=True)]
    df_tra2 = df[df["Loại GD"] == "Trả hàng"]
    df_bs   = df[df["Loại GD"] == "Xuất bổ sung"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Đơn có PO/HĐ", df_po["Số chứng từ"].nunique() if "Số chứng từ" in df_po.columns else len(df_po))
    c2.metric("↩️ Phiếu trả hàng", df_tra2["Số chứng từ"].nunique() if "Số chứng từ" in df_tra2.columns else len(df_tra2))
    c3.metric("🔄 Xuất bổ sung", df_bs["Số chứng từ"].nunique() if "Số chứng từ" in df_bs.columns else len(df_bs))
    c4.metric("💰 GT trả hàng (VNĐ)", f"{abs(df_tra2['Thành tiền bán'].sum()):,.0f}")

    st.markdown("""
    <div class="info-box">
    <b>⚠️ File OM_RPT_055 không có ngày thanh toán thực tế.</b><br>
    Để phân tích BCCN đầy đủ, cần bổ sung:<br>
    &nbsp;&nbsp;• <b>Sổ công nợ phải thu (AR Aging)</b> → tính số ngày tồn đọng, hạn mức tín dụng<br>
    &nbsp;&nbsp;• <b>Lịch sử thanh toán</b> → xác định thói quen TT (NET 30/60/90 ngày)<br><br>
    <b>Dấu hiệu nhận biết từ dữ liệu hiện có:</b><br>
    &nbsp;&nbsp;• Ghi chú <b>B-xxx / PO</b> → đơn theo dự án → thường thanh toán chậm (NET 30–90)<br>
    &nbsp;&nbsp;• Đơn <b>trả hàng</b> → tranh chấp chất lượng → kéo dài công nợ<br>
    &nbsp;&nbsp;• Nhiều địa điểm giao hàng → nhà thầu nhiều dự án → rủi ro phân tán công nợ
    </div>
    """, unsafe_allow_html=True)

    if not df_po.empty:
        with st.expander(f"📋 {len(df_po)} đơn có PO / mã dự án"):
            show_po = [c for c in ["Số chứng từ", "Ngày chứng từ", "Tên hàng",
                                    "Thành tiền bán", "Ghi chú"] if c in df_po.columns]
            df_po_s = df_po[show_po].drop_duplicates().copy()
            if "Thành tiền bán" in df_po_s.columns:
                df_po_s["Thành tiền bán"] = df_po_s["Thành tiền bán"].map("{:,.0f}".format)
            st.dataframe(df_po_s, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">⚠️ Đánh giá rủi ro tổng hợp</div>', unsafe_allow_html=True)

    risks = []
    score = 0

    # 1. Trả hàng
    tong_ban = df_ban["Thành tiền bán"].sum()
    tong_tra = abs(df_tra2["Thành tiền bán"].sum())
    tl_tra = (tong_tra / tong_ban * 100) if tong_ban > 0 else 0
    if tl_tra > 10:
        score += 30
        risks.append(("high",   f"↩️ Tỷ lệ hàng trả: <b>{tl_tra:.1f}%</b> ({tong_tra:,.0f} VNĐ) — rủi ro tranh chấp/chất lượng cao"))
    elif tl_tra > 3:
        score += 15
        risks.append(("medium", f"↩️ Tỷ lệ hàng trả: <b>{tl_tra:.1f}%</b> — cần theo dõi"))
    else:
        risks.append(("low",    f"✅ Tỷ lệ trả hàng thấp: {tl_tra:.1f}%"))

    # 2. Biên LN
    tong_ln = df_ban["Lợi nhuận"].sum()
    bien = (tong_ln / tong_ban * 100) if tong_ban > 0 else 0
    if bien < 5:
        score += 25
        risks.append(("high",   f"💹 Biên LN rất thấp: <b>{bien:.1f}%</b> — bán dưới giá hoặc chiết khấu lớn"))
    elif bien < 15:
        score += 10
        risks.append(("medium", f"💹 Biên LN ở mức thấp: <b>{bien:.1f}%</b>"))
    else:
        risks.append(("low",    f"✅ Biên LN bình thường: {bien:.1f}%"))

    # 3. Xuất bổ sung
    if not df_bs.empty:
        score += 15
        risks.append(("medium", f"🔄 Có <b>{len(df_bs)}</b> dòng xuất bổ sung/thay thế — giao nhầm, giao thiếu hoặc tranh chấp"))

    # 4. Đơn hàng outlier
    q75 = df_ban["Thành tiền bán"].quantile(0.75)
    q25 = df_ban["Thành tiền bán"].quantile(0.25)
    iqr = q75 - q25
    outliers = df_ban[df_ban["Thành tiền bán"] > q75 + 3 * iqr] if iqr > 0 else pd.DataFrame()
    if not outliers.empty:
        score += 10
        risks.append(("medium", f"📦 Có <b>{len(outliers)}</b> đơn hàng giá trị rất lớn — kiểm soát hạn mức tín dụng"))
    else:
        risks.append(("low",    "✅ Không có đơn hàng giá trị bất thường."))

    # 5. Địa điểm giao hàng phân tán
    if "Nơi giao hàng" in df_ban.columns:
        n_noi = df_ban["Nơi giao hàng"].nunique()
        if n_noi >= 5:
            score += 10
            risks.append(("medium", f"📍 Giao hàng tới <b>{n_noi}</b> địa điểm — nhà thầu nhiều dự án, rủi ro công nợ phân tán"))
        else:
            risks.append(("low",    f"✅ Số địa điểm giao hàng: {n_noi} (bình thường)"))

    # 6. Tần suất mua
    n_thang_mua = df_ban["Tháng"].nunique()
    delta_days  = (df_ban["Ngày chứng từ"].max() - df_ban["Ngày chứng từ"].min()).days
    n_thang_khoang = max(delta_days // 30, 1)
    ty_active = n_thang_mua / n_thang_khoang
    if ty_active < 0.5:
        score += 10
        risks.append(("medium", f"🔁 Mua chỉ <b>{n_thang_mua}/{n_thang_khoang}</b> tháng — không đều, phụ thuộc dự án"))
    else:
        risks.append(("low",    f"✅ Mua đều đặn: {n_thang_mua} tháng có giao dịch"))

    # Hiển thị điểm rủi ro
    if score >= 50:
        color, label = "#e74c3c", "🔴 RỦI RO CAO"
    elif score >= 25:
        color, label = "#f39c12", "🟡 RỦI RO TRUNG BÌNH"
    else:
        color, label = "#26c281", "🟢 RỦI RO THẤP"

    st.markdown(f"""
    <div style='background:#1a2035;border-radius:10px;padding:20px;text-align:center;margin:12px 0;'>
        <div style='font-size:34px;font-weight:900;color:{color};'>{label}</div>
        <div style='font-size:16px;color:#9aa0b0;margin-top:6px;'>
            Điểm rủi ro: <b style='color:{color}'>{score}/100</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for lvl, msg in risks:
        st.markdown(f'<div class="risk-{lvl}">{msg}</div>', unsafe_allow_html=True)