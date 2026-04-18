import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PKD Dự Án – Hoa Sen Analytics",
    layout="wide",
    page_icon="🏗️",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
#  GLOBAL STYLE
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Be Vietnam Pro', sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1528 60%, #111a2e 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #c8d6ea !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stRadio label { color: #7a9abf !important; font-size:11px; text-transform:uppercase; letter-spacing:.08em; }

/* ── Main background ── */
[data-testid="stAppViewContainer"] { background: #080d1a; }
[data-testid="stHeader"] { background: transparent; }

/* ── KPI cards ── */
.kpi-row { display:flex; gap:14px; margin-bottom:20px; }
.kpi-card {
    flex:1; background:linear-gradient(135deg,#0f1e36 0%,#132040 100%);
    border:1px solid rgba(56,139,253,0.18); border-radius:12px;
    padding:18px 20px; position:relative; overflow:hidden;
}
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:var(--accent); border-radius:12px 12px 0 0;
}
.kpi-icon { font-size:22px; margin-bottom:6px; display:block; }
.kpi-val  { font-size:26px; font-weight:800; color:#e8f0fe; line-height:1.1; font-family:'JetBrains Mono',monospace; }
.kpi-lab  { font-size:11px; color:#6a8cac; text-transform:uppercase; letter-spacing:.08em; margin-top:5px; }
.kpi-delta-up   { color:#34d399; font-size:11px; margin-top:3px; font-weight:600; }
.kpi-delta-down { color:#f87171; font-size:11px; margin-top:3px; font-weight:600; }

/* ── Section headings ── */
.sec-head {
    font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.12em;
    color:#388bfd; border-left:3px solid #388bfd; padding-left:10px;
    margin:24px 0 12px 0;
}

/* ── Risk gauge ── */
.risk-wrap { background:#0f1e36; border-radius:12px; padding:20px; margin-bottom:12px; }
.risk-bar-bg { background:#1a2b45; border-radius:99px; height:10px; margin:8px 0 4px; }
.risk-bar-fill { height:10px; border-radius:99px; transition:width .6s ease; }
.risk-label-row { display:flex; justify-content:space-between; align-items:center; }
.risk-label { font-size:13px; color:#8aa8cc; }
.risk-score { font-family:'JetBrains Mono',monospace; font-size:15px; font-weight:700; }
.risk-total-box {
    background:linear-gradient(135deg,#0f1e36,#1a2b45);
    border:1px solid rgba(56,139,253,.25); border-radius:14px;
    padding:22px; text-align:center; margin-top:10px;
}
.risk-total-val { font-size:52px; font-weight:800; font-family:'JetBrains Mono',monospace; }
.risk-total-sub { font-size:12px; color:#6a8cac; text-transform:uppercase; letter-spacing:.1em; margin-top:4px; }

/* ── Alert boxes ── */
.alert-high   { background:#2d0f0f; border-left:3px solid #f87171; padding:10px 14px; border-radius:6px; margin:5px 0; color:#fca5a5; font-size:13px; }
.alert-medium { background:#2d1f0a; border-left:3px solid #fbbf24; padding:10px 14px; border-radius:6px; margin:5px 0; color:#fde68a; font-size:13px; }
.alert-low    { background:#0a1f14; border-left:3px solid #34d399; padding:10px 14px; border-radius:6px; margin:5px 0; color:#6ee7b7; font-size:13px; }
.alert-info   { background:#0a1428; border-left:3px solid #388bfd; padding:10px 14px; border-radius:6px; margin:5px 0; color:#93c5fd; font-size:13px; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {
    font-size:13px; font-weight:600; color:#6a8cac !important;
    padding:8px 16px; border-radius:6px 6px 0 0;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color:#388bfd !important; border-bottom:2px solid #388bfd;
    background:rgba(56,139,253,.08);
}

/* ── Plotly charts ── */
.js-plotly-plot { border-radius:10px; overflow:hidden; }

/* ── Tables ── */
[data-testid="stDataFrame"] { border-radius:10px; overflow:hidden; }

/* ── Page title ── */
.page-title {
    font-size:28px; font-weight:800; color:#e8f0fe;
    letter-spacing:-.02em; margin-bottom:2px;
}
.page-sub {
    font-size:13px; color:#4a6a8a; margin-bottom:20px;
    font-family:'JetBrains Mono',monospace;
}
.logo-bar {
    display:flex; align-items:center; gap:12px; margin-bottom:24px;
    padding-bottom:16px; border-bottom:1px solid rgba(255,255,255,.06);
}
.logo-dot { width:36px; height:36px; background:#388bfd; border-radius:8px;
    display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PLOTLY THEME
# ══════════════════════════════════════════════════════════════
PLOT_BG   = "#0a0f1a"
PAPER_BG  = "#0a0f1a"
GRID_COL  = "rgba(255,255,255,0.05)"
FONT_COL  = "#8aa8cc"
COLORS    = ["#388bfd","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c","#22d3ee","#e879f9"]

def fig_layout(fig, title="", height=380):
    fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        font=dict(family="Be Vietnam Pro", color=FONT_COL, size=12),
        title=dict(text=title, font=dict(size=14, color="#c8d6ea"), x=0.01),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        margin=dict(l=12, r=12, t=42 if title else 12, b=12),
        xaxis=dict(gridcolor=GRID_COL, showline=False, tickfont=dict(size=11)),
        yaxis=dict(gridcolor=GRID_COL, showline=False, tickfont=dict(size=11)),
    )
    return fig

def fmt(v):
    try:
        v = float(v)
        if abs(v) >= 1e9:  return f"{v/1e9:.1f} Tỷ"
        if abs(v) >= 1e6:  return f"{v/1e6:.1f} Tr"
        if abs(v) >= 1e3:  return f"{v/1e3:.0f}K"
        return f"{v:,.0f}"
    except: return str(v)

def fmt_full(v):
    try: return f"{float(v):,.0f}"
    except: return str(v)

# ══════════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="logo-bar">
        <div class="logo-dot">🏗️</div>
        <div>
            <div style="font-size:14px;font-weight:700;color:#e8f0fe;">PKD Dự Án Analytics</div>
            <div style="font-size:11px;color:#4a6a8a;">Hoa Sen Group</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("📂 Upload Excel báo cáo", type=["xlsx"], accept_multiple_files=True)

if not uploaded:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:60vh;gap:16px;">
        <div style="font-size:64px;">🏗️</div>
        <div style="font-size:22px;font-weight:700;color:#e8f0fe;">PKD Dự Án – Sales Analytics</div>
        <div style="font-size:14px;color:#4a6a8a;text-align:center;">Upload file Excel báo cáo bán hàng để bắt đầu phân tích</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════════
NHOM_SP = [
    ("Ống HDPE",        r"HDPE"),
    ("Ống PVC nước",    r"PVC.*(?:nước|nong dài|nong trơn|thoát)"),
    ("Ống PVC bơm cát", r"PVC.*(?:cát|bơm cát)"),
    ("Ống PPR",         r"PPR"),
    ("Lõi PVC",         r"(?:Lơi|Lõi|lori)"),
    ("Phụ kiện & Keo",  r"(?:Nối|Co |Tê |Van |Keo |Măng|Bít|Y PVC|Y PPR)"),
    ("Ống thép",        r"(?:thép|steel|inox)"),
]

def find_header(fb):
    raw = pd.read_excel(io.BytesIO(fb), header=None, engine="openpyxl", nrows=40)
    kws = ["khách hàng","số chứng từ","tên hàng","ngày chứng từ","mã nhóm"]
    for i in range(raw.shape[0]):
        vals = ["" if (isinstance(v,float) and pd.isna(v)) else str(v) for v in raw.iloc[i].tolist()]
        if sum(1 for k in kws if k in " ".join(vals).lower()) >= 2:
            return i
    return 0

@st.cache_data(show_spinner="⏳ Đang xử lý dữ liệu…")
def load(file_data):
    frames = []
    for name, fb in file_data:
        hr = find_header(fb)
        df = pd.read_excel(io.BytesIO(fb), header=hr, engine="openpyxl")
        df.columns = [str(c).strip().replace("\n"," ") for c in df.columns]
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(how="all")
        df["_src"] = name
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)

    # Ngày
    df["Ngày chứng từ"] = pd.to_datetime(df["Ngày chứng từ"], dayfirst=True, errors="coerce")
    df = df[df["Ngày chứng từ"].notna()].copy()
    df["Nam"]   = df["Ngày chứng từ"].dt.year.astype(str)
    df["Quy"]   = df["Ngày chứng từ"].dt.to_period("Q").astype(str)
    df["Thang"] = df["Ngày chứng từ"].dt.to_period("M").astype(str)
    df["Thang_num"] = df["Ngày chứng từ"].dt.month

    # Số
    for c in ["Thành tiền bán","Thành tiền vốn","Lợi nhuận",
              "Khối lượng","Số lượng","Giá bán","Giá vốn",
              "Đơn giá vận chuyển","Đơn giá quy đổi"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0

    # Loại GD
    gc = df["Ghi chú"].astype(str).str.upper() if "Ghi chú" in df.columns else pd.Series("", index=df.index)
    loai = df["Loại đơn hàng"].astype(str).str.upper() if "Loại đơn hàng" in df.columns else pd.Series("", index=df.index)
    df["Loai_GD"] = "Xuất bán"
    df.loc[gc.str.contains(r"NHẬP TRẢ|TRẢ HÀNG", regex=True, na=False), "Loai_GD"] = "Trả hàng"
    df.loc[loai.str.contains(r"TRA HANG|HUY HD", regex=True, na=False), "Loai_GD"] = "Trả hàng"
    df.loc[gc.str.contains(r"BỔ SUNG|THAY THẾ|BS PKTM", regex=True, na=False), "Loai_GD"] = "Xuất bổ sung"

    # Nhóm SP
    ten = df["Tên hàng"].astype(str) if "Tên hàng" in df.columns else pd.Series("", index=df.index)
    df["Nhom_SP"] = "Khác"
    for lbl, pat in NHOM_SP:
        df.loc[ten.str.contains(pat, case=False, regex=True, na=False), "Nhom_SP"] = lbl

    # Biên LN
    df["Bien_LN"] = np.where(df["Thành tiền bán"]!=0, df["Lợi nhuận"]/df["Thành tiền bán"]*100, 0)

    # Tỉnh giao hàng
    if "Nơi giao hàng" in df.columns:
        tinh = df["Nơi giao hàng"].astype(str).str.extract(
            r'(?:Tỉnh|T\.|TP\s|Thành phố|tỉnh)\s*([A-ZÀ-Ỹa-zà-ỹ\s]+?)(?:,|\.|$)'
        )[0].str.strip()
        df["Tinh"] = tinh.fillna("Không rõ")
    else:
        df["Tinh"] = "Không rõ"

    # Cuối tháng flag
    df["Cuoi_thang"] = df["Ngày chứng từ"].dt.day >= 28

    return df

file_data = [(u.name, u.read()) for u in uploaded]
df_all = load(file_data)

if df_all.empty:
    st.error("❌ Không có dữ liệu hợp lệ."); st.stop()

# ══════════════════════════════════════════════════════════════
#  SIDEBAR FILTERS
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#4a6a8a;margin:16px 0 6px;">🔍 Bộ lọc</p>', unsafe_allow_html=True)

    # PKD
    pkd_col = "Tên nhóm KH" if "Tên nhóm KH" in df_all.columns else "Mã nhóm KH"
    pkd_list = ["Tất cả PKD"] + sorted(df_all[pkd_col].dropna().astype(str).unique())
    pkd_sel  = st.selectbox("🏢 Phòng Kinh Doanh", pkd_list)

    if pkd_sel != "Tất cả PKD":
        df_pkd = df_all[df_all[pkd_col].astype(str) == pkd_sel].copy()
    else:
        df_pkd = df_all.copy()

    # KH
    kh_list = ["Tất cả KH"] + sorted(df_pkd["Tên khách hàng"].dropna().astype(str).unique())
    kh_sel  = st.selectbox("👤 Khách hàng", kh_list)

    if kh_sel != "Tất cả KH":
        df_scope = df_pkd[df_pkd["Tên khách hàng"].astype(str) == kh_sel].copy()
    else:
        df_scope = df_pkd.copy()

    # Quý
    quy_list = sorted(df_scope["Quy"].dropna().unique())
    quy_sel  = st.multiselect("📅 Quý", quy_list, default=quy_list)
    df_scope = df_scope[df_scope["Quy"].isin(quy_sel)].copy()

    # Tháng
    thang_list = sorted(df_scope["Thang"].dropna().unique())
    thang_sel  = st.multiselect("📆 Tháng", thang_list, default=thang_list)
    df_scope   = df_scope[df_scope["Thang"].isin(thang_sel)].copy()

    st.markdown("---")
    st.markdown(f'<p style="font-size:11px;color:#4a6a8a;">{len(df_scope):,} dòng dữ liệu</p>', unsafe_allow_html=True)

df_ban = df_scope[df_scope["Loai_GD"] == "Xuất bán"].copy()

# ══════════════════════════════════════════════════════════════
#  PAGE HEADER
# ══════════════════════════════════════════════════════════════
ngay_min = df_scope["Ngày chứng từ"].min()
ngay_max = df_scope["Ngày chứng từ"].max()
scope_name = kh_sel if kh_sel != "Tất cả KH" else pkd_sel

st.markdown(f"""
<div class="logo-bar">
    <div class="logo-dot">🏗️</div>
    <div>
        <div class="page-title">{scope_name}</div>
        <div class="page-sub">{ngay_min.strftime('%d/%m/%Y') if pd.notna(ngay_min) else '?'} → {ngay_max.strftime('%d/%m/%Y') if pd.notna(ngay_max) else '?'} &nbsp;·&nbsp; PKD Dự Án Analytics</div>
    </div>
</div>
""", unsafe_allow_html=True)

if df_ban.empty:
    st.warning("⚠️ Không có dữ liệu xuất bán cho bộ lọc đã chọn."); st.stop()

# ══════════════════════════════════════════════════════════════
#  GLOBAL KPI BAR
# ══════════════════════════════════════════════════════════════
tong_dt   = df_ban["Thành tiền bán"].sum()
tong_ln   = df_ban["Lợi nhuận"].sum()
tong_kl   = df_ban["Khối lượng"].sum() / 1000
bien_ln   = (tong_ln/tong_dt*100) if tong_dt else 0
n_duan    = df_ban["Số ĐH"].nunique() if "Số ĐH" in df_ban.columns else 0
n_kh      = df_ban["Tên khách hàng"].nunique()

kpis = [
    ("#388bfd","💰","Doanh thu",  fmt(tong_dt)),
    ("#34d399","💹","Lợi nhuận",  fmt(tong_ln)),
    ("#fbbf24","📊","Biên LN",    f"{bien_ln:.1f}%"),
    ("#a78bfa","⚖️","KL (tấn)",   f"{tong_kl:,.1f}"),
    ("#22d3ee","📋","Dự án/ĐH",   f"{n_duan}"),
    ("#fb923c","👥","Khách hàng", f"{n_kh}"),
]
cols = st.columns(len(kpis))
for col, (accent, icon, lab, val) in zip(cols, kpis):
    col.markdown(f"""
    <div class="kpi-card" style="--accent:{accent}">
        <span class="kpi-icon">{icon}</span>
        <div class="kpi-val">{val}</div>
        <div class="kpi-lab">{lab}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ══════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════
t1, t2, t3, t4, t5 = st.tabs([
    "📦 Thói quen & Dự án",
    "📈 Doanh thu & Sản lượng",
    "💹 Lợi nhuận",
    "🚚 Giao hàng",
    "⚠️ Điểm rủi ro",
])

# ══════════════════════════════════════════════════════════════
#  TAB 1 – THÓI QUEN & DỰ ÁN
# ══════════════════════════════════════════════════════════════
with t1:
    st.markdown('<div class="sec-head">📋 Loại hình công trình dự án</div>', unsafe_allow_html=True)

    # Loại hình KD
    if "Loại hình kinh doanh" in df_ban.columns:
        df_loai = (df_ban.groupby("Loại hình kinh doanh")
                   .agg(N_CT=("Số chứng từ","nunique") if "Số chứng từ" in df_ban.columns else ("Thành tiền bán","count"),
                        DT=("Thành tiền bán","sum"),
                        KL=("Khối lượng", lambda x: x.sum()/1000))
                   .reset_index().sort_values("DT", ascending=False))

        c1, c2 = st.columns([1.4,1])
        with c1:
            fig = px.bar(df_loai, y="Loại hình kinh doanh", x="DT",
                         orientation="h", color="DT",
                         color_continuous_scale=[[0,"#1a2b45"],[1,"#388bfd"]],
                         text=df_loai["DT"].apply(fmt),
                         labels={"DT":"Doanh thu","Loại hình kinh doanh":""})
            fig.update_traces(textposition="outside", textfont_size=11)
            fig.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
            fig_layout(fig, "Doanh thu theo Loại hình công trình", height=320)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.pie(df_loai, names="Loại hình kinh doanh", values="DT",
                          hole=0.55, color_discrete_sequence=COLORS)
            fig2.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
            fig_layout(fig2, "Tỷ trọng DT", height=320)
            st.plotly_chart(fig2, use_container_width=True)

    # Top dự án (Số ĐH)
    st.markdown('<div class="sec-head">🏆 Top dự án theo doanh thu</div>', unsafe_allow_html=True)
    if "Số ĐH" in df_ban.columns:
        df_duan = (df_ban.groupby("Số ĐH")
                   .agg(KH=("Tên khách hàng","first"),
                        Loai=("Loại hình kinh doanh","first") if "Loại hình kinh doanh" in df_ban.columns else ("Tên khách hàng","first"),
                        DT=("Thành tiền bán","sum"),
                        LN=("Lợi nhuận","sum"),
                        KL=("Khối lượng", lambda x: round(x.sum()/1000,1)),
                        N_SP=("Tên hàng","nunique"),
                        Ngay_dau=("Ngày chứng từ","min"),
                        Ngay_cuoi=("Ngày chứng từ","max"))
                   .reset_index().sort_values("DT", ascending=False))
        df_duan["Bien_%"] = (df_duan["LN"]/df_duan["DT"]*100).round(1)
        df_duan["Thoi_gian"] = (df_duan["Ngay_cuoi"]-df_duan["Ngay_dau"]).dt.days.apply(lambda x: f"{x} ngày")
        df_duan["DT_fmt"] = df_duan["DT"].apply(fmt)
        df_duan["LN_fmt"] = df_duan["LN"].apply(fmt)

        top_n = st.slider("Số dự án hiển thị", 5, 30, 15, key="top_duan")
        df_top_duan = df_duan.head(top_n)

        fig_d = px.bar(df_top_duan, x="Số ĐH", y="DT",
                       color="Bien_%", color_continuous_scale="RdYlGn",
                       hover_data={"KH":True,"Loai":True,"KL":True,"Thoi_gian":True,"DT_fmt":True},
                       labels={"DT":"Doanh thu","Bien_%":"Biên LN%"})
        fig_d.update_layout(xaxis_tickangle=-35, xaxis_tickfont_size=9)
        fig_layout(fig_d, f"Top {top_n} dự án theo Doanh thu (màu = Biên LN%)", height=380)
        st.plotly_chart(fig_d, use_container_width=True)

        show_cols = ["Số ĐH","KH","Loai","DT_fmt","LN_fmt","Bien_%","KL","N_SP","Thoi_gian"]
        show_cols = [c for c in show_cols if c in df_top_duan.columns]
        rename_map = {"Số ĐH":"Đơn hàng","KH":"Khách hàng","Loai":"Loại hình",
                      "DT_fmt":"Doanh thu","LN_fmt":"Lợi nhuận","Bien_%":"Biên LN%",
                      "KL":"KL (tấn)","N_SP":"# SP","Thoi_gian":"Thời gian"}
        st.dataframe(df_top_duan[show_cols].rename(columns=rename_map),
                     use_container_width=True, hide_index=True)

    # Top sản phẩm
    st.markdown('<div class="sec-head">📦 Mặt hàng quan trọng – mua nhiều nhất</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        df_nhom = (df_ban.groupby("Nhom_SP")
                   .agg(N=("Nhom_SP","count"), KL=("Khối lượng",lambda x: x.sum()/1000),
                        DT=("Thành tiền bán","sum"))
                   .reset_index().sort_values("DT",ascending=False))
        fig_n = px.bar(df_nhom, x="Nhom_SP", y="DT", color="Nhom_SP",
                       text=df_nhom["DT"].apply(fmt),
                       color_discrete_sequence=COLORS, labels={"DT":"DT","Nhom_SP":""})
        fig_n.update_traces(textposition="outside", textfont_size=10)
        fig_n.update_layout(showlegend=False)
        fig_layout(fig_n, "DT theo nhóm sản phẩm", height=320)
        st.plotly_chart(fig_n, use_container_width=True)
    with c2:
        if "Tên hàng" in df_ban.columns:
            df_sp = (df_ban.groupby("Tên hàng")
                     .agg(N=("Tên hàng","count"), KL=("Khối lượng",lambda x: round(x.sum()/1000,1)),
                          DT=("Thành tiền bán","sum"))
                     .reset_index().sort_values("DT",ascending=False).head(10))
            fig_sp = px.bar(df_sp, y="Tên hàng", x="KL", orientation="h",
                            color="KL", color_continuous_scale=[[0,"#1a2b45"],[1,"#34d399"]],
                            text=df_sp["KL"].apply(lambda x: f"{x:.0f}T"),
                            labels={"KL":"KL (tấn)","Tên hàng":""})
            fig_sp.update_traces(textposition="outside", textfont_size=10)
            fig_sp.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
            fig_layout(fig_sp, "Top 10 SP – Khối lượng (tấn)", height=320)
            st.plotly_chart(fig_sp, use_container_width=True)

    # Thời điểm mua nhiều nhất
    st.markdown('<div class="sec-head">📅 Thời điểm mua hàng nhiều nhất</div>', unsafe_allow_html=True)
    if "Tên hàng" in df_ban.columns:
        top5_sp = df_ban.groupby("Tên hàng")["Khối lượng"].sum().nlargest(5).index.tolist()
        df_heat = (df_ban[df_ban["Tên hàng"].isin(top5_sp)]
                   .groupby(["Tên hàng","Thang"])["Khối lượng"]
                   .sum().reset_index())
        df_piv = df_heat.pivot(index="Tên hàng", columns="Thang", values="Khối lượng").fillna(0)
        if not df_piv.empty:
            fig_h = px.imshow(df_piv/1000, color_continuous_scale="Blues", aspect="auto",
                              labels=dict(color="KL (tấn)"),
                              title="Heatmap KL (tấn): Top 5 SP × Tháng")
            fig_h.update_layout(plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                                 font_color=FONT_COL, height=280,
                                 coloraxis_colorbar=dict(tickfont=dict(size=10)))
            st.plotly_chart(fig_h, use_container_width=True)

# ══════════════════════════════════════════════════════════════
#  TAB 2 – DOANH THU & SẢN LƯỢNG
# ══════════════════════════════════════════════════════════════
with t2:
    st.markdown('<div class="sec-head">📈 Biến động Doanh thu & Sản lượng theo tháng</div>', unsafe_allow_html=True)

    df_m = (df_ban.groupby("Thang")
            .agg(DT=("Thành tiền bán","sum"),
                 KL=("Khối lượng", lambda x: x.sum()/1000),
                 LN=("Lợi nhuận","sum"),
                 N_DH=("Số ĐH","nunique") if "Số ĐH" in df_ban.columns else ("Thành tiền bán","count"))
            .reset_index().sort_values("Thang"))
    df_m["Bien_%"] = (df_m["LN"]/df_m["DT"].replace(0,np.nan)*100).round(1).fillna(0)
    df_m["KL_prev"] = df_m["KL"].shift(1)
    df_m["KL_change_%"] = ((df_m["KL"]-df_m["KL_prev"])/df_m["KL_prev"]*100).round(1)

    # Combo chart
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Doanh thu (VNĐ) & Khối lượng (tấn)", "Biên LN (%) & Tăng trưởng KL (%)"),
        vertical_spacing=0.10, row_heights=[0.6, 0.4]
    )
    fig.add_trace(go.Bar(x=df_m["Thang"], y=df_m["DT"], name="Doanh thu",
                         marker_color="#388bfd", opacity=0.85,
                         text=df_m["DT"].apply(fmt), textposition="outside", textfont_size=10), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_m["Thang"], y=df_m["KL"], name="KL (tấn)",
                             mode="lines+markers", line=dict(color="#34d399",width=2.5),
                             marker=dict(size=7), yaxis="y2"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_m["Thang"], y=df_m["Bien_%"], name="Biên LN%",
                             mode="lines+markers+text",
                             text=[f"{v:.1f}%" for v in df_m["Bien_%"]],
                             textposition="top center", textfont_size=10,
                             line=dict(color="#fbbf24",width=2)), row=2, col=1)
    fig.add_trace(go.Bar(x=df_m["Thang"], y=df_m["KL_change_%"], name="Tăng KL%",
                         marker_color=["#f87171" if v<0 else "#34d399" for v in df_m["KL_change_%"].fillna(0)],
                         opacity=0.7), row=2, col=1)
    fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        font=dict(family="Be Vietnam Pro", color=FONT_COL, size=11),
        height=560, legend=dict(orientation="h", y=-0.06, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=12,r=12,t=36,b=12),
        xaxis=dict(gridcolor=GRID_COL), xaxis2=dict(gridcolor=GRID_COL),
        yaxis=dict(gridcolor=GRID_COL), yaxis2=dict(gridcolor=GRID_COL),
        yaxis3=dict(gridcolor=GRID_COL), yaxis4=dict(gridcolor=GRID_COL),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tháng đột biến
    st.markdown('<div class="sec-head">⚡ Tháng có sản lượng tăng đột biến</div>', unsafe_allow_html=True)
    mean_kl = df_m["KL"].mean()
    std_kl  = df_m["KL"].std() or 1
    dot_bien = df_m[df_m["KL"] > mean_kl + 1.5*std_kl]
    giam_dot = df_m[df_m["KL"] < mean_kl - 1.5*std_kl]

    if not dot_bien.empty:
        for _, r in dot_bien.iterrows():
            st.markdown(f'<div class="alert-high">🔥 Tháng <b>{r["Thang"]}</b>: KL = <b>{r["KL"]:,.0f} tấn</b> — cao hơn TB {((r["KL"]-mean_kl)/mean_kl*100):.0f}% → Kiểm tra dự án lớn hoặc đơn hàng tập trung</div>', unsafe_allow_html=True)
    if not giam_dot.empty:
        for _, r in giam_dot.iterrows():
            st.markdown(f'<div class="alert-medium">📉 Tháng <b>{r["Thang"]}</b>: KL = <b>{r["KL"]:,.0f} tấn</b> — thấp hơn TB {((mean_kl-r["KL"])/mean_kl*100):.0f}% → Kiểm tra tiến độ dự án</div>', unsafe_allow_html=True)
    if dot_bien.empty and giam_dot.empty:
        st.markdown('<div class="alert-low">✅ Sản lượng ổn định, không có tháng đột biến.</div>', unsafe_allow_html=True)

    # Bảng tháng
    df_m_s = df_m.copy()
    df_m_s["DT"]  = df_m_s["DT"].apply(fmt)
    df_m_s["LN"]  = df_m_s["LN"].apply(fmt)
    df_m_s["KL"]  = df_m_s["KL"].round(1)
    df_m_s = df_m_s.drop(columns=["KL_prev","KL_change_%"],errors="ignore")
    df_m_s.columns = ["Tháng","Doanh thu","KL (tấn)","Lợi nhuận","Số ĐH","Biên LN (%)"]
    st.dataframe(df_m_s, use_container_width=True, hide_index=True)

    # Quý
    st.markdown('<div class="sec-head">📊 Tổng hợp theo Quý</div>', unsafe_allow_html=True)
    df_q = (df_ban.groupby("Quy")
            .agg(DT=("Thành tiền bán","sum"),
                 KL=("Khối lượng",lambda x: round(x.sum()/1000,1)),
                 LN=("Lợi nhuận","sum"),
                 N_DH=("Số ĐH","nunique") if "Số ĐH" in df_ban.columns else ("Thành tiền bán","count"),
                 N_KH=("Tên khách hàng","nunique"))
            .reset_index())
    df_q["Bien_%"] = (df_q["LN"]/df_q["DT"].replace(0,np.nan)*100).round(1).fillna(0)

    c1,c2 = st.columns(2)
    with c1:
        fig_q = px.bar(df_q, x="Quy", y="DT", color="Bien_%",
                       color_continuous_scale="RdYlGn",
                       text=df_q["DT"].apply(fmt),
                       labels={"DT":"Doanh thu","Bien_%":"Biên LN%","Quy":"Quý"})
        fig_q.update_traces(textposition="outside", textfont_size=11)
        fig_layout(fig_q, "Doanh thu theo Quý (màu = Biên LN%)", height=300)
        st.plotly_chart(fig_q, use_container_width=True)
    with c2:
        df_q_s = df_q.copy()
        df_q_s["DT"] = df_q_s["DT"].apply(fmt)
        df_q_s["LN"] = df_q_s["LN"].apply(fmt)
        df_q_s.columns = ["Quý","Doanh thu","KL (tấn)","Lợi nhuận","Số ĐH","Số KH","Biên LN (%)"]
        st.dataframe(df_q_s, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
#  TAB 3 – LỢI NHUẬN
# ══════════════════════════════════════════════════════════════
with t3:
    st.markdown('<div class="sec-head">💹 Biên lợi nhuận theo Dự án</div>', unsafe_allow_html=True)

    if "Số ĐH" in df_ban.columns:
        df_ln_duan = (df_ban.groupby(["Số ĐH"])
                      .agg(KH=("Tên khách hàng","first"),
                           Loai=("Loại hình kinh doanh","first") if "Loại hình kinh doanh" in df_ban.columns else ("Tên khách hàng","first"),
                           DT=("Thành tiền bán","sum"),
                           Von=("Thành tiền vốn","sum"),
                           LN=("Lợi nhuận","sum"),
                           KL=("Khối lượng",lambda x: round(x.sum()/1000,1)),
                           Thang_bd=("Thang","min"), Thang_kt=("Thang","max"))
                      .reset_index())
        df_ln_duan["Bien_%"] = (df_ln_duan["LN"]/df_ln_duan["DT"].replace(0,np.nan)*100).round(1).fillna(0)
        df_ln_duan = df_ln_duan.sort_values("DT",ascending=False)

        # Scatter: DT vs Biên LN
        fig_sc = px.scatter(df_ln_duan, x="DT", y="Bien_%",
                            size="KL", color="Bien_%",
                            hover_data={"KH":True,"Loai":True,"KL":True},
                            color_continuous_scale="RdYlGn",
                            labels={"DT":"Doanh thu","Bien_%":"Biên LN%","KL":"KL (tấn)"})
        fig_sc.add_hline(y=df_ln_duan["Bien_%"].mean(),
                         line_dash="dash", line_color="#fbbf24",
                         annotation_text=f"TB: {df_ln_duan['Bien_%'].mean():.1f}%",
                         annotation_font_color="#fbbf24")
        fig_layout(fig_sc, "Scatter: DT vs Biên LN% theo Dự án (kích thước = KL tấn)", height=420)
        st.plotly_chart(fig_sc, use_container_width=True)

        # Biên LN phân phối
        c1,c2 = st.columns(2)
        with c1:
            fig_hist = px.histogram(df_ln_duan, x="Bien_%", nbins=20,
                                    color_discrete_sequence=["#388bfd"],
                                    labels={"Bien_%":"Biên LN%","count":"Số dự án"})
            fig_layout(fig_hist, "Phân phối Biên LN% các dự án", height=300)
            st.plotly_chart(fig_hist, use_container_width=True)
        with c2:
            # Biên LN theo loại hình
            if "Loai" in df_ln_duan.columns:
                df_bl = (df_ln_duan.groupby("Loai")["Bien_%"]
                         .mean().round(1).reset_index().sort_values("Bien_%",ascending=False))
                fig_bl = px.bar(df_bl, y="Loai", x="Bien_%", orientation="h",
                                color="Bien_%", color_continuous_scale="RdYlGn",
                                text=df_bl["Bien_%"].apply(lambda v: f"{v:.1f}%"),
                                labels={"Bien_%":"Biên LN% TB","Loai":""})
                fig_bl.update_traces(textposition="outside", textfont_size=10)
                fig_bl.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
                fig_layout(fig_bl, "Biên LN% TB theo Loại hình", height=300)
                st.plotly_chart(fig_bl, use_container_width=True)

        # Dự án LN âm
        st.markdown('<div class="sec-head">❗ Dự án Lợi nhuận âm / Biên LN thấp</div>', unsafe_allow_html=True)
        df_ln_am = df_ln_duan[df_ln_duan["LN"] < 0].sort_values("LN")
        if not df_ln_am.empty:
            for _, r in df_ln_am.head(10).iterrows():
                st.markdown(f'<div class="alert-high">🔴 <b>{r["Số ĐH"]}</b> | {r.get("KH","?")} | DT: {fmt(r["DT"])} | LN: <b>{fmt(r["LN"])}</b> | Biên: {r["Bien_%"]:.1f}%</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-low">✅ Không có dự án nào lợi nhuận âm.</div>', unsafe_allow_html=True)

        # Thống kê dự án trong năm
        st.markdown('<div class="sec-head">📊 Số dự án hoạt động theo tháng</div>', unsafe_allow_html=True)
        df_duan_thang = (df_ban.groupby("Thang")["Số ĐH"].nunique().reset_index(name="Số dự án"))
        fig_nd = px.bar(df_duan_thang, x="Thang", y="Số dự án",
                        color="Số dự án", color_continuous_scale=[[0,"#1a2b45"],[1,"#388bfd"]],
                        text="Số dự án", labels={"Thang":"Tháng"})
        fig_nd.update_traces(textposition="outside", textfont_size=11)
        fig_nd.update_layout(coloraxis_showscale=False)
        fig_layout(fig_nd, "Số dự án/đơn hàng hoạt động theo tháng", height=300)
        st.plotly_chart(fig_nd, use_container_width=True)

        # Bảng chi tiết
        with st.expander("📋 Bảng chi tiết Biên LN từng dự án"):
            df_ln_s = df_ln_duan.copy()
            df_ln_s["DT"] = df_ln_s["DT"].apply(fmt)
            df_ln_s["LN"] = df_ln_s["LN"].apply(fmt)
            df_ln_s["Von"] = df_ln_s["Von"].apply(fmt)
            show = ["Số ĐH","KH","Loai","DT","Von","LN","Bien_%","KL","Thang_bd","Thang_kt"]
            show = [c for c in show if c in df_ln_s.columns]
            st.dataframe(df_ln_s[show].rename(columns={"KH":"Khách hàng","Loai":"Loại hình",
                                                         "Bien_%":"Biên LN%","KL":"KL(tấn)",
                                                         "Thang_bd":"Tháng BĐ","Thang_kt":"Tháng KT"}),
                         use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════
#  TAB 4 – GIAO HÀNG
# ══════════════════════════════════════════════════════════════
with t4:
    st.markdown('<div class="sec-head">🚚 Địa điểm & Hình thức giao hàng</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if "Freight Terms" in df_ban.columns:
            df_ft = df_ban["Freight Terms"].value_counts().reset_index()
            df_ft.columns = ["Hình thức","Số lần"]
            fig_ft = px.pie(df_ft, names="Hình thức", values="Số lần",
                            hole=0.55, color_discrete_sequence=COLORS)
            fig_ft.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
            fig_layout(fig_ft, "Điều kiện giao hàng (Freight Terms)", height=300)
            st.plotly_chart(fig_ft, use_container_width=True)
    with c2:
        if "Shipping method" in df_ban.columns:
            df_sm = df_ban["Shipping method"].value_counts().reset_index()
            df_sm.columns = ["Phương tiện","Số lần"]
            fig_sm = px.pie(df_sm, names="Phương tiện", values="Số lần",
                            hole=0.55, color_discrete_sequence=COLORS[2:])
            fig_sm.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
            fig_layout(fig_sm, "Phương tiện vận chuyển", height=300)
            st.plotly_chart(fig_sm, use_container_width=True)

    # Địa điểm giao hàng (tỉnh) – quan trọng với PKD dự án
    st.markdown('<div class="sec-head">📍 Phân bổ địa điểm giao hàng – Tỉnh/TP (quan trọng với PKD dự án)</div>', unsafe_allow_html=True)

    df_tinh = (df_ban.groupby("Tinh")
               .agg(N=("Tinh","count"),
                    KL=("Khối lượng",lambda x: round(x.sum()/1000,1)),
                    DT=("Thành tiền bán","sum"))
               .reset_index().sort_values("DT",ascending=False))
    df_tinh = df_tinh[df_tinh["Tinh"].str.len() > 2].head(25)

    c1,c2 = st.columns([1.6,1])
    with c1:
        fig_t = px.bar(df_tinh.head(15), y="Tinh", x="KL",
                       orientation="h", color="KL",
                       color_continuous_scale=[[0,"#1a2b45"],[1,"#388bfd"]],
                       text=df_tinh.head(15)["KL"].apply(lambda v: f"{v:.0f}T"),
                       labels={"KL":"KL (tấn)","Tinh":""})
        fig_t.update_traces(textposition="outside", textfont_size=10)
        fig_t.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
        fig_layout(fig_t, "Top 15 Tỉnh/TP theo Khối lượng giao hàng", height=420)
        st.plotly_chart(fig_t, use_container_width=True)
    with c2:
        fig_tp = px.pie(df_tinh.head(10), names="Tinh", values="DT",
                        hole=0.5, color_discrete_sequence=COLORS)
        fig_tp.update_traces(textposition="inside", textinfo="percent", textfont_size=10)
        fig_layout(fig_tp, "Top 10 Tỉnh – Tỷ trọng DT", height=420)
        st.plotly_chart(fig_tp, use_container_width=True)

    # Nơi giao hàng chi tiết theo dự án
    if "Số ĐH" in df_ban.columns and "Nơi giao hàng" in df_ban.columns:
        st.markdown('<div class="sec-head">🗺️ Địa điểm giao hàng chi tiết theo Dự án</div>', unsafe_allow_html=True)
        df_gh = (df_ban.groupby(["Số ĐH","Nơi giao hàng"])
                 .agg(KH=("Tên khách hàng","first"),
                      KL=("Khối lượng",lambda x: round(x.sum()/1000,2)),
                      DT=("Thành tiền bán","sum"))
                 .reset_index().sort_values("DT",ascending=False))
        df_gh["DT"] = df_gh["DT"].apply(fmt)
        with st.expander(f"📋 {len(df_gh)} điểm giao hàng – xem chi tiết"):
            st.dataframe(df_gh.rename(columns={"Số ĐH":"Đơn hàng","KH":"Khách hàng",
                                                 "KL":"KL(tấn)","DT":"Doanh thu"}),
                         use_container_width=True, hide_index=True)

    # Giao hàng theo tháng
    st.markdown('<div class="sec-head">📅 Phân bổ giao hàng theo tháng & Phương tiện</div>', unsafe_allow_html=True)
    if "Shipping method" in df_ban.columns:
        df_gh_m = (df_ban.groupby(["Thang","Shipping method"])
                   .agg(KL=("Khối lượng",lambda x: x.sum()/1000))
                   .reset_index())
        fig_gm = px.bar(df_gh_m, x="Thang", y="KL", color="Shipping method",
                        barmode="stack", color_discrete_sequence=COLORS,
                        labels={"KL":"KL (tấn)","Thang":"Tháng","Shipping method":"Phương tiện"})
        fig_layout(fig_gm, "KL (tấn) giao hàng theo tháng & Phương tiện", height=320)
        st.plotly_chart(fig_gm, use_container_width=True)

# ══════════════════════════════════════════════════════════════
#  TAB 5 – ĐIỂM RỦI RO
# ══════════════════════════════════════════════════════════════
with t5:
    st.markdown('<div class="sec-head">⚠️ Phân tích & Chấm điểm Rủi ro (thang 100)</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert-info">📌 Điểm rủi ro dựa trên 7 tiêu chí, mỗi tiêu chí có trọng số riêng theo đặc thù PKD Dự án.</div>', unsafe_allow_html=True)

    tong_dt_ban = df_ban["Thành tiền bán"].sum()
    tong_ln_ban = df_ban["Lợi nhuận"].sum()
    bien_tb_all = (tong_ln_ban/tong_dt_ban*100) if tong_dt_ban else 0

    criteria = []  # (name, weight, score_0_to_weight, level, detail)

    # ── C1: Thói quen – Tần suất đột biến KL (10/100) ──
    kl_std  = df_m["KL"].std() if len(df_m)>1 else 0
    kl_mean = df_m["KL"].mean() if len(df_m)>0 else 1
    n_dotbien = len(df_m[df_m["KL"] > kl_mean + 1.5*kl_std]) if kl_std>0 else 0
    c1_score = min(10, n_dotbien * 3)
    c1_level = "high" if c1_score>=7 else "medium" if c1_score>=4 else "low"
    criteria.append(("📦 Tần suất KL đột biến", 10, c1_score, c1_level,
                      f"{n_dotbien} tháng có KL đột biến vượt TB 1.5σ"))

    # ── C2: Doanh thu – Tập trung cuối tháng (5/100) ──
    dt_cuoi = df_ban[df_ban["Cuoi_thang"]]["Thành tiền bán"].sum()
    tl_cuoi = (dt_cuoi/tong_dt_ban*100) if tong_dt_ban else 0
    c2_score = min(5, tl_cuoi/10)
    c2_level = "high" if tl_cuoi>40 else "medium" if tl_cuoi>25 else "low"
    criteria.append(("📅 DT tập trung cuối tháng", 5, round(c2_score,1), c2_level,
                      f"{tl_cuoi:.1f}% DT rơi vào ngày 28–31"))

    # ── C3: Lợi nhuận âm (20/100) ──
    df_ln_am_ban = df_ban[df_ban["Lợi nhuận"] < 0]
    tl_ln_am = (len(df_ln_am_ban)/len(df_ban)*100) if len(df_ban)>0 else 0
    c3_score = min(20, tl_ln_am*2)
    c3_level = "high" if tl_ln_am>5 else "medium" if tl_ln_am>1 else "low"
    criteria.append(("📉 Dòng Lợi nhuận âm", 20, round(c3_score,1), c3_level,
                      f"{len(df_ln_am_ban)} dòng LN âm ({tl_ln_am:.1f}%)"))

    # ── C4: Biên LN thấp (20/100) ──
    c4_score = 20 if bien_tb_all < 5 else (12 if bien_tb_all < 15 else (5 if bien_tb_all < 25 else 0))
    c4_level = "high" if c4_score>=15 else "medium" if c4_score>=8 else "low"
    criteria.append(("💹 Biên LN tổng thể", 20, c4_score, c4_level,
                      f"Biên LN trung bình = {bien_tb_all:.1f}%"))

    # ── C5: Trả hàng (15/100) ──
    df_tra = df_scope[df_scope["Loai_GD"] == "Trả hàng"]
    tong_tra = abs(df_tra["Thành tiền bán"].sum())
    tl_tra   = (tong_tra/tong_dt_ban*100) if tong_dt_ban else 0
    c5_score = min(15, tl_tra*1.5)
    c5_level = "high" if tl_tra>10 else "medium" if tl_tra>3 else "low"
    criteria.append(("↩️ Tỷ lệ trả hàng", 15, round(c5_score,1), c5_level,
                      f"Tỷ lệ trả hàng: {tl_tra:.1f}% ({fmt(tong_tra)} VNĐ)"))

    # ── C6: Địa điểm giao hàng phân tán (10/100) ──
    n_tinh = df_ban["Tinh"].nunique()
    c6_score = min(10, n_tinh * 0.8)
    c6_level = "high" if n_tinh>10 else "medium" if n_tinh>5 else "low"
    criteria.append(("📍 Phân tán địa điểm giao", 10, round(c6_score,1), c6_level,
                      f"Giao hàng tới {n_tinh} tỉnh/TP"))

    # ── C7: Giá bán < Giá vốn (20/100) ──
    if "Giá bán" in df_ban.columns and "Giá vốn" in df_ban.columns:
        n_gban_thap = ((df_ban["Giá bán"]>0) & (df_ban["Giá vốn"]>0) &
                       (df_ban["Giá bán"]<df_ban["Giá vốn"])).sum()
        tl_gban = (n_gban_thap/len(df_ban)*100) if len(df_ban)>0 else 0
        c7_score = min(20, tl_gban*4)
        c7_level = "high" if tl_gban>10 else "medium" if tl_gban>3 else "low"
    else:
        n_gban_thap, tl_gban, c7_score, c7_level = 0,0,0,"low"
    criteria.append(("💸 Giá bán < Giá vốn", 20, round(c7_score,1), c7_level,
                      f"{n_gban_thap} dòng ({tl_gban:.1f}%) giá bán thấp hơn giá vốn"))

    # Tổng điểm
    total_score = sum(c[2] for c in criteria)
    max_score   = sum(c[1] for c in criteria)  # = 100
    norm_score  = round(total_score / max_score * 100) if max_score else 0

    if norm_score >= 60:
        risk_color, risk_label = "#f87171", "RỦI RO CAO"
    elif norm_score >= 35:
        risk_color, risk_label = "#fbbf24", "RỦI RO TB"
    else:
        risk_color, risk_label = "#34d399", "RỦI RO THẤP"

    # Gauge chart
    c1_col, c2_col = st.columns([1, 2])
    with c1_col:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=norm_score,
            domain={"x":[0,1],"y":[0,1]},
            number={"font":{"size":48,"color":risk_color,"family":"JetBrains Mono"}},
            gauge={
                "axis":{"range":[0,100],"tickfont":{"size":10,"color":FONT_COL}},
                "bar":{"color":risk_color},
                "bgcolor":"#0f1e36",
                "bordercolor":"#1a2b45",
                "steps":[
                    {"range":[0,35],"color":"#0a1f14"},
                    {"range":[35,60],"color":"#2d1f0a"},
                    {"range":[60,100],"color":"#2d0f0f"},
                ],
                "threshold":{"line":{"color":"white","width":2},"thickness":0.8,"value":norm_score}
            }
        ))
        fig_gauge.update_layout(
            paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
            font=dict(color=FONT_COL, family="Be Vietnam Pro"),
            height=260, margin=dict(l=10,r=10,t=10,b=10),
            annotations=[dict(text=risk_label, x=0.5, y=-0.08, showarrow=False,
                               font=dict(size=13,color=risk_color,family="Be Vietnam Pro"),
                               xanchor="center")]
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with c2_col:
        st.markdown('<div class="risk-wrap">', unsafe_allow_html=True)
        for name, weight, score, level, detail in criteria:
            pct = (score/weight*100) if weight else 0
            bar_color = "#f87171" if level=="high" else "#fbbf24" if level=="medium" else "#34d399"
            st.markdown(f"""
            <div style="margin-bottom:14px;">
                <div class="risk-label-row">
                    <span class="risk-label">{name}</span>
                    <span class="risk-score" style="color:{bar_color}">{score:.1f} / {weight}</span>
                </div>
                <div style="font-size:11px;color:#4a6a8a;margin:2px 0 4px;">{detail}</div>
                <div class="risk-bar-bg">
                    <div class="risk-bar-fill" style="width:{pct:.0f}%;background:{bar_color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Chi tiết cảnh báo
    st.markdown('<div class="sec-head">🔍 Chi tiết cảnh báo</div>', unsafe_allow_html=True)
    for name, weight, score, level, detail in criteria:
        if level == "high":
            st.markdown(f'<div class="alert-high">🔴 <b>{name}</b>: {detail} — Điểm rủi ro: {score:.1f}/{weight}</div>', unsafe_allow_html=True)
        elif level == "medium":
            st.markdown(f'<div class="alert-medium">🟡 <b>{name}</b>: {detail} — Điểm rủi ro: {score:.1f}/{weight}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="alert-low">🟢 <b>{name}</b>: {detail} ✓</div>', unsafe_allow_html=True)

    # Công nợ placeholder
    st.markdown('<div class="sec-head">🏦 Công nợ (chưa cập nhật)</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="alert-info">
        📋 <b>Module Công nợ chưa có dữ liệu.</b><br>
        Để phân tích đầy đủ, cần bổ sung file:<br>
        &nbsp;&nbsp;• <b>AR Aging Report</b> → số ngày tồn đọng, quá hạn từng dự án<br>
        &nbsp;&nbsp;• <b>Lịch sử thanh toán</b> → thói quen NET 30/60/90 ngày theo từng KH<br>
        &nbsp;&nbsp;• <b>Hạn mức tín dụng</b> → so sánh dư nợ thực tế với hạn mức<br>
        Dấu hiệu từ dữ liệu hiện tại: đơn hàng dự án (PO/HĐ) thường thanh toán chậm NET 30–90 ngày, đặc biệt khi giao hàng nhiều đợt theo tiến độ công trình.
    </div>
    """, unsafe_allow_html=True)