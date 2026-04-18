"""
PKD Dự Án Analytics – Hoa Sen Group
====================================
Logic giá đúng:
  • Giá bán    (VNĐ/cái)  × Số lượng  = Thành tiền bán
  • Giá vốn    (VNĐ/kg)   × Khối lượng = Thành tiền vốn
  • Đơn giá quy đổi = Thành tiền bán / Khối lượng  (VNĐ/kg – dùng so sánh với Giá vốn)
  • Margin/kg  = Đơn giá quy đổi – Giá vốn
"""

import io
import warnings
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PKD Dự Án Analytics – Hoa Sen",
    layout="wide", page_icon="🏗️",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Be Vietnam Pro',sans-serif;}

/* Sidebar */
[data-testid="stSidebar"]{background:linear-gradient(160deg,#060c1a 0%,#0a1428 100%);border-right:1px solid rgba(255,255,255,.05);}
[data-testid="stSidebar"] *{color:#b8cfe8!important;}
[data-testid="stSidebar"] label{color:#4a7aaa!important;font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;}
[data-testid="stAppViewContainer"]{background:#07111f;}
[data-testid="stHeader"]{background:transparent;}

/* KPI */
.kpi-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px;}
.kpi-card{background:linear-gradient(135deg,#0d1c33 0%,#0f2040 100%);
  border:1px solid rgba(56,139,253,.15);border-radius:12px;padding:16px 18px;
  position:relative;overflow:hidden;}
.kpi-card::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--ac);border-radius:12px 12px 0 0;}
.kpi-icon{font-size:20px;margin-bottom:6px;}
.kpi-v{font-size:22px;font-weight:800;color:#e4eefb;line-height:1.15;font-family:'JetBrains Mono',monospace;}
.kpi-l{font-size:10px;color:#4a7aaa;text-transform:uppercase;letter-spacing:.09em;margin-top:5px;}

/* Sections */
.sec{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
  color:#388bfd;border-left:3px solid #388bfd;padding-left:10px;margin:22px 0 12px 0;}

/* Alerts */
.al-h{background:#30100e;border-left:3px solid #f87171;padding:9px 13px;border-radius:6px;margin:4px 0;color:#fca5a5;font-size:12.5px;}
.al-m{background:#2d1e0a;border-left:3px solid #fbbf24;padding:9px 13px;border-radius:6px;margin:4px 0;color:#fde68a;font-size:12.5px;}
.al-l{background:#091e12;border-left:3px solid #34d399;padding:9px 13px;border-radius:6px;margin:4px 0;color:#6ee7b7;font-size:12.5px;}
.al-i{background:#091828;border-left:3px solid #388bfd;padding:9px 13px;border-radius:6px;margin:4px 0;color:#93c5fd;font-size:12.5px;}

/* Risk bars */
.rb-wrap{background:#0d1c33;border-radius:10px;padding:16px 18px;margin-bottom:10px;}
.rb-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;}
.rb-name{font-size:12.5px;color:#8aaac8;}
.rb-sc{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;}
.rb-sub{font-size:10.5px;color:#3d5a78;margin-bottom:5px;}
.rb-bg{background:#1a2b45;border-radius:99px;height:7px;}
.rb-fill{height:7px;border-radius:99px;}

/* Page header */
.ph{display:flex;align-items:center;gap:14px;margin-bottom:22px;
  padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,.05);}
.ph-dot{width:40px;height:40px;background:#388bfd;border-radius:10px;
  display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
.ph-title{font-size:26px;font-weight:800;color:#e4eefb;letter-spacing:-.02em;}
.ph-sub{font-size:11.5px;color:#2e4a68;font-family:'JetBrains Mono',monospace;margin-top:2px;}

.badge-h{background:#f87171;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:99px;}
.badge-m{background:#fbbf24;color:#1a1a00;font-size:10px;font-weight:700;padding:2px 7px;border-radius:99px;}
.badge-l{background:#34d399;color:#001a0a;font-size:10px;font-weight:700;padding:2px 7px;border-radius:99px;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
COLORS  = ["#388bfd","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c","#22d3ee","#e879f9","#84cc16","#06b6d4"]
BG      = "#07111f"
PLOT_BG = "#0a1525"
GRID    = "rgba(255,255,255,0.05)"
FC      = "#6a8cac"

NHOM_SP = [
    ("Ống HDPE",        r"HDPE"),
    ("Ống PVC nước",    r"PVC.*(?:nước|nong dài|nong trơn|thoát nước)"),
    ("Ống PVC bơm cát", r"PVC.*(?:cát|bơm cát)"),
    ("Ống PPR",         r"PPR"),
    ("Lõi PVC",         r"(?:Lơi|Lõi|lori)"),
    ("Phụ kiện & Keo",  r"(?:Nối|Co |Tê |Van |Keo |Măng|Bít|Nắp|Hộp nối|Y PVC|Y PPR|Co\()"),
    ("Ống thép/HDPE đặc biệt", r"(?:thép|bích|flanges|PN\d)"),
]

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def playout(fig, title="", h=380):
    fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
        font=dict(family="Be Vietnam Pro", color=FC, size=11),
        title=dict(text=title, font=dict(size=13, color="#c0d4ee"), x=0.01),
        height=h,
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
        margin=dict(l=10,r=10,t=40 if title else 10,b=10),
        xaxis=dict(gridcolor=GRID, showline=False, tickfont_size=10),
        yaxis=dict(gridcolor=GRID, showline=False, tickfont_size=10),
    )
    return fig

def fmt(v, unit=""):
    try:
        v=float(v)
        s = f"{v/1e9:.2f} Tỷ" if abs(v)>=1e9 else f"{v/1e6:.1f} Tr" if abs(v)>=1e6 else f"{v/1e3:.0f}K" if abs(v)>=1e3 else f"{v:,.0f}"
        return s+unit
    except: return str(v)

def kpi(col, accent, icon, label, value):
    col.markdown(f"""
    <div class="kpi-card" style="--ac:{accent}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-v">{value}</div>
        <div class="kpi-l">{label}</div>
    </div>""", unsafe_allow_html=True)

def sec(txt): st.markdown(f'<div class="sec">{txt}</div>', unsafe_allow_html=True)
def alert(lvl, txt): st.markdown(f'<div class="al-{lvl}">{txt}</div>', unsafe_allow_html=True)

def find_header(fb):
    try:
        raw=pd.read_excel(io.BytesIO(fb),header=None,engine="openpyxl",nrows=40)
    except: return 0
    kws=["khách hàng","số chứng từ","tên hàng","ngày chứng từ","mã nhóm","thành tiền bán"]
    for i in range(raw.shape[0]):
        vals=["" if (isinstance(v,float) and pd.isna(v)) else str(v) for v in raw.iloc[i].tolist()]
        if sum(1 for k in kws if k in " ".join(vals).lower())>=2: return i
    return 0

# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""<div class="ph" style="margin-bottom:16px;padding-bottom:12px;">
        <div class="ph-dot">🏗️</div>
        <div><div style="font-size:13px;font-weight:700;color:#e4eefb;">PKD Dự Án Analytics</div>
        <div style="font-size:10px;color:#2e4a68;">Hoa Sen Group</div></div></div>""",
        unsafe_allow_html=True)
    uploaded = st.file_uploader("📂 Upload Excel báo cáo", type=["xlsx"], accept_multiple_files=True)

if not uploaded:
    st.markdown("""<div style="display:flex;flex-direction:column;align-items:center;
        justify-content:center;height:65vh;gap:14px;text-align:center;">
        <div style="font-size:60px;">🏗️</div>
        <div style="font-size:24px;font-weight:800;color:#e4eefb;">PKD Dự Án Analytics</div>
        <div style="font-size:13px;color:#2e4a68;">Upload file Excel báo cáo bán hàng để bắt đầu phân tích</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  LOAD & PROCESS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="⏳ Đang xử lý dữ liệu…")
def load(file_data):
    frames=[]
    for name,fb in file_data:
        try:
            hr=find_header(fb)
            d=pd.read_excel(io.BytesIO(fb),header=hr,engine="openpyxl")
            d.columns=[str(c).strip().replace("\n"," ") for c in d.columns]
            d=d.loc[:,~d.columns.str.startswith("Unnamed")].dropna(how="all")
            d["_src"]=name; frames.append(d)
        except Exception as e: st.warning(f"⚠️ `{name}`: {e}")
    if not frames: return pd.DataFrame()
    df=pd.concat(frames,ignore_index=True)

    # ── Cột bắt buộc
    for col in ["Ngày chứng từ","Tên khách hàng","Thành tiền bán"]:
        if col not in df.columns:
            st.error(f"❌ Thiếu cột '{col}'"); return pd.DataFrame()

    # ── Số hoá
    num=["Thành tiền bán","Thành tiền vốn","Lợi nhuận","Khối lượng","Số lượng",
         "Giá bán","Giá vốn","Đơn giá quy đổi","Đơn giá vận chuyển"]
    for c in num:
        df[c]=pd.to_numeric(df.get(c,0),errors="coerce").fillna(0)

    # ── Ngày
    df["Ngày chứng từ"]=pd.to_datetime(df["Ngày chứng từ"],dayfirst=True,errors="coerce")
    df=df[df["Ngày chứng từ"].notna()].copy()
    df["Nam"]   =df["Ngày chứng từ"].dt.year.astype(str)
    df["Quy"]   =df["Ngày chứng từ"].dt.to_period("Q").astype(str)
    df["Thang"] =df["Ngày chứng từ"].dt.to_period("M").astype(str)
    df["Thang_num"]=df["Ngày chứng từ"].dt.month
    df["Cuoi_thang"]=df["Ngày chứng từ"].dt.day>=28

    # ── Loại GD
    gc=df["Ghi chú"].astype(str).str.upper() if "Ghi chú" in df.columns else pd.Series("",index=df.index)
    loai=df["Loại đơn hàng"].astype(str).str.upper() if "Loại đơn hàng" in df.columns else pd.Series("",index=df.index)
    df["Loai_GD"]="Xuất bán"
    df.loc[gc.str.contains(r"NHẬP TRẢ|TRẢ HÀNG",regex=True,na=False),"Loai_GD"]="Trả hàng"
    df.loc[loai.str.contains(r"TRA HANG|HUY HD",regex=True,na=False),"Loai_GD"]="Trả hàng"
    df.loc[gc.str.contains(r"BỔ SUNG|THAY THẾ|BS PKTM",regex=True,na=False),"Loai_GD"]="Xuất bổ sung"
    df.loc[(df["Khối lượng"]<0)&(df["Loai_GD"]=="Xuất bán"),"Loai_GD"]="Nhập lại/Hủy"

    # ── Giá tính theo đúng logic
    # Giá bán (VNĐ/cái) → Thành tiền bán = Giá bán × Số lượng
    df["GB_cai"]=np.where(df["Số lượng"]!=0, df["Thành tiền bán"]/df["Số lượng"], df["Giá bán"])

    # Giá vốn (VNĐ/kg) → Thành tiền vốn = Giá vốn × Khối lượng  (đây là Giá vốn có sẵn)
    df["GV_kg"]=df["Giá vốn"]  # đã là VNĐ/kg

    # Đơn giá bán quy đổi về /kg để so sánh với giá vốn
    df["Don_gia_ban_kg"]=np.where(df["Khối lượng"]!=0, df["Thành tiền bán"]/df["Khối lượng"], 0)

    # Margin/kg = giá bán/kg - giá vốn/kg
    df["Margin_kg"]=df["Don_gia_ban_kg"]-df["GV_kg"]
    df["Margin_kg_pct"]=np.where(df["Don_gia_ban_kg"]!=0,
                                   df["Margin_kg"]/df["Don_gia_ban_kg"]*100, 0)

    # Biên LN chính thức = LN / TTBán
    df["Bien_LN"]=np.where(df["Thành tiền bán"]!=0,
                            df["Lợi nhuận"]/df["Thành tiền bán"]*100, 0)

    # ── Z-score giá bán/cái theo SP (phát hiện bất thường)
    df_valid_gb=df[(df["Số lượng"]>0)&(df["GB_cai"]>0)].copy()
    z_gb=df_valid_gb.groupby("Tên hàng")["GB_cai"].transform(
        lambda x: (x-x.mean())/(x.std()+1e-9))
    df.loc[df_valid_gb.index,"Z_giaban"]=z_gb

    # ── Z-score giá vốn/kg theo SP
    df_valid_gv=df[(df["Khối lượng"]>0)&(df["GV_kg"]>0)].copy()
    z_gv=df_valid_gv.groupby("Tên hàng")["GV_kg"].transform(
        lambda x: (x-x.mean())/(x.std()+1e-9))
    df.loc[df_valid_gv.index,"Z_giavon"]=z_gv

    # ── Giảm giá so với TB thị trường (trong dataset)
    sp_mean_gb=df[df["GB_cai"]>0].groupby("Tên hàng")["GB_cai"].mean()
    df["SP_mean_gb"]=df["Tên hàng"].map(sp_mean_gb)
    df["Discount_pct"]=np.where(df["SP_mean_gb"]>0,
        (df["SP_mean_gb"]-df["GB_cai"])/df["SP_mean_gb"]*100, 0)

    # ── Nhóm SP
    ten=df["Tên hàng"].astype(str) if "Tên hàng" in df.columns else pd.Series("",index=df.index)
    df["Nhom_SP"]="Khác"
    for lbl,pat in NHOM_SP:
        df.loc[ten.str.contains(pat,case=False,regex=True,na=False),"Nhom_SP"]=lbl

    # ── Tỉnh giao hàng
    if "Nơi giao hàng" in df.columns:
        tinh=df["Nơi giao hàng"].astype(str).str.extract(
            r'(?:Tỉnh|T\.|TP\s|Thành phố|tỉnh)\s*([A-ZÀ-Ỹa-zà-ỹ\s]+?)(?:,|\.|$)')[0].str.strip()
        df["Tinh"]=tinh.fillna("Khác")
    else: df["Tinh"]="Khác"

    # Mã kho text
    if "Mã kho" in df.columns:
        df["Mã kho"]=df["Mã kho"].astype(str).str.replace(".0","",regex=False).str.strip()

    return df

file_data=[(u.name,u.read()) for u in uploaded]
df_all=load(file_data)
if df_all.empty: st.error("Không có dữ liệu hợp lệ."); st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR FILTERS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p style="font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:#2e4a68;margin:14px 0 6px;">🔍 Bộ lọc</p>', unsafe_allow_html=True)

    pkd_col="Tên nhóm KH" if "Tên nhóm KH" in df_all.columns else "Mã nhóm KH"
    pkd_list=["Tất cả PKD"]+sorted(df_all[pkd_col].dropna().astype(str).unique())
    pkd_sel=st.selectbox("🏢 Phòng Kinh Doanh Dự Án",pkd_list)

    df_pkd=df_all[df_all[pkd_col].astype(str)==pkd_sel].copy() if pkd_sel!="Tất cả PKD" else df_all.copy()

    kh_list=["Tất cả KH"]+sorted(df_pkd["Tên khách hàng"].dropna().astype(str).unique())
    kh_sel=st.selectbox("👤 Khách hàng",kh_list)

    df_scope=df_pkd[df_pkd["Tên khách hàng"].astype(str)==kh_sel].copy() if kh_sel!="Tất cả KH" else df_pkd.copy()

    quy_list=sorted(df_scope["Quy"].dropna().unique())
    quy_sel=st.multiselect("📅 Quý",quy_list,default=quy_list)
    df_scope=df_scope[df_scope["Quy"].isin(quy_sel)].copy()

    thang_list=sorted(df_scope["Thang"].dropna().unique())
    thang_sel=st.multiselect("📆 Tháng",thang_list,default=thang_list)
    df_scope=df_scope[df_scope["Thang"].isin(thang_sel)].copy()

    st.markdown("---")
    st.markdown(f'<p style="font-size:10px;color:#2e4a68;">{len(df_scope):,} dòng · {df_scope["Thang"].nunique()} tháng</p>', unsafe_allow_html=True)

df_ban=df_scope[df_scope["Loai_GD"]=="Xuất bán"].copy()

# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════
ngmin=df_scope["Ngày chứng từ"].min(); ngmax=df_scope["Ngày chứng từ"].max()
scope_name=kh_sel if kh_sel!="Tất cả KH" else pkd_sel
st.markdown(f"""<div class="ph">
    <div class="ph-dot">🏗️</div>
    <div>
        <div class="ph-title">{scope_name}</div>
        <div class="ph-sub">{ngmin.strftime('%d/%m/%Y') if pd.notna(ngmin) else '?'} → {ngmax.strftime('%d/%m/%Y') if pd.notna(ngmax) else '?'} &nbsp;·&nbsp; PKD Dự Án Analytics</div>
    </div>
</div>""", unsafe_allow_html=True)

if df_ban.empty:
    st.warning("⚠️ Không có dữ liệu xuất bán."); st.stop()

# KPI ROW
tong_dt=df_ban["Thành tiền bán"].sum()
tong_ln=df_ban["Lợi nhuận"].sum()
tong_kl=df_ban["Khối lượng"].sum()/1000
tong_sl=df_ban["Số lượng"].sum()
bien_ln=(tong_ln/tong_dt*100) if tong_dt else 0
n_duan=df_ban["Số ĐH"].nunique() if "Số ĐH" in df_ban.columns else 0

# Biên margin/kg trung bình (đúng logic)
df_ban_kl=df_ban[df_ban["Khối lượng"]>0]
margin_kg_tb=df_ban_kl["Margin_kg"].mean() if len(df_ban_kl) else 0

st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
c1,c2,c3,c4,c5,c6=st.columns(6)
kpi(c1,"#388bfd","💰","Doanh thu",fmt(tong_dt))
kpi(c2,"#34d399","💹","Lợi nhuận",fmt(tong_ln))
kpi(c3,"#fbbf24","📊","Biên LN %",f"{bien_ln:.1f}%")
kpi(c4,"#a78bfa","⚖️","KL (tấn)",f"{tong_kl:,.1f}")
kpi(c5,"#22d3ee","📦","Số lượng (cái)",f"{int(tong_sl):,}")
kpi(c6,"#fb923c","🏗️","Số dự án/ĐH",f"{n_duan}")
st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════
t1,t2,t3,t4,t5=st.tabs([
    "📦 Thói quen & Dự án",
    "📈 Doanh thu & Sản lượng",
    "💹 Lợi nhuận & Giá",
    "🚚 Giao hàng",
    "⚠️ Rủi ro & Bất thường",
])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 – THÓI QUEN & DỰ ÁN
# ══════════════════════════════════════════════════════════════════════════════
with t1:
    sec("📋 Loại hình công trình dự án")
    if "Loại hình kinh doanh" in df_ban.columns:
        df_loai=(df_ban.groupby("Loại hình kinh doanh")
                 .agg(N=("Số chứng từ","nunique") if "Số chứng từ" in df_ban.columns else ("Thành tiền bán","count"),
                      DT=("Thành tiền bán","sum"),
                      KL=("Khối lượng",lambda x:x.sum()/1000))
                 .reset_index().sort_values("DT",ascending=False))
        c1,c2=st.columns([1.5,1])
        with c1:
            fig=px.bar(df_loai,y="Loại hình kinh doanh",x="DT",orientation="h",
                       color="DT",color_continuous_scale=[[0,"#1a2b45"],[1,"#388bfd"]],
                       text=df_loai["DT"].apply(fmt),labels={"DT":"Doanh thu","Loại hình kinh doanh":""})
            fig.update_traces(textposition="outside",textfont_size=10)
            fig.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
            playout(fig,"Doanh thu theo Loại hình Công trình",h=300)
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            fig2=px.pie(df_loai,names="Loại hình kinh doanh",values="DT",hole=0.55,
                        color_discrete_sequence=COLORS)
            fig2.update_traces(textposition="inside",textinfo="percent",textfont_size=10)
            playout(fig2,"Tỷ trọng",h=300); st.plotly_chart(fig2,use_container_width=True)

    # Top dự án
    sec("🏆 Top dự án (Số ĐH) – DT & Biên LN")
    if "Số ĐH" in df_ban.columns:
        agg_duan=(df_ban.groupby("Số ĐH")
                  .agg(KH=("Tên khách hàng","first"),
                       Loai=("Loại hình kinh doanh","first") if "Loại hình kinh doanh" in df_ban.columns else ("Tên khách hàng","first"),
                       DT=("Thành tiền bán","sum"),
                       Von=("Thành tiền vốn","sum"),
                       LN=("Lợi nhuận","sum"),
                       KL_tan=("Khối lượng",lambda x:round(x.sum()/1000,1)),
                       SL=("Số lượng","sum"),
                       N_SP=("Tên hàng","nunique"),
                       Ngay_bd=("Ngày chứng từ","min"),
                       Ngay_kt=("Ngày chứng từ","max"))
                  .reset_index())
        agg_duan["Bien_%"]=(agg_duan["LN"]/agg_duan["DT"].replace(0,np.nan)*100).round(1).fillna(0)
        agg_duan["Margin_kg_avg"]=np.where(agg_duan["KL_tan"]>0,
            (agg_duan["LN"]/agg_duan["KL_tan"]/1000).round(0),0)
        agg_duan["Thoi_gian"]=(agg_duan["Ngay_kt"]-agg_duan["Ngay_bd"]).dt.days.apply(lambda x:f"{x}d")
        agg_duan=agg_duan.sort_values("DT",ascending=False)

        top_n=st.slider("Số dự án hiển thị",5,30,15,key="sl_duan")
        df_td=agg_duan.head(top_n)
        fig_d=px.bar(df_td,x="Số ĐH",y="DT",color="Bien_%",
                     color_continuous_scale="RdYlGn",
                     hover_data={"KH":True,"Loai":True,"KL_tan":True,"Bien_%":True,"Thoi_gian":True},
                     labels={"DT":"Doanh thu","Bien_%":"Biên LN%"})
        fig_d.update_layout(xaxis_tickangle=-35,xaxis_tickfont_size=9)
        playout(fig_d,f"Top {top_n} dự án – Doanh thu (màu = Biên LN%)",h=380)
        st.plotly_chart(fig_d,use_container_width=True)

        show=["Số ĐH","KH","Loai","DT","LN","Bien_%","KL_tan","SL","N_SP","Thoi_gian"]
        show=[c for c in show if c in df_td.columns]
        df_td_s=df_td[show].copy()
        df_td_s["DT"]=df_td_s["DT"].apply(fmt); df_td_s["LN"]=df_td_s["LN"].apply(fmt)
        st.dataframe(df_td_s.rename(columns={"KH":"Khách hàng","Loai":"Loại hình","Bien_%":"Biên LN%",
                                               "KL_tan":"KL(tấn)","SL":"SL(cái)","N_SP":"#SP","Thoi_gian":"Thời gian"}),
                     use_container_width=True,hide_index=True)

    # SP quan trọng
    sec("📦 Mặt hàng quan trọng – Khối lượng & Doanh thu")
    c1,c2=st.columns(2)
    with c1:
        if "Tên hàng" in df_ban.columns:
            df_sp=(df_ban.groupby("Tên hàng")
                   .agg(KL=("Khối lượng",lambda x:round(x.sum()/1000,2)),
                        DT=("Thành tiền bán","sum"),
                        SL=("Số lượng","sum"))
                   .reset_index().sort_values("KL",ascending=False).head(12))
            fig3=px.bar(df_sp,y="Tên hàng",x="KL",orientation="h",color="KL",
                        color_continuous_scale=[[0,"#1a2b45"],[1,"#34d399"]],
                        text=df_sp["KL"].apply(lambda v:f"{v:.0f}T"),
                        labels={"KL":"KL (tấn)","Tên hàng":""})
            fig3.update_traces(textposition="outside",textfont_size=10)
            fig3.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
            playout(fig3,"Top 12 SP – Khối lượng (tấn)",h=360); st.plotly_chart(fig3,use_container_width=True)
    with c2:
        df_nhom=(df_ban.groupby("Nhom_SP")
                 .agg(KL=("Khối lượng",lambda x:round(x.sum()/1000,1)),
                      DT=("Thành tiền bán","sum"),
                      N=("Nhom_SP","count"))
                 .reset_index().sort_values("DT",ascending=False))
        fig4=px.pie(df_nhom,names="Nhom_SP",values="DT",hole=0.5,color_discrete_sequence=COLORS)
        fig4.update_traces(textposition="inside",textinfo="percent+label",textfont_size=10)
        playout(fig4,"Tỷ trọng DT theo Nhóm SP",h=360); st.plotly_chart(fig4,use_container_width=True)

    # Heatmap thời điểm mua
    sec("📅 Heatmap – thời điểm mua hàng nhiều nhất (KL tấn)")
    if "Tên hàng" in df_ban.columns:
        top6_sp=df_ban.groupby("Tên hàng")["Khối lượng"].sum().nlargest(8).index.tolist()
        df_hm=(df_ban[df_ban["Tên hàng"].isin(top6_sp)]
               .groupby(["Tên hàng","Thang"])["Khối lượng"].sum()/1000).reset_index()
        df_piv=df_hm.pivot(index="Tên hàng",columns="Thang",values="Khối lượng").fillna(0)
        if not df_piv.empty:
            fig_h=go.Figure(go.Heatmap(z=df_piv.values,x=list(df_piv.columns),
                                        y=list(df_piv.index),colorscale="Blues",
                                        text=np.round(df_piv.values,1),texttemplate="%{text}T",
                                        textfont_size=9,hoverongaps=False))
            fig_h.update_layout(plot_bgcolor=PLOT_BG,paper_bgcolor=PLOT_BG,
                                  font_color=FC,height=280,margin=dict(l=10,r=10,t=10,b=10),
                                  xaxis_tickfont_size=10,yaxis_tickfont_size=10)
            st.plotly_chart(fig_h,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 – DOANH THU & SẢN LƯỢNG
# ══════════════════════════════════════════════════════════════════════════════
with t2:
    sec("📈 Biến động theo tháng – Doanh thu, KL, Biên LN")
    df_m=(df_ban.groupby("Thang")
          .agg(DT=("Thành tiền bán","sum"),
               KL=("Khối lượng",lambda x:x.sum()/1000),
               SL=("Số lượng","sum"),
               LN=("Lợi nhuận","sum"),
               N_DH=("Số ĐH","nunique") if "Số ĐH" in df_ban.columns else ("Thành tiền bán","count"))
          .reset_index().sort_values("Thang"))
    df_m["Bien_%"]=(df_m["LN"]/df_m["DT"].replace(0,np.nan)*100).round(1).fillna(0)
    df_m["KL_prev"]=df_m["KL"].shift(1)
    df_m["KL_mom"]= ((df_m["KL"]-df_m["KL_prev"])/df_m["KL_prev"]*100).round(1)
    df_m["DT_prev"]=df_m["DT"].shift(1)
    df_m["DT_mom"]= ((df_m["DT"]-df_m["DT_prev"])/df_m["DT_prev"]*100).round(1)

    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,
        subplot_titles=("① Doanh thu (VNĐ) & Khối lượng (tấn)",
                        "② Số lượng (cái) & Số Đơn hàng",
                        "③ Biên LN (%) & Tăng trưởng KL MoM (%)"),
        vertical_spacing=0.08,row_heights=[0.4,0.3,0.3])
    fig.add_trace(go.Bar(x=df_m["Thang"],y=df_m["DT"],name="Doanh thu",
                          marker_color="#388bfd",opacity=0.85,
                          text=df_m["DT"].apply(fmt),textposition="outside",textfont_size=9),row=1,col=1)
    fig.add_trace(go.Scatter(x=df_m["Thang"],y=df_m["KL"],name="KL (tấn)",
                              mode="lines+markers",line=dict(color="#34d399",width=2.5),
                              marker_size=6,yaxis="y2"),row=1,col=1)
    fig.add_trace(go.Bar(x=df_m["Thang"],y=df_m["SL"],name="SL (cái)",
                          marker_color="#a78bfa",opacity=0.8),row=2,col=1)
    fig.add_trace(go.Scatter(x=df_m["Thang"],y=df_m["N_DH"],name="Số ĐH",
                              mode="lines+markers",line=dict(color="#fbbf24",width=2)),row=2,col=1)
    fig.add_trace(go.Scatter(x=df_m["Thang"],y=df_m["Bien_%"],name="Biên LN%",
                              mode="lines+markers+text",
                              text=[f"{v:.1f}%" for v in df_m["Bien_%"]],
                              textposition="top center",textfont_size=9,
                              line=dict(color="#f87171",width=2)),row=3,col=1)
    fig.add_trace(go.Bar(x=df_m["Thang"],y=df_m["KL_mom"],name="KL MoM%",
                          marker_color=[("#f87171" if v<0 else "#34d399") for v in df_m["KL_mom"].fillna(0)],
                          opacity=0.6),row=3,col=1)
    fig.update_layout(plot_bgcolor=PLOT_BG,paper_bgcolor=PLOT_BG,
                       font=dict(family="Be Vietnam Pro",color=FC,size=11),
                       height=640,legend=dict(orientation="h",y=-0.06,bgcolor="rgba(0,0,0,0)"),
                       margin=dict(l=10,r=10,t=36,b=10))
    for ax in ["xaxis","xaxis2","xaxis3","yaxis","yaxis2","yaxis3","yaxis4","yaxis5","yaxis6"]:
        fig.update_layout(**{ax:dict(gridcolor=GRID,showline=False)})
    st.plotly_chart(fig,use_container_width=True)

    # Phát hiện tháng đột biến
    sec("⚡ Phát hiện tháng Sản lượng bất thường")
    mean_kl=df_m["KL"].mean(); std_kl=df_m["KL"].std() or 1
    for _,r in df_m.iterrows():
        z=(r["KL"]-mean_kl)/std_kl
        mom=r["KL_mom"]
        if z>1.5:
            alert("h",f"🔺 <b>{r['Thang']}</b>: KL = <b>{r['KL']:,.0f} tấn</b> — cao hơn TB {z:.1f}σ | MoM: {mom:+.1f}% → Kiểm tra đơn hàng dự án lớn, có thể đẩy doanh số")
        elif z<-1.5:
            alert("m",f"🔻 <b>{r['Thang']}</b>: KL = <b>{r['KL']:,.0f} tấn</b> — thấp hơn TB {abs(z):.1f}σ | MoM: {mom:+.1f}% → Kiểm tra tiến độ dự án, khách chậm nhận hàng")
        elif mom is not np.nan and abs(mom)>40:
            alert("m",f"📊 <b>{r['Thang']}</b>: Tăng trưởng KL MoM = <b>{mom:+.1f}%</b> — biến động lớn cần xem lại")

    # Bảng & Quý
    sec("📊 Tổng hợp theo Quý")
    df_q=(df_ban.groupby("Quy")
          .agg(DT=("Thành tiền bán","sum"),
               KL=("Khối lượng",lambda x:round(x.sum()/1000,1)),
               LN=("Lợi nhuận","sum"),
               N_DH=("Số ĐH","nunique") if "Số ĐH" in df_ban.columns else ("Thành tiền bán","count"),
               N_KH=("Tên khách hàng","nunique"))
          .reset_index())
    df_q["Bien_%"]=(df_q["LN"]/df_q["DT"].replace(0,np.nan)*100).round(1).fillna(0)
    c1,c2=st.columns(2)
    with c1:
        fig_q=px.bar(df_q,x="Quy",y="DT",color="Bien_%",color_continuous_scale="RdYlGn",
                     text=df_q["DT"].apply(fmt),labels={"DT":"Doanh thu","Bien_%":"Biên LN%","Quy":"Quý"})
        fig_q.update_traces(textposition="outside",textfont_size=10)
        playout(fig_q,"Doanh thu theo Quý (màu = Biên LN%)",h=280); st.plotly_chart(fig_q,use_container_width=True)
    with c2:
        df_q_s=df_q.copy()
        df_q_s["DT"]=df_q_s["DT"].apply(fmt); df_q_s["LN"]=df_q_s["LN"].apply(fmt)
        df_q_s.columns=["Quý","Doanh thu","KL(tấn)","Lợi nhuận","Số ĐH","Số KH","Biên LN(%)"]
        st.dataframe(df_q_s,use_container_width=True,hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 – LỢI NHUẬN & GIÁ
# ══════════════════════════════════════════════════════════════════════════════
with t3:
    sec("💹 Biên lợi nhuận – đúng theo logic giá")
    alert("i","📌 <b>Logic tính giá:</b> Giá bán (VNĐ/cái) × Số lượng = Thành tiền bán &nbsp;|&nbsp; Giá vốn (VNĐ/kg) × Khối lượng = Thành tiền vốn &nbsp;|&nbsp; Margin/kg = (Thành tiền bán ÷ KL) − Giá vốn")

    # Biên LN theo tháng
    df_ln_m=(df_ban.groupby("Thang")
             .agg(DT=("Thành tiền bán","sum"),Von=("Thành tiền vốn","sum"),LN=("Lợi nhuận","sum"))
             .reset_index().sort_values("Thang"))
    df_ln_m["Bien_%"]=(df_ln_m["LN"]/df_ln_m["DT"].replace(0,np.nan)*100).round(2).fillna(0)

    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,
        subplot_titles=("DT / Vốn / LN (VNĐ)","Biên LN (%)"),
        vertical_spacing=0.12,row_heights=[0.6,0.4])
    fig.add_trace(go.Bar(x=df_ln_m["Thang"],y=df_ln_m["DT"],name="Doanh thu",marker_color="#388bfd"),row=1,col=1)
    fig.add_trace(go.Bar(x=df_ln_m["Thang"],y=df_ln_m["Von"],name="Giá vốn",marker_color="#f87171"),row=1,col=1)
    fig.add_trace(go.Scatter(x=df_ln_m["Thang"],y=df_ln_m["LN"],name="Lợi nhuận",
                              mode="lines+markers",line=dict(color="#34d399",width=2.5)),row=1,col=1)
    fig.add_trace(go.Scatter(x=df_ln_m["Thang"],y=df_ln_m["Bien_%"],name="Biên LN%",
                              mode="lines+markers+text",
                              text=[f"{v:.1f}%" for v in df_ln_m["Bien_%"]],
                              textposition="top center",textfont_size=9,
                              line=dict(color="#fbbf24",width=2.5)),row=2,col=1)
    fig.update_layout(plot_bgcolor=PLOT_BG,paper_bgcolor=PLOT_BG,
                       font=dict(family="Be Vietnam Pro",color=FC,size=11),
                       height=500,barmode="group",legend=dict(orientation="h",y=-0.08,bgcolor="rgba(0,0,0,0)"),
                       margin=dict(l=10,r=10,t=36,b=10))
    st.plotly_chart(fig,use_container_width=True)

    # Biên LN bất thường
    sec("🔍 Kỳ nghi có chiết khấu / chính sách giá đặc biệt")
    mb=df_ln_m["Bien_%"].mean(); sb=df_ln_m["Bien_%"].std() or 1
    found_anom=False
    for _,r in df_ln_m.iterrows():
        z=(r["Bien_%"]-mb)/sb
        if z<-1.8:
            alert("h",f"🔴 <b>{r['Thang']}</b>: Biên LN = <b>{r['Bien_%']:.1f}%</b> (TB: {mb:.1f}%, Z={z:.1f}) → Nghi chiết khấu lớn hoặc giá đặc biệt")
            found_anom=True
        elif z<-1.2:
            alert("m",f"🟡 <b>{r['Thang']}</b>: Biên LN = <b>{r['Bien_%']:.1f}%</b> (TB: {mb:.1f}%, Z={z:.1f}) → Cần kiểm tra chính sách đợt này")
            found_anom=True
    if not found_anom:
        alert("l","✅ Biên LN ổn định qua các kỳ, không có tháng bất thường")

    # Margin/kg theo nhóm SP
    sec("⚙️ Margin/kg (VNĐ) – So sánh Giá bán/kg vs Giá vốn/kg")
    df_mgsp=(df_ban[df_ban["Khối lượng"]>0]
             .groupby("Nhom_SP")
             .agg(GV_kg_avg=("GV_kg","mean"),
                  Don_gia_ban_kg=("Don_gia_ban_kg","mean"),
                  Margin_kg=("Margin_kg","mean"),
                  Margin_pct=("Margin_kg_pct","mean"))
             .reset_index().round(0))
    c1,c2=st.columns(2)
    with c1:
        fig_mg=go.Figure()
        fig_mg.add_trace(go.Bar(name="Giá bán/kg (VNĐ)",x=df_mgsp["Nhom_SP"],y=df_mgsp["Don_gia_ban_kg"],marker_color="#388bfd",opacity=0.85))
        fig_mg.add_trace(go.Bar(name="Giá vốn/kg (VNĐ)",x=df_mgsp["Nhom_SP"],y=df_mgsp["GV_kg_avg"],marker_color="#f87171",opacity=0.85))
        fig_mg.update_layout(barmode="group")
        playout(fig_mg,"Giá bán/kg vs Giá vốn/kg theo Nhóm SP",h=320)
        st.plotly_chart(fig_mg,use_container_width=True)
    with c2:
        fig_mp=px.bar(df_mgsp.sort_values("Margin_pct",ascending=False),
                      x="Nhom_SP",y="Margin_pct",color="Margin_pct",
                      color_continuous_scale="RdYlGn",text=df_mgsp.sort_values("Margin_pct",ascending=False)["Margin_pct"].apply(lambda v:f"{v:.1f}%"),
                      labels={"Margin_pct":"Margin/kg %","Nhom_SP":""})
        fig_mp.update_traces(textposition="outside",textfont_size=10)
        fig_mp.update_layout(coloraxis_showscale=False)
        playout(fig_mp,"Margin/kg (%) theo Nhóm SP",h=320)
        st.plotly_chart(fig_mp,use_container_width=True)

    # Biên LN theo dự án
    if "Số ĐH" in df_ban.columns:
        sec("🏗️ Biên LN từng dự án – Scatter DT vs Biên%")
        df_ld=(df_ban.groupby("Số ĐH")
               .agg(KH=("Tên khách hàng","first"),
                    DT=("Thành tiền bán","sum"),LN=("Lợi nhuận","sum"),
                    KL=("Khối lượng",lambda x:round(x.sum()/1000,1)))
               .reset_index())
        df_ld["Bien_%"]=(df_ld["LN"]/df_ld["DT"].replace(0,np.nan)*100).round(1).fillna(0)
        fig_sc=px.scatter(df_ld,x="DT",y="Bien_%",size="KL",color="Bien_%",
                          hover_data={"KH":True,"KL":True},
                          color_continuous_scale="RdYlGn",
                          labels={"DT":"Doanh thu","Bien_%":"Biên LN%","KL":"KL(tấn)"})
        fig_sc.add_hline(y=df_ld["Bien_%"].mean(),line_dash="dash",line_color="#fbbf24",
                          annotation_text=f"TB: {df_ld['Bien_%'].mean():.1f}%",
                          annotation_font_color="#fbbf24")
        fig_sc.add_hline(y=0,line_color="#f87171",line_width=1)
        playout(fig_sc,"Scatter: Doanh thu vs Biên LN% (kích thước = KL tấn)",h=400)
        st.plotly_chart(fig_sc,use_container_width=True)

        # Dự án LN âm
        sec("❗ Dự án Lợi nhuận âm")
        df_lnam=df_ld[df_ld["LN"]<0].sort_values("LN")
        if not df_lnam.empty:
            for _,r in df_lnam.head(8).iterrows():
                alert("h",f"🔴 <b>{r['Số ĐH']}</b> | {r.get('KH','?')[:40]} | DT: {fmt(r['DT'])} | LN: <b>{fmt(r['LN'])}</b> | Biên: {r['Bien_%']:.1f}%")
        else:
            alert("l","✅ Không có dự án nào lợi nhuận âm.")

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 – GIAO HÀNG
# ══════════════════════════════════════════════════════════════════════════════
with t4:
    sec("🚚 Điều kiện & Phương tiện giao hàng")
    c1,c2=st.columns(2)
    with c1:
        if "Freight Terms" in df_ban.columns:
            ft=df_ban["Freight Terms"].value_counts().reset_index(); ft.columns=["Hình thức","N"]
            fig_ft=px.pie(ft,names="Hình thức",values="N",hole=0.55,color_discrete_sequence=COLORS)
            fig_ft.update_traces(textposition="inside",textinfo="percent+label",textfont_size=10)
            playout(fig_ft,"Điều kiện giao hàng",h=280); st.plotly_chart(fig_ft,use_container_width=True)
    with c2:
        if "Shipping method" in df_ban.columns:
            sm=df_ban["Shipping method"].value_counts().reset_index(); sm.columns=["PT","N"]
            fig_sm=px.pie(sm,names="PT",values="N",hole=0.55,color_discrete_sequence=COLORS[2:])
            fig_sm.update_traces(textposition="inside",textinfo="percent+label",textfont_size=10)
            playout(fig_sm,"Phương tiện vận chuyển",h=280); st.plotly_chart(fig_sm,use_container_width=True)

    sec("📍 Top tỉnh/TP nhận hàng – quan trọng với PKD Dự án")
    df_tinh=(df_ban.groupby("Tinh")
             .agg(N=("Tinh","count"),KL=("Khối lượng",lambda x:round(x.sum()/1000,1)),
                  DT=("Thành tiền bán","sum"))
             .reset_index().sort_values("KL",ascending=False))
    df_tinh=df_tinh[df_tinh["Tinh"].str.len()>2].head(20)
    c1,c2=st.columns([1.6,1])
    with c1:
        fig_t=px.bar(df_tinh.head(15),y="Tinh",x="KL",orientation="h",color="KL",
                     color_continuous_scale=[[0,"#1a2b45"],[1,"#388bfd"]],
                     text=df_tinh.head(15)["KL"].apply(lambda v:f"{v:.0f}T"),
                     labels={"KL":"KL(tấn)","Tinh":""})
        fig_t.update_traces(textposition="outside",textfont_size=10)
        fig_t.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
        playout(fig_t,"Top 15 Tỉnh/TP theo Khối lượng",h=400); st.plotly_chart(fig_t,use_container_width=True)
    with c2:
        fig_tp=px.pie(df_tinh.head(10),names="Tinh",values="DT",hole=0.5,color_discrete_sequence=COLORS)
        fig_tp.update_traces(textposition="inside",textinfo="percent",textfont_size=10)
        playout(fig_tp,"Top 10 Tỉnh – Tỷ trọng DT",h=400); st.plotly_chart(fig_tp,use_container_width=True)

    sec("🗺️ Địa điểm giao theo Dự án")
    if "Số ĐH" in df_ban.columns and "Nơi giao hàng" in df_ban.columns:
        df_gh=(df_ban.groupby(["Số ĐH","Nơi giao hàng"])
               .agg(KH=("Tên khách hàng","first"),
                    KL=("Khối lượng",lambda x:round(x.sum()/1000,2)),
                    DT=("Thành tiền bán","sum"))
               .reset_index().sort_values("DT",ascending=False))
        df_gh["DT"]=df_gh["DT"].apply(fmt)
        with st.expander(f"📋 {len(df_gh)} điểm giao hàng – xem chi tiết"):
            st.dataframe(df_gh.rename(columns={"Số ĐH":"Đơn hàng","KH":"Khách hàng","KL":"KL(tấn)","DT":"Doanh thu"}),
                         use_container_width=True,hide_index=True)

    sec("📦 Chi phí vận chuyển (VNĐ/kg) theo tháng")
    if "Đơn giá vận chuyển" in df_ban.columns:
        df_vc=(df_ban[df_ban["Đơn giá vận chuyển"]>0]
               .groupby("Thang")["Đơn giá vận chuyển"].mean().reset_index())
        fig_vc=px.bar(df_vc,x="Thang",y="Đơn giá vận chuyển",
                      text=df_vc["Đơn giá vận chuyển"].apply(lambda v:f"{v:,.0f}"),
                      color="Đơn giá vận chuyển",color_continuous_scale=[[0,"#1a2b45"],[1,"#fb923c"]],
                      labels={"Đơn giá vận chuyển":"ĐG VC (VNĐ/kg)","Thang":"Tháng"})
        fig_vc.update_traces(textposition="outside",textfont_size=10)
        fig_vc.update_layout(coloraxis_showscale=False)
        playout(fig_vc,"Đơn giá vận chuyển TB (VNĐ/kg) theo tháng",h=280)
        st.plotly_chart(fig_vc,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 – RỦI RO & BẤT THƯỜNG
# ══════════════════════════════════════════════════════════════════════════════
with t5:
    sec("⚠️ Nhận diện Rủi ro & Dấu hiệu Bất thường – Chuyên sâu")
    alert("i","📌 Phân tích 10 nhóm dấu hiệu bất thường dựa trên logic giá đúng: Giá bán/cái × SL = TTBán | Giá vốn/kg × KL = TTVốn | Margin/kg = GB/kg − GV/kg")

    tong_dt_ban=df_ban["Thành tiền bán"].sum()
    tong_ln_ban=df_ban["Lợi nhuận"].sum()
    bien_tb=(tong_ln_ban/tong_dt_ban*100) if tong_dt_ban else 0
    risks=[]  # (name, weight, score, level, detail, df_detail)

    # ── R1: Giá bán/cái bất thường (z-score > 2.5) [10đ]
    anom_gb=df_ban[(df_ban.get("Z_giaban",pd.Series(0,index=df_ban.index)).fillna(0).abs()>2.5)&(df_ban["Giá bán"]>0)]
    n_agb=len(anom_gb); pct_agb=(n_agb/len(df_ban)*100) if len(df_ban) else 0
    s1=min(10,pct_agb*3); lv1="h" if s1>=7 else "m" if s1>=3 else "l"
    risks.append(("💰 Giá bán/cái bất thường (Z>2.5σ)",10,s1,lv1,
                   f"{n_agb} dòng ({pct_agb:.1f}%) giá bán/cái lệch >2.5σ so với cùng SP — chiết khấu bất thường hoặc sai giá",
                   anom_gb[["Ngày chứng từ","Tên khách hàng","Tên hàng","Giá bán","Số lượng","Thành tiền bán","Z_giaban"]].rename(columns={"Z_giaban":"Z-score"}) if not anom_gb.empty else None))

    # ── R2: Giá vốn/kg bất thường (z > 2.5) [10đ]
    anom_gv=df_ban[(df_ban.get("Z_giavon",pd.Series(0,index=df_ban.index)).fillna(0).abs()>2.5)&(df_ban["GV_kg"]>0)]
    n_agv=len(anom_gv); pct_agv=(n_agv/len(df_ban)*100) if len(df_ban) else 0
    s2=min(10,pct_agv*3); lv2="h" if s2>=7 else "m" if s2>=3 else "l"
    risks.append(("🏭 Giá vốn/kg bất thường (Z>2.5σ)",10,s2,lv2,
                   f"{n_agv} dòng ({pct_agv:.1f}%) giá vốn/kg lệch >2.5σ — lô hàng tồn kho cũ, giá nhập sai, hoặc phân bổ chi phí bất thường",
                   anom_gv[["Ngày chứng từ","Tên khách hàng","Tên hàng","GV_kg","Khối lượng","Thành tiền vốn","Z_giavon"]].rename(columns={"GV_kg":"Giá vốn/kg","Z_giavon":"Z-score"}) if not anom_gv.empty else None))

    # ── R3: Margin/kg âm – bán lỗ tính theo kg [20đ]
    df_lo_kg=df_ban[(df_ban["Khối lượng"]>0)&(df_ban["Don_gia_ban_kg"]>0)&(df_ban["Margin_kg"]<0)]
    n_lo=len(df_lo_kg); pct_lo=(n_lo/len(df_ban)*100) if len(df_ban) else 0
    tong_lo=abs(df_lo_kg["Lợi nhuận"].sum())
    s3=min(20,pct_lo*4); lv3="h" if pct_lo>5 else "m" if pct_lo>1 else "l"
    risks.append(("📉 Margin/kg âm (bán lỗ theo kg)",20,s3,lv3,
                   f"{n_lo} dòng ({pct_lo:.1f}%) có GB/kg < GV/kg — tổng thiệt hại: {fmt(tong_lo)} VNĐ | Nguyên nhân: chiết khấu cái lớn nhưng kg ít, hoặc phụ kiện nhỏ bán theo cái rẻ",
                   df_lo_kg[["Ngày chứng từ","Tên khách hàng","Tên hàng","Don_gia_ban_kg","GV_kg","Margin_kg","Lợi nhuận"]].rename(columns={"Don_gia_ban_kg":"GB/kg","GV_kg":"GV/kg"}) if not df_lo_kg.empty else None))

    # ── R4: KH mua giá thấp hơn TB thị trường >15% [15đ]
    df_disc=df_ban[(df_ban.get("Discount_pct",pd.Series(0,index=df_ban.index)).fillna(0)>15)&(df_ban["GB_cai"]>0)]
    n_disc=len(df_disc); tong_disc=df_disc["Thành tiền bán"].sum(); pct_disc=(n_disc/len(df_ban)*100) if len(df_ban) else 0
    s4=min(15,pct_disc*2); lv4="h" if pct_disc>10 else "m" if pct_disc>3 else "l"
    risks.append(("🏷️ Giá bán thấp hơn TB thị trường >15%",15,s4,lv4,
                   f"{n_disc} dòng ({pct_disc:.1f}%) giá bán/cái thấp hơn TB cùng SP >15% — Tổng DT bị ảnh hưởng: {fmt(tong_disc)} VNĐ",
                   df_disc[["Ngày chứng từ","Tên khách hàng","Tên hàng","GB_cai","SP_mean_gb","Discount_pct","Thành tiền bán"]].rename(columns={"GB_cai":"Giá bán/cái","SP_mean_gb":"TB thị trường","Discount_pct":"Giảm%"}) if not df_disc.empty else None))

    # ── R5: Giá vốn bất thường trong cùng 1 đơn hàng [10đ]
    if "Số ĐH" in df_ban.columns:
        df_same_dh=df_ban[(df_ban["GV_kg"]>0)&(df_ban["Khối lượng"]>0)]
        gv_std_dh=df_same_dh.groupby(["Số ĐH","Tên hàng"])["GV_kg"].std().dropna()
        gv_mean_dh=df_same_dh.groupby(["Số ĐH","Tên hàng"])["GV_kg"].mean()
        cv_dh=(gv_std_dh/gv_mean_dh*100).dropna()
        high_cv=cv_dh[cv_dh>10]
        n_hcv=len(high_cv); s5=min(10,n_hcv/10); lv5="h" if n_hcv>20 else "m" if n_hcv>5 else "l"
        risks.append(("🔄 Giá vốn/kg biến động trong cùng 1 ĐH+SP",10,round(s5,1),lv5,
                       f"{n_hcv} cặp (ĐH, SP) có CV Giá vốn >10% — xuất nhiều lô khác giá vốn trong cùng dự án, cần kiểm soát",None))
    else:
        s5=0; lv5="l"
        risks.append(("🔄 Giá vốn/kg biến động trong cùng 1 ĐH+SP",10,0,"l","Không có cột Số ĐH để kiểm tra",None))

    # ── R6: Tập trung đơn cuối tháng [5đ]
    dt_cuoi=df_ban[df_ban["Cuoi_thang"]]["Thành tiền bán"].sum()
    tl_cuoi=(dt_cuoi/tong_dt_ban*100) if tong_dt_ban else 0
    s6=min(5,tl_cuoi/10); lv6="h" if tl_cuoi>40 else "m" if tl_cuoi>25 else "l"
    risks.append(("📅 DT tập trung cuối tháng (28-31)",5,round(s6,1),lv6,
                   f"{tl_cuoi:.1f}% doanh thu rơi vào ngày 28–31 — dấu hiệu đẩy doanh số cuối kỳ, ghi nhận doanh thu sớm",None))

    # ── R7: Trả hàng & nhập lại [15đ]
    df_tra=df_scope[df_scope["Loai_GD"].isin(["Trả hàng","Nhập lại/Hủy"])]
    tong_tra=abs(df_tra["Thành tiền bán"].sum()); tl_tra=(tong_tra/tong_dt_ban*100) if tong_dt_ban else 0
    s7=min(15,tl_tra*1.5); lv7="h" if tl_tra>10 else "m" if tl_tra>3 else "l"
    risks.append(("↩️ Trả hàng / Nhập lại / Hủy đơn",15,round(s7,1),lv7,
                   f"{len(df_tra)} phiếu – Giá trị: {fmt(tong_tra)} VNĐ ({tl_tra:.1f}% DT) — khách đặt nhầm, xuất sai, chất lượng",
                   df_tra[["Ngày chứng từ","Tên khách hàng","Tên hàng","Khối lượng","Thành tiền bán","Ghi chú"]].head(20) if not df_tra.empty else None))

    # ── R8: Biên LN tổng thấp [10đ]
    s8=(10 if bien_tb<5 else 6 if bien_tb<15 else 2 if bien_tb<25 else 0)
    lv8="h" if s8>=8 else "m" if s8>=4 else "l"
    risks.append(("💹 Biên LN tổng thể",10,s8,lv8,f"Biên LN TB = {bien_tb:.1f}% — {'Rất thấp, nguy cơ bán phá giá' if s8>=8 else 'Thấp' if s8>=4 else 'Bình thường'}",None))

    # ── R9: SP có xu hướng giá giảm liên tục [3đ]
    if "Tên hàng" in df_ban.columns:
        df_trend_chk=df_ban[(df_ban["Số lượng"]>0)&(df_ban["GB_cai"]>0)].groupby(["Tên khách hàng","Tên hàng","Thang"])["GB_cai"].mean().reset_index()
        def is_declining(g):
            if len(g)<3: return False
            prices=g.sort_values("Thang")["GB_cai"].values
            diffs=np.diff(prices)
            return (diffs<0).sum()>=len(diffs)*0.75
        n_decl=df_trend_chk.groupby(["Tên khách hàng","Tên hàng"]).apply(is_declining).sum()
        s9=min(3,int(n_decl)/5); lv9="m" if n_decl>10 else "l"
        risks.append(("📉 Cặp KH-SP có giá bán giảm liên tục",3,round(s9,1),lv9,
                       f"{n_decl} cặp KH-SP có giá bán/cái giảm ≥75% số tháng — áp lực cạnh tranh hoặc chiết khấu leo thang",None))
    else:
        risks.append(("📉 Giá bán giảm liên tục",3,0,"l","Không có cột Tên hàng",None))

    # ── R10: Chi phí VC cao bất thường [2đ]
    if "Đơn giá vận chuyển" in df_ban.columns:
        df_vc2=df_ban[df_ban["Đơn giá vận chuyển"]>0]
        q3vc=df_vc2["Đơn giá vận chuyển"].quantile(0.75); iqrvc=q3vc-df_vc2["Đơn giá vận chuyển"].quantile(0.25)
        n_vc_out=len(df_vc2[df_vc2["Đơn giá vận chuyển"]>q3vc+3*iqrvc]) if iqrvc>0 else 0
        s10=min(2,n_vc_out/100); lv10="m" if n_vc_out>50 else "l"
        risks.append(("🚚 Chi phí vận chuyển/kg bất thường",2,round(s10,1),lv10,
                       f"{n_vc_out} dòng ĐG vận chuyển vượt Q3+3×IQR — giao xa, hàng nhỏ lẻ, hoặc tuyến đặc biệt",None))
    else:
        risks.append(("🚚 Chi phí vận chuyển",2,0,"l","Không có dữ liệu",None))

    # ══ TỔNG ĐIỂM ══
    total_w=sum(r[1] for r in risks)  # =100
    total_s=sum(r[2] for r in risks)
    norm=round(total_s/total_w*100) if total_w else 0
    n_h=sum(1 for r in risks if r[3]=="h")
    n_m=sum(1 for r in risks if r[3]=="m")
    n_l=sum(1 for r in risks if r[3]=="l")
    risk_color=("#f87171" if norm>=60 else "#fbbf24" if norm>=30 else "#34d399")
    risk_label=("RỦI RO CAO" if norm>=60 else "RỦI RO TRUNG BÌNH" if norm>=30 else "RỦI RO THẤP")

    st.markdown("---")
    cg,cd=st.columns([1,2])
    with cg:
        fig_g=go.Figure(go.Indicator(
            mode="gauge+number",value=norm,
            number={"font":{"size":52,"color":risk_color,"family":"JetBrains Mono"}},
            gauge={"axis":{"range":[0,100],"tickfont":{"size":10,"color":FC}},
                   "bar":{"color":risk_color},
                   "bgcolor":"#0d1c33","bordercolor":"#1a2b45",
                   "steps":[{"range":[0,30],"color":"#091e12"},
                             {"range":[30,60],"color":"#2d1e0a"},
                             {"range":[60,100],"color":"#30100e"}],
                   "threshold":{"line":{"color":"#fff","width":2},"thickness":0.8,"value":norm}}))
        fig_g.update_layout(paper_bgcolor=PLOT_BG,plot_bgcolor=PLOT_BG,
                             font_color=FC,height=260,margin=dict(l=10,r=10,t=10,b=10),
                             annotations=[dict(text=f"{risk_label}",x=0.5,y=-0.1,showarrow=False,
                                               font=dict(size=13,color=risk_color),xanchor="center")])
        st.plotly_chart(fig_g,use_container_width=True)
        st.markdown(f"""<div style="text-align:center;padding:10px;background:#0d1c33;border-radius:8px;">
            <span style="font-size:12px;color:#4a7aaa;">🔴 {n_h} cao</span>&nbsp;&nbsp;
            <span style="font-size:12px;color:#4a7aaa;">🟡 {n_m} trung bình</span>&nbsp;&nbsp;
            <span style="font-size:12px;color:#4a7aaa;">🟢 {n_l} thấp</span>
        </div>""", unsafe_allow_html=True)

    with cd:
        st.markdown('<div class="rb-wrap">', unsafe_allow_html=True)
        for name,weight,score,lv,detail,_ in risks:
            pct=(score/weight*100) if weight else 0
            bc=("#f87171" if lv=="h" else "#fbbf24" if lv=="m" else "#34d399")
            st.markdown(f"""
            <div style="margin-bottom:13px;">
                <div class="rb-row">
                    <span class="rb-name">{name}</span>
                    <span class="rb-sc" style="color:{bc}">{score:.1f}/{weight}</span>
                </div>
                <div class="rb-sub">{detail}</div>
                <div class="rb-bg"><div class="rb-fill" style="width:{pct:.0f}%;background:{bc};"></div></div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Chi tiết từng rủi ro
    sec("🔍 Chi tiết cảnh báo & Dữ liệu bằng chứng")
    for name,weight,score,lv,detail,df_det in risks:
        alert(lv,f"<b>[{name}]</b> — Điểm: {score:.1f}/{weight} — {detail}")
        if df_det is not None and not df_det.empty and lv in ["h","m"]:
            with st.expander(f"📋 Xem {min(len(df_det),50)} dòng bằng chứng – {name}"):
                d2=df_det.head(50).copy()
                for c in ["Thành tiền bán","Lợi nhuận","Giá bán/cái","GB/kg","GV/kg","Margin_kg","TB thị trường"]:
                    if c in d2.columns:
                        d2[c]=pd.to_numeric(d2[c],errors="coerce").apply(lambda v: f"{v:,.0f}" if pd.notna(v) else "")
                st.dataframe(d2,use_container_width=True,hide_index=True)

    # Công nợ
    sec("🏦 Công nợ (chưa cập nhật)")
    alert("i","""📋 <b>Module Công nợ chưa có dữ liệu.</b> Cần bổ sung:
    <br>&nbsp;&nbsp;• <b>AR Aging Report</b> → ngày tồn đọng, quá hạn từng dự án
    <br>&nbsp;&nbsp;• <b>Lịch sử thanh toán</b> → thói quen NET 30/60/90 ngày
    <br>&nbsp;&nbsp;• <b>Hạn mức tín dụng</b> → so sánh dư nợ vs hạn mức
    <br><b>Nhận xét từ dữ liệu:</b> Đơn hàng có PO/dự án thường TT theo tiến độ công trình, chậm 30–90 ngày; trả hàng kéo dài công nợ""")