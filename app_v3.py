"""
PKD Dự Án Analytics – Hoa Sen Group  v3
Giá bán (VNĐ/cái) × SL = Thành tiền bán
Giá vốn (VNĐ/kg)  × KL = Thành tiền vốn
GB/kg = Thành tiền bán / KL   →  Margin/kg = GB/kg − GV/kg
"""
import io, warnings
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
#  CONFIG & STYLE
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="PKD Dự Án – Hoa Sen", layout="wide",
                   page_icon="🏗️", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Be Vietnam Pro',sans-serif;}

section[data-testid="stSidebar"]{background:#060d1c;border-right:1px solid #0f1f35;}
section[data-testid="stSidebar"] *{color:#8aaac8!important;}
section[data-testid="stSidebar"] label{color:#3a5a7a!important;font-size:10px;text-transform:uppercase;letter-spacing:.1em;}
[data-testid="stAppViewContainer"]{background:#070e1d;}
[data-testid="stHeader"]{background:transparent;}

/* KPI */
.krow{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:18px;}
.kc{background:#0b1829;border:1px solid #132240;border-radius:10px;
    padding:14px 16px;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--a);}
.ki{font-size:18px;margin-bottom:4px;}
.kv{font-size:21px;font-weight:800;color:#ddeeff;font-family:'JetBrains Mono',monospace;line-height:1.2;}
.kl{font-size:10px;color:#3a5a7a;text-transform:uppercase;letter-spacing:.08em;margin-top:4px;}

/* Section heading */
.sh{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.13em;
    color:#388bfd;border-left:3px solid #388bfd;padding-left:8px;margin:20px 0 10px;}

/* Alert rows */
.ah{background:#2a0e0e;border-left:3px solid #f87171;padding:8px 12px;border-radius:5px;margin:3px 0;color:#fca5a5;font-size:12px;line-height:1.5;}
.am{background:#271a08;border-left:3px solid #fbbf24;padding:8px 12px;border-radius:5px;margin:3px 0;color:#fde68a;font-size:12px;line-height:1.5;}
.al{background:#081a0f;border-left:3px solid #34d399;padding:8px 12px;border-radius:5px;margin:3px 0;color:#6ee7b7;font-size:12px;line-height:1.5;}
.ai{background:#071628;border-left:3px solid #388bfd;padding:8px 12px;border-radius:5px;margin:3px 0;color:#93c5fd;font-size:12px;line-height:1.5;}

/* Risk bar */
.rb{background:#0b1829;border-radius:8px;padding:14px 16px;margin-bottom:8px;}
.rb-row{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;}
.rb-n{font-size:12px;color:#7a9abf;}
.rb-s{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;}
.rb-d{font-size:10.5px;color:#2e4a68;margin-bottom:5px;}
.rb-bg{background:#132240;border-radius:99px;height:6px;}
.rb-f{height:6px;border-radius:99px;}

/* Gauge box */
.gbox{background:#0b1829;border:1px solid #132240;border-radius:12px;
      padding:18px;text-align:center;}
.gscore{font-size:56px;font-weight:800;font-family:'JetBrains Mono',monospace;line-height:1;}
.glabel{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-top:6px;}
.gsub{font-size:10px;color:#3a5a7a;margin-top:4px;}

/* Page header */
.ph{display:flex;align-items:center;gap:12px;margin-bottom:18px;
    padding-bottom:14px;border-bottom:1px solid #0f1f35;}
.ph-ic{width:38px;height:38px;background:#388bfd;border-radius:9px;
       display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;}
.ph-t{font-size:24px;font-weight:800;color:#ddeeff;letter-spacing:-.02em;}
.ph-s{font-size:11px;color:#2e4a68;font-family:'JetBrains Mono',monospace;margin-top:2px;}

[data-testid="stTabs"] [role="tab"]{font-size:12.5px;font-weight:600;color:#3a5a7a!important;padding:7px 14px;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{color:#388bfd!important;border-bottom:2px solid #388bfd;background:rgba(56,139,253,.07);}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────
C  = ["#388bfd","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c","#22d3ee","#e879f9","#84cc16"]
BG = "#07111e"; PBG = "#090f1c"; GR = "rgba(255,255,255,0.05)"; FC = "#5a7a9a"

NHOM = [
    ("Ống HDPE",     r"HDPE"),
    ("Ống PVC",      r"PVC.*(?:nước|nong|thoát|cát)"),
    ("Ống PPR",      r"PPR"),
    ("Lõi PVC",      r"(?:Lơi|Lõi|lori)"),
    ("Phụ kiện",     r"(?:Nối|Co |Tê |Van |Keo |Bít|Măng|Hộp|Nắp|Y PVC|Y PPR)"),
    ("Thép/Đặc biệt",r"(?:thép|bích|PN\d)"),
]

def pl(fig, title="", h=360):
    fig.update_layout(
        plot_bgcolor=PBG, paper_bgcolor=PBG,
        font=dict(family="Be Vietnam Pro", color=FC, size=11),
        title=dict(text=title, font=dict(size=13,color="#aaccee"), x=0.01),
        height=h, margin=dict(l=8,r=8,t=38 if title else 8,b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
        xaxis=dict(gridcolor=GR, showline=False, tickfont_size=10),
        yaxis=dict(gridcolor=GR, showline=False, tickfont_size=10),
    )
    return fig

def f(v):
    try:
        v=float(v)
        if abs(v)>=1e9: return f"{v/1e9:.2f} Tỷ"
        if abs(v)>=1e6: return f"{v/1e6:.1f} Tr"
        if abs(v)>=1e3: return f"{v/1e3:.0f}K"
        return f"{v:,.0f}"
    except: return str(v)

def kpi(col,accent,icon,lab,val):
    col.markdown(f'<div class="kc" style="--a:{accent}"><div class="ki">{icon}</div>'
                 f'<div class="kv">{val}</div><div class="kl">{lab}</div></div>',
                 unsafe_allow_html=True)

def sh(t): st.markdown(f'<div class="sh">{t}</div>', unsafe_allow_html=True)
def al(cls,t): st.markdown(f'<div class="{cls}">{t}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  HEADER FIND
# ─────────────────────────────────────────────────────────────
def find_hdr(fb):
    try:
        raw=pd.read_excel(io.BytesIO(fb),header=None,engine="openpyxl",nrows=40)
        kws=["khách hàng","số chứng từ","tên hàng","ngày chứng từ","thành tiền bán"]
        for i in range(raw.shape[0]):
            vals=["" if (isinstance(v,float) and pd.isna(v)) else str(v) for v in raw.iloc[i]]
            if sum(1 for k in kws if k in " ".join(vals).lower())>=2: return i
    except: pass
    return 0

# ─────────────────────────────────────────────────────────────
#  UPLOAD
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="padding:14px 0 10px;border-bottom:1px solid #0f1f35;margin-bottom:12px;">'
                '<span style="font-size:14px;font-weight:700;color:#ddeeff;">🏗️ PKD Dự Án</span><br>'
                '<span style="font-size:10px;color:#2e4a68;">Hoa Sen Group Analytics</span></div>',
                unsafe_allow_html=True)
    up = st.file_uploader("📂 Upload Excel báo cáo", type=["xlsx"], accept_multiple_files=True)

if not up:
    st.markdown('<div style="display:flex;flex-direction:column;align-items:center;'
                'justify-content:center;height:70vh;gap:12px;text-align:center;">'
                '<div style="font-size:56px;">🏗️</div>'
                '<div style="font-size:22px;font-weight:800;color:#ddeeff;">PKD Dự Án Analytics</div>'
                '<div style="font-size:13px;color:#2e4a68;">Upload file Excel báo cáo bán hàng để bắt đầu</div>'
                '</div>', unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────
#  LOAD & COMPUTE
# ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="⏳ Đang xử lý…")
def load(fdata):
    frames=[]
    for name,fb in fdata:
        try:
            hr=find_hdr(fb)
            d=pd.read_excel(io.BytesIO(fb),header=hr,engine="openpyxl")
            d.columns=[str(c).strip().replace("\n"," ") for c in d.columns]
            d=d.loc[:,~d.columns.str.startswith("Unnamed")].dropna(how="all")
            d["_f"]=name; frames.append(d)
        except Exception as e:
            st.warning(f"⚠️ {name}: {e}")
    if not frames: return pd.DataFrame()
    df=pd.concat(frames,ignore_index=True)

    # ── Kiểm tra cột bắt buộc
    req=["Tên khách hàng","Ngày chứng từ","Thành tiền bán"]
    miss=[c for c in req if c not in df.columns]
    if miss: st.error(f"❌ Thiếu cột: {miss}"); return pd.DataFrame()

    # ── Số hoá
    NUM=["Thành tiền bán","Thành tiền vốn","Lợi nhuận","Khối lượng","Số lượng",
         "Giá bán","Giá vốn","Đơn giá vận chuyển","Đơn giá quy đổi"]
    for c in NUM:
        df[c]=pd.to_numeric(df.get(c,0),errors="coerce").fillna(0)

    # ── Ngày
    df["Ngày chứng từ"]=pd.to_datetime(df["Ngày chứng từ"],dayfirst=True,errors="coerce")
    df=df[df["Ngày chứng từ"].notna()].copy()
    df["Nam"]  =df["Ngày chứng từ"].dt.year.astype(str)
    df["Quy"]  =df["Ngày chứng từ"].dt.to_period("Q").astype(str)
    df["Thang"]=df["Ngày chứng từ"].dt.to_period("M").astype(str)
    df["Day"]  =df["Ngày chứng từ"].dt.day
    df["Cuoi"] =df["Day"]>=28

    # ── Loại GD
    gc =df["Ghi chú"].astype(str).str.upper()       if "Ghi chú"       in df.columns else pd.Series("",index=df.index)
    lo =df["Loại đơn hàng"].astype(str).str.upper() if "Loại đơn hàng" in df.columns else pd.Series("",index=df.index)
    df["GD"]="Bán"
    df.loc[gc.str.contains(r"NHẬP TRẢ|TRẢ HÀNG",regex=True,na=False),"GD"]="Trả"
    df.loc[lo.str.contains(r"TRA HANG|HUY HD",regex=True,na=False),"GD"]="Trả"
    df.loc[gc.str.contains(r"BỔ SUNG|THAY THẾ|BS PKTM",regex=True,na=False),"GD"]="Bổ sung"
    df.loc[(df["Khối lượng"]<0)&(df["GD"]=="Bán"),"GD"]="Nhập lại"

    # ── GIÁ (logic đúng)
    # GB/cái = TT bán ÷ SL
    df["GB_cai"]=np.where(df["Số lượng"]!=0, df["Thành tiền bán"]/df["Số lượng"], df["Giá bán"])
    # GV/kg = cột Giá vốn (đã là VNĐ/kg)
    df["GV_kg"]=df["Giá vốn"]
    # GB/kg = TT bán ÷ KL  (để so sánh với GV/kg)
    df["GB_kg"]=np.where(df["Khối lượng"]!=0, df["Thành tiền bán"]/df["Khối lượng"], 0)
    # Margin/kg
    df["Mgn_kg"]=df["GB_kg"]-df["GV_kg"]
    df["Mgn_pct"]=np.where(df["GB_kg"]!=0, df["Mgn_kg"]/df["GB_kg"]*100, 0)
    # Biên LN chính thức
    df["Bien"]=np.where(df["Thành tiền bán"]!=0, df["Lợi nhuận"]/df["Thành tiền bán"]*100, 0)

    # ── Z-score giá bán/cái (so cùng SP)
    m=df[(df["Số lượng"]>0)&(df["GB_cai"]>0)].copy()
    df.loc[m.index,"Z_gb"]=m.groupby("Tên hàng")["GB_cai"].transform(
        lambda x:(x-x.mean())/(x.std()+1e-9))

    # ── Z-score giá vốn/kg (so cùng SP)
    m2=df[(df["Khối lượng"]>0)&(df["GV_kg"]>0)].copy()
    df.loc[m2.index,"Z_gv"]=m2.groupby("Tên hàng")["GV_kg"].transform(
        lambda x:(x-x.mean())/(x.std()+1e-9))

    # ── TB thị trường giá bán/cái theo SP (trong dataset)
    sp_tb=df[df["GB_cai"]>0].groupby("Tên hàng")["GB_cai"].mean()
    df["SP_tb"]=df["Tên hàng"].map(sp_tb)
    df["Disc"]= np.where(df["SP_tb"]>0,(df["SP_tb"]-df["GB_cai"])/df["SP_tb"]*100,0)

    # ── Nhóm SP
    ten=df["Tên hàng"].astype(str) if "Tên hàng" in df.columns else pd.Series("",index=df.index)
    df["NSP"]="Khác"
    for lbl,pat in NHOM:
        df.loc[ten.str.contains(pat,case=False,regex=True,na=False),"NSP"]=lbl

    # ── Tỉnh (trích xuất từ Nơi giao hàng)
    if "Nơi giao hàng" in df.columns:
        tinh=df["Nơi giao hàng"].astype(str).str.extract(
            r'(?:Tỉnh|T\.|TP\s|Thành phố|tỉnh)\s*([A-ZÀ-Ỹa-zà-ỹ\s]+?)(?:,|\.|$)')[0].str.strip()
        df["Tinh"]=tinh.fillna("Khác")
    else: df["Tinh"]="Khác"

    return df

fdata=[(u.name,u.read()) for u in up]
DF=load(fdata)
if DF.empty: st.error("Không có dữ liệu hợp lệ."); st.stop()

# ─────────────────────────────────────────────────────────────
#  SIDEBAR FILTERS  (PKD → KH → Quý → Tháng)
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-size:10px;text-transform:uppercase;letter-spacing:.1em;'
                'color:#2e4a68;margin:12px 0 6px;">🔍 Bộ lọc</p>', unsafe_allow_html=True)

    PKD_COL="Tên nhóm KH" if "Tên nhóm KH" in DF.columns else "Mã nhóm KH"
    pkd_opts=["Tất cả"]+sorted(DF[PKD_COL].dropna().astype(str).unique())
    pkd=st.selectbox("🏢 Phòng Kinh Doanh Dự Án", pkd_opts)

    D1=DF[DF[PKD_COL].astype(str)==pkd].copy() if pkd!="Tất cả" else DF.copy()

    kh_opts=["Tất cả"]+sorted(D1["Tên khách hàng"].dropna().astype(str).unique())
    kh=st.selectbox("👤 Khách hàng", kh_opts)

    D2=D1[D1["Tên khách hàng"].astype(str)==kh].copy() if kh!="Tất cả" else D1.copy()

    q_opts=sorted(D2["Quy"].dropna().unique())
    q_sel=st.multiselect("📅 Quý", q_opts, default=q_opts)
    D2=D2[D2["Quy"].isin(q_sel)].copy()

    t_opts=sorted(D2["Thang"].dropna().unique())
    t_sel=st.multiselect("📆 Tháng", t_opts, default=t_opts)
    D2=D2[D2["Thang"].isin(t_sel)].copy()

    st.markdown(f'<p style="font-size:10px;color:#2e4a68;margin-top:8px;">{len(D2):,} dòng · '
                f'{D2["Thang"].nunique()} tháng</p>', unsafe_allow_html=True)

BAN=D2[D2["GD"]=="Bán"].copy()   # chỉ xuất bán

# ─────────────────────────────────────────────────────────────
#  PAGE HEADER
# ─────────────────────────────────────────────────────────────
nm=D2["Ngày chứng từ"].min(); nx=D2["Ngày chứng từ"].max()
scope=kh if kh!="Tất cả" else pkd
st.markdown(f'<div class="ph"><div class="ph-ic">🏗️</div><div>'
            f'<div class="ph-t">{scope}</div>'
            f'<div class="ph-s">{nm.strftime("%d/%m/%Y") if pd.notna(nm) else "?"} → '
            f'{nx.strftime("%d/%m/%Y") if pd.notna(nx) else "?"} &nbsp;·&nbsp; PKD Dự Án Analytics</div>'
            f'</div></div>', unsafe_allow_html=True)

if BAN.empty:
    st.warning("⚠️ Không có dữ liệu xuất bán."); st.stop()

# ─────────────────────────────────────────────────────────────
#  KPI ROW
# ─────────────────────────────────────────────────────────────
tDT =BAN["Thành tiền bán"].sum()
tLN =BAN["Lợi nhuận"].sum()
tKL =BAN["Khối lượng"].sum()/1000
tSL =BAN["Số lượng"].sum()
bien=(tLN/tDT*100) if tDT else 0
nDH =BAN["Số ĐH"].nunique() if "Số ĐH" in BAN.columns else 0

st.markdown('<div class="krow">',unsafe_allow_html=True)
c1,c2,c3,c4,c5,c6=st.columns(6)
kpi(c1,"#388bfd","💰","Doanh thu",f(tDT))
kpi(c2,"#34d399","💹","Lợi nhuận",f(tLN))
kpi(c3,"#fbbf24","📊","Biên LN %",f"{bien:.1f}%")
kpi(c4,"#a78bfa","⚖️","KL (tấn)",f"{tKL:,.1f}")
kpi(c5,"#22d3ee","📦","SL (cái)",f"{int(tSL):,}")
kpi(c6,"#fb923c","🏗️","Dự án / ĐH",f"{nDH}")
st.markdown('</div>',unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  4 TABS
# ─────────────────────────────────────────────────────────────
T1,T2,T3,T4=st.tabs([
    "📦 Sản phẩm & Dự án",
    "📈 Doanh thu & Sản lượng",
    "💹 Lợi nhuận & Giá",
    "⚠️ Rủi ro & Bất thường",
])

# ═══════════════════════════════════════════════════════════════
#  TAB 1 – SẢN PHẨM & DỰ ÁN
# ═══════════════════════════════════════════════════════════════
with T1:
    # ── Loại hình công trình
    sh("📋 Loại hình công trình")
    if "Loại hình kinh doanh" in BAN.columns:
        dloai=(BAN.groupby("Loại hình kinh doanh")
               .agg(DT=("Thành tiền bán","sum"),KL=("Khối lượng",lambda x:x.sum()/1000))
               .reset_index().sort_values("DT",ascending=False))
        c1,c2=st.columns([1.6,1])
        with c1:
            fig=px.bar(dloai,y="Loại hình kinh doanh",x="DT",orientation="h",
                       color="DT",color_continuous_scale=[[0,"#0d1f3a"],[1,"#388bfd"]],
                       text=dloai["DT"].apply(f),labels={"DT":"Doanh thu","Loại hình kinh doanh":""})
            fig.update_traces(textposition="outside",textfont_size=10)
            fig.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
            pl(fig,"Doanh thu theo Loại hình Công trình",h=280)
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            fig2=px.pie(dloai,names="Loại hình kinh doanh",values="DT",
                        hole=0.55,color_discrete_sequence=C)
            fig2.update_traces(textposition="inside",textinfo="percent",textfont_size=11)
            pl(fig2,"Tỷ trọng",h=280); st.plotly_chart(fig2,use_container_width=True)

    # ── Top dự án
    sh("🏆 Top dự án (Số ĐH)")
    if "Số ĐH" in BAN.columns:
        dda=(BAN.groupby("Số ĐH")
             .agg(KH=("Tên khách hàng","first"),
                  Loai=("Loại hình kinh doanh","first") if "Loại hình kinh doanh" in BAN.columns else ("Tên khách hàng","first"),
                  DT=("Thành tiền bán","sum"),LN=("Lợi nhuận","sum"),
                  KL=("Khối lượng",lambda x:round(x.sum()/1000,1)),
                  NSP=("Tên hàng","nunique") if "Tên hàng" in BAN.columns else ("Thành tiền bán","count"),
                  Nbd=("Ngày chứng từ","min"),Nkt=("Ngày chứng từ","max"))
             .reset_index())
        dda["Bien"]=(dda["LN"]/dda["DT"].replace(0,np.nan)*100).round(1).fillna(0)
        dda["Tgian"]=(dda["Nkt"]-dda["Nbd"]).dt.days.apply(lambda x:f"{x}d")
        dda=dda.sort_values("DT",ascending=False)
        top=st.slider("Số dự án hiển thị",5,30,15,key="sl1")
        dtop=dda.head(top)

        fig3=px.bar(dtop,x="Số ĐH",y="DT",color="Bien",
                    color_continuous_scale="RdYlGn",
                    hover_data={"KH":True,"Loai":True,"KL":True,"Bien":True,"Tgian":True},
                    labels={"DT":"Doanh thu","Bien":"Biên LN%"})
        fig3.update_layout(xaxis_tickangle=-35,xaxis_tickfont_size=8,coloraxis_colorbar_thickness=12)
        pl(fig3,f"Top {top} dự án – DT (màu = Biên LN%)",h=360)
        st.plotly_chart(fig3,use_container_width=True)

        sc=["Số ĐH","KH","Loai","DT","LN","Bien","KL","NSP","Tgian"]
        sc=[c for c in sc if c in dtop.columns]
        ds=dtop[sc].copy(); ds["DT"]=ds["DT"].apply(f); ds["LN"]=ds["LN"].apply(f)
        st.dataframe(ds.rename(columns={"KH":"Khách hàng","Loai":"Loại hình","Bien":"Biên%",
                                         "KL":"KL(tấn)","NSP":"#SP","Tgian":"Thời gian"}),
                     use_container_width=True,hide_index=True)

    # ── SP & heatmap
    sh("📦 Mặt hàng quan trọng & Thời điểm mua")
    c1,c2=st.columns(2)
    with c1:
        if "Tên hàng" in BAN.columns:
            dsp=(BAN.groupby("Tên hàng")
                 .agg(KL=("Khối lượng",lambda x:round(x.sum()/1000,1)),DT=("Thành tiền bán","sum"))
                 .reset_index().sort_values("KL",ascending=False).head(12))
            fig4=px.bar(dsp,y="Tên hàng",x="KL",orientation="h",color="KL",
                        color_continuous_scale=[[0,"#0d1f3a"],[1,"#34d399"]],
                        text=dsp["KL"].apply(lambda v:f"{v:.0f}T"),labels={"KL":"KL(tấn)","Tên hàng":""})
            fig4.update_traces(textposition="outside",textfont_size=10)
            fig4.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
            pl(fig4,"Top 12 SP – Khối lượng (tấn)",h=360); st.plotly_chart(fig4,use_container_width=True)
    with c2:
        dnsp=(BAN.groupby("NSP").agg(DT=("Thành tiền bán","sum"),KL=("Khối lượng",lambda x:x.sum()/1000)).reset_index())
        fig5=px.pie(dnsp,names="NSP",values="DT",hole=0.5,color_discrete_sequence=C)
        fig5.update_traces(textposition="inside",textinfo="percent+label",textfont_size=10)
        pl(fig5,"Tỷ trọng DT theo Nhóm SP",h=360); st.plotly_chart(fig5,use_container_width=True)

    # Heatmap
    if "Tên hàng" in BAN.columns:
        top8=BAN.groupby("Tên hàng")["Khối lượng"].sum().nlargest(8).index.tolist()
        dhm=(BAN[BAN["Tên hàng"].isin(top8)]
             .groupby(["Tên hàng","Thang"])["Khối lượng"].sum()/1000).reset_index()
        dpiv=dhm.pivot(index="Tên hàng",columns="Thang",values="Khối lượng").fillna(0)
        if not dpiv.empty:
            fig6=go.Figure(go.Heatmap(
                z=dpiv.values,x=list(dpiv.columns),y=list(dpiv.index),
                colorscale="Blues",hoverongaps=False,
                text=[[f"{v:.0f}T" for v in row] for row in dpiv.values],
                texttemplate="%{text}",textfont_size=9))
            fig6.update_layout(plot_bgcolor=PBG,paper_bgcolor=PBG,font_color=FC,
                                height=260,margin=dict(l=8,r=8,t=8,b=8),
                                xaxis_tickfont_size=10,yaxis_tickfont_size=9)
            st.plotly_chart(fig6,use_container_width=True)

    # Giao hàng
    sh("🚚 Địa điểm giao hàng & Phương tiện")
    c1,c2,c3=st.columns(3)
    with c1:
        if "Freight Terms" in BAN.columns:
            dft=BAN["Freight Terms"].value_counts().reset_index(); dft.columns=["H","N"]
            fig7=px.pie(dft,names="H",values="N",hole=0.55,color_discrete_sequence=C)
            fig7.update_traces(textposition="inside",textinfo="percent",textfont_size=10)
            pl(fig7,"Điều kiện giao hàng",h=240); st.plotly_chart(fig7,use_container_width=True)
    with c2:
        if "Shipping method" in BAN.columns:
            dsm=BAN["Shipping method"].value_counts().reset_index(); dsm.columns=["P","N"]
            fig8=px.pie(dsm,names="P",values="N",hole=0.55,color_discrete_sequence=C[2:])
            fig8.update_traces(textposition="inside",textinfo="percent",textfont_size=10)
            pl(fig8,"Phương tiện VC",h=240); st.plotly_chart(fig8,use_container_width=True)
    with c3:
        dtinh=(BAN.groupby("Tinh").agg(KL=("Khối lượng",lambda x:round(x.sum()/1000,1))).reset_index()
               .sort_values("KL",ascending=False))
        dtinh=dtinh[dtinh["Tinh"].str.len()>2].head(8)
        fig9=px.bar(dtinh,x="KL",y="Tinh",orientation="h",
                    color="KL",color_continuous_scale=[[0,"#0d1f3a"],[1,"#388bfd"]],
                    text=dtinh["KL"].apply(lambda v:f"{v:.0f}T"),labels={"KL":"KL(tấn)","Tinh":""})
        fig9.update_traces(textposition="outside",textfont_size=9)
        fig9.update_layout(coloraxis_showscale=False,yaxis=dict(autorange="reversed"))
        pl(fig9,"Top 8 Tỉnh/TP – KL(tấn)",h=240); st.plotly_chart(fig9,use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  TAB 2 – DOANH THU & SẢN LƯỢNG
# ═══════════════════════════════════════════════════════════════
with T2:
    sh("📈 Biến động theo tháng")
    dm=(BAN.groupby("Thang")
        .agg(DT=("Thành tiền bán","sum"),
             KL=("Khối lượng",lambda x:x.sum()/1000),
             SL=("Số lượng","sum"),
             LN=("Lợi nhuận","sum"),
             NDH=("Số ĐH","nunique") if "Số ĐH" in BAN.columns else ("Thành tiền bán","count"))
        .reset_index().sort_values("Thang"))
    dm["Bien"]=(dm["LN"]/dm["DT"].replace(0,np.nan)*100).round(1).fillna(0)
    dm["KL_d"]=dm["KL"].diff().round(1)
    dm["KL_mom"]=dm["KL"].pct_change().mul(100).round(1)

    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,
        subplot_titles=("Doanh thu (VNĐ) & Khối lượng (tấn)","Biên LN (%) & Tăng trưởng KL MoM (%)"),
        vertical_spacing=0.10,row_heights=[0.6,0.4])

    fig.add_trace(go.Bar(x=dm["Thang"],y=dm["DT"],name="Doanh thu",
                          marker_color="#388bfd",opacity=0.85,
                          text=dm["DT"].apply(f),textposition="outside",textfont_size=9),row=1,col=1)
    fig.add_trace(go.Scatter(x=dm["Thang"],y=dm["KL"],name="KL (tấn)",
                              mode="lines+markers",line=dict(color="#34d399",width=2.5),
                              marker_size=6),row=1,col=1)
    fig.add_trace(go.Scatter(x=dm["Thang"],y=dm["Bien"],name="Biên LN%",
                              mode="lines+markers+text",
                              text=[f"{v:.1f}%" for v in dm["Bien"]],
                              textposition="top center",textfont_size=9,
                              line=dict(color="#fbbf24",width=2.5)),row=2,col=1)
    fig.add_trace(go.Bar(x=dm["Thang"],y=dm["KL_mom"],name="KL MoM%",
                          marker_color=[("#f87171" if (v or 0)<0 else "#34d399") for v in dm["KL_mom"]],
                          opacity=0.6),row=2,col=1)
    fig.update_layout(plot_bgcolor=PBG,paper_bgcolor=PBG,
                       font=dict(family="Be Vietnam Pro",color=FC,size=11),
                       height=540,legend=dict(orientation="h",y=-0.06,bgcolor="rgba(0,0,0,0)"),
                       margin=dict(l=8,r=8,t=34,b=8))
    for ax in fig.layout:
        if ax.startswith(("xaxis","yaxis")):
            fig.layout[ax].update(gridcolor=GR,showline=False)
    st.plotly_chart(fig,use_container_width=True)

    # Tháng đột biến tự động
    sh("⚡ Phát hiện tháng sản lượng bất thường")
    mkl=dm["KL"].mean(); skl=dm["KL"].std() or 1
    found=False
    for _,r in dm.iterrows():
        z=(r["KL"]-mkl)/skl; mom=r.get("KL_mom",0) or 0
        if abs(z)>1.5:
            cls,ico=("ah","🔺") if z>0 else ("am","🔻")
            al(cls,f"{ico} <b>{r['Thang']}</b>: KL = <b>{r['KL']:,.0f} tấn</b> "
               f"(Z={z:+.1f}σ, MoM={mom:+.1f}%) — "
               f"{'Đột biến tăng → kiểm tra đơn hàng dự án lớn tập trung, rủi ro giao hàng không đủ' if z>0 else 'Sụt giảm mạnh → tiến độ dự án chậm, khách hoãn nhận hàng'}")
            found=True
    if not found: al("al","✅ Sản lượng ổn định qua các tháng, không có đột biến.")

    # Quý
    sh("📊 Tổng hợp theo Quý")
    dq=(BAN.groupby("Quy")
        .agg(DT=("Thành tiền bán","sum"),KL=("Khối lượng",lambda x:round(x.sum()/1000,1)),
             LN=("Lợi nhuận","sum"),
             NDH=("Số ĐH","nunique") if "Số ĐH" in BAN.columns else ("Thành tiền bán","count"),
             NKH=("Tên khách hàng","nunique"))
        .reset_index())
    dq["Bien"]=(dq["LN"]/dq["DT"].replace(0,np.nan)*100).round(1).fillna(0)
    c1,c2=st.columns(2)
    with c1:
        fq=px.bar(dq,x="Quy",y="DT",color="Bien",color_continuous_scale="RdYlGn",
                  text=dq["DT"].apply(f),labels={"DT":"Doanh thu","Bien":"Biên LN%","Quy":"Quý"})
        fq.update_traces(textposition="outside",textfont_size=10)
        fq.update_layout(coloraxis_colorbar_thickness=12)
        pl(fq,"Doanh thu theo Quý (màu = Biên LN%)",h=280); st.plotly_chart(fq,use_container_width=True)
    with c2:
        dqs=dq.copy(); dqs["DT"]=dqs["DT"].apply(f); dqs["LN"]=dqs["LN"].apply(f)
        dqs.columns=["Quý","Doanh thu","KL(tấn)","Lợi nhuận","Số ĐH","Số KH","Biên(%)"]
        st.dataframe(dqs,use_container_width=True,hide_index=True)

    # Bảng chi tiết tháng
    with st.expander("📋 Bảng chi tiết từng tháng"):
        dms=dm.copy(); dms["DT"]=dms["DT"].apply(f); dms["LN"]=dms["LN"].apply(f)
        dms=dms.drop(columns=["KL_d","KL_mom"],errors="ignore")
        dms.columns=["Tháng","Doanh thu","KL(tấn)","SL(cái)","Lợi nhuận","Số ĐH","Biên(%)"]
        st.dataframe(dms,use_container_width=True,hide_index=True)

# ═══════════════════════════════════════════════════════════════
#  TAB 3 – LỢI NHUẬN & GIÁ
# ═══════════════════════════════════════════════════════════════
with T3:
    al("ai","📌 <b>Logic giá:</b>&nbsp; GB/cái (VNĐ/cái) × SL = TT Bán &nbsp;|&nbsp; "
           "GV/kg (VNĐ/kg) × KL = TT Vốn &nbsp;|&nbsp; "
           "Margin/kg = (TT Bán ÷ KL) − GV/kg")

    # Chart LN theo tháng
    sh("💹 Doanh thu / Vốn / Lợi nhuận & Biên LN (%) theo tháng")
    dlnm=(BAN.groupby("Thang")
          .agg(DT=("Thành tiền bán","sum"),Von=("Thành tiền vốn","sum"),LN=("Lợi nhuận","sum"))
          .reset_index().sort_values("Thang"))
    dlnm["Bien"]=(dlnm["LN"]/dlnm["DT"].replace(0,np.nan)*100).round(2).fillna(0)

    figln=make_subplots(rows=2,cols=1,shared_xaxes=True,
        subplot_titles=("DT / Giá vốn / LN (VNĐ)","Biên LN (%)"),
        vertical_spacing=0.12,row_heights=[0.55,0.45])
    figln.add_trace(go.Bar(x=dlnm["Thang"],y=dlnm["DT"],name="Doanh thu",marker_color="#388bfd",opacity=0.8),row=1,col=1)
    figln.add_trace(go.Bar(x=dlnm["Thang"],y=dlnm["Von"],name="Giá vốn",marker_color="#f87171",opacity=0.8),row=1,col=1)
    figln.add_trace(go.Scatter(x=dlnm["Thang"],y=dlnm["LN"],name="Lợi nhuận",
                                mode="lines+markers",line=dict(color="#34d399",width=2.5)),row=1,col=1)
    figln.add_trace(go.Scatter(x=dlnm["Thang"],y=dlnm["Bien"],name="Biên LN%",
                                mode="lines+markers+text",
                                text=[f"{v:.1f}%" for v in dlnm["Bien"]],
                                textposition="top center",textfont_size=9,
                                line=dict(color="#fbbf24",width=2.5)),row=2,col=1)
    figln.update_layout(plot_bgcolor=PBG,paper_bgcolor=PBG,
                         font=dict(family="Be Vietnam Pro",color=FC,size=11),
                         height=500,barmode="group",
                         legend=dict(orientation="h",y=-0.07,bgcolor="rgba(0,0,0,0)"),
                         margin=dict(l=8,r=8,t=34,b=8))
    for ax in figln.layout:
        if ax.startswith(("xaxis","yaxis")): figln.layout[ax].update(gridcolor=GR,showline=False)
    st.plotly_chart(figln,use_container_width=True)

    # Kỳ bất thường biên LN
    mb=dlnm["Bien"].mean(); sb=dlnm["Bien"].std() or 1
    anom_thang=[r for _,r in dlnm.iterrows() if (r["Bien"]-mb)/sb < -1.2]
    if anom_thang:
        sh("🔍 Kỳ nghi có chiết khấu / chính sách đặc biệt")
        for r in anom_thang:
            z=(r["Bien"]-mb)/sb
            cls="ah" if z<-1.8 else "am"
            al(cls,f"{'🔴' if z<-1.8 else '🟡'} <b>{r['Thang']}</b>: Biên LN = <b>{r['Bien']:.1f}%</b> "
               f"(TB={mb:.1f}%, Z={z:.1f}σ) → Nguyên nhân có thể: chiết khấu hợp đồng dự án lớn, "
               f"giá đặc biệt cuối quý, hoặc bán kèm SP biên thấp")

    # Margin/kg theo nhóm SP
    sh("⚙️ So sánh Giá bán/kg vs Giá vốn/kg theo Nhóm SP")
    dmnsp=(BAN[BAN["Khối lượng"]>0]
           .groupby("NSP")
           .agg(GV=("GV_kg","mean"),GB=("GB_kg","mean"),Mgn=("Mgn_kg","mean"),
                Mpct=("Mgn_pct","mean"))
           .reset_index().round(0))
    c1,c2=st.columns(2)
    with c1:
        fmg=go.Figure()
        fmg.add_trace(go.Bar(name="Giá bán/kg",x=dmnsp["NSP"],y=dmnsp["GB"],marker_color="#388bfd",opacity=0.85))
        fmg.add_trace(go.Bar(name="Giá vốn/kg",x=dmnsp["NSP"],y=dmnsp["GV"],marker_color="#f87171",opacity=0.85))
        fmg.update_layout(barmode="group")
        pl(fmg,"GB/kg vs GV/kg theo Nhóm SP",h=300); st.plotly_chart(fmg,use_container_width=True)
    with c2:
        fmp=px.bar(dmnsp.sort_values("Mpct",ascending=False),x="NSP",y="Mpct",
                   color="Mpct",color_continuous_scale="RdYlGn",
                   text=dmnsp.sort_values("Mpct",ascending=False)["Mpct"].apply(lambda v:f"{v:.0f}%"),
                   labels={"Mpct":"Margin/kg %","NSP":""})
        fmp.update_traces(textposition="outside",textfont_size=10)
        fmp.update_layout(coloraxis_colorbar_thickness=12)
        pl(fmp,"Margin/kg (%) theo Nhóm SP",h=300); st.plotly_chart(fmp,use_container_width=True)

    # Scatter dự án
    if "Số ĐH" in BAN.columns:
        sh("🏗️ Scatter Dự án: Doanh thu vs Biên LN%")
        dld=(BAN.groupby("Số ĐH")
             .agg(KH=("Tên khách hàng","first"),
                  DT=("Thành tiền bán","sum"),LN=("Lợi nhuận","sum"),
                  KL=("Khối lượng",lambda x:round(x.sum()/1000,1)))
             .reset_index())
        dld["Bien"]=(dld["LN"]/dld["DT"].replace(0,np.nan)*100).round(1).fillna(0)
        fsc=px.scatter(dld,x="DT",y="Bien",size="KL",color="Bien",
                       hover_data={"KH":True,"KL":True},
                       color_continuous_scale="RdYlGn",
                       labels={"DT":"Doanh thu","Bien":"Biên LN%","KL":"KL(tấn)"})
        fsc.add_hline(y=dld["Bien"].mean(),line_dash="dash",line_color="#fbbf24",
                       annotation_text=f"TB {dld['Bien'].mean():.1f}%",
                       annotation_font_color="#fbbf24")
        fsc.add_hline(y=0,line_color="#f87171",line_width=1,
                       annotation_text="Ngưỡng lỗ",annotation_font_color="#f87171")
        pl(fsc,"Dự án: DT vs Biên LN% (kích thước = KL tấn)",h=380)
        st.plotly_chart(fsc,use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  TAB 4 – RỦI RO & BẤT THƯỜNG (gộp, thang 100)
# ═══════════════════════════════════════════════════════════════
with T4:
    sh("⚠️ Phân tích Rủi ro & Dấu hiệu Bất thường (thang 100)")
    al("ai","📌 Điểm rủi ro tổng hợp từ 6 nhóm dấu hiệu chính. "
           "Mỗi nhóm được tính dựa trên số liệu thực tế, có chỉ ra nguyên nhân và bằng chứng cụ thể.")

    tDT_=BAN["Thành tiền bán"].sum()
    tLN_=BAN["Lợi nhuận"].sum()
    bien_=(tLN_/tDT_*100) if tDT_ else 0

    # ── Tính 6 chỉ số rủi ro, mỗi chỉ số max tổng thành 100
    RISKS=[]  # (tên, điểm/100, level, mô_tả_nguyên_nhân, df_detail)

    # R1 – Biên LN & Giá (30 điểm)
    # Sub R1a: Biên LN tổng thấp (15đ)
    r1a=15 if bien_<5 else 9 if bien_<15 else 3 if bien_<25 else 0
    # Sub R1b: Margin/kg âm (15đ)
    dlo=BAN[(BAN["Khối lượng"]>0)&(BAN["GB_kg"]>0)&(BAN["Mgn_kg"]<0)]
    plo=(len(dlo)/len(BAN)*100) if len(BAN) else 0; tlo=abs(dlo["Lợi nhuận"].sum())
    r1b=min(15,plo*3)
    r1=r1a+r1b
    lv1="h" if r1>=20 else "m" if r1>=10 else "l"
    detail_r1=(f"Biên LN tổng = <b>{bien_:.1f}%</b> {'(rất thấp)' if r1a>=12 else '(thấp)' if r1a>=6 else ''}"
               f" &nbsp;|&nbsp; Margin/kg âm: <b>{len(dlo)} dòng ({plo:.1f}%)</b> – "
               f"thiệt hại {f(tlo)} VNĐ.<br>"
               f"<b>→ Nguyên nhân:</b> Giá bán/cái chiết khấu sâu cho hàng phụ kiện nhỏ (tính theo cái) "
               f"nhưng giá vốn tính theo kg cao → bán lỗ thực tế khi quy về kg.")
    dcols1=["Ngày chứng từ","Tên khách hàng","Tên hàng","GB_kg","GV_kg","Mgn_kg","Lợi nhuận"]
    dcols1=[c for c in dcols1 if c in dlo.columns]
    RISKS.append(("💹 Biên LN & Margin/kg",30,r1,lv1,detail_r1,
                  dlo[dcols1].rename(columns={"GB_kg":"GB/kg","GV_kg":"GV/kg","Mgn_kg":"Margin/kg"}) if not dlo.empty else None))

    # R2 – Trả hàng & Hủy đơn (20 điểm)
    dtra=D2[D2["GD"].isin(["Trả","Nhập lại"])]
    gt_tra=abs(dtra["Thành tiền bán"].sum()); tl_tra=(gt_tra/tDT_*100) if tDT_ else 0
    r2=min(20,tl_tra*2)
    lv2="h" if tl_tra>10 else "m" if tl_tra>3 else "l"
    detail_r2=(f"<b>{len(dtra)} phiếu</b> trả hàng/hủy đơn – Giá trị: <b>{f(gt_tra)} VNĐ ({tl_tra:.1f}% DT)</b><br>"
               f"<b>→ Nguyên nhân phổ biến:</b> Khách đặt nhầm item, xuất sai quy cách, "
               f"chất lượng không đáp ứng yêu cầu công trình (đường kính/áp lực), "
               f"hoặc thay đổi thiết kế dự án giữa chừng.")
    dcols2=["Ngày chứng từ","Tên khách hàng","Tên hàng","Khối lượng","Thành tiền bán","Ghi chú"]
    dcols2=[c for c in dcols2 if c in dtra.columns]
    RISKS.append(("↩️ Trả hàng & Hủy đơn",20,round(r2,1),lv2,detail_r2,
                  dtra[dcols2].head(30) if not dtra.empty else None))

    # R3 – Giá bán bất thường (20 điểm)
    # Sub R3a: Z-score giá bán/cái > 2.5σ (10đ)
    zagb=BAN.get("Z_gb",pd.Series(0,index=BAN.index)).fillna(0)
    nabn=int((zagb.abs()>2.5).sum()); pabn=(nabn/len(BAN)*100) if len(BAN) else 0
    r3a=min(10,pabn*3)
    # Sub R3b: Discount vs TB thị trường >15% (10đ)
    ddisc=BAN[(BAN.get("Disc",pd.Series(0,index=BAN.index)).fillna(0)>15)&(BAN["GB_cai"]>0)]
    pdisc=(len(ddisc)/len(BAN)*100) if len(BAN) else 0
    r3b=min(10,pdisc*1.5)
    r3=r3a+r3b
    lv3="h" if r3>=14 else "m" if r3>=6 else "l"
    detail_r3=(f"Giá bán/cái bất thường (Z>2.5σ): <b>{nabn} dòng ({pabn:.1f}%)</b><br>"
               f"Giá bán thấp hơn TB thị trường >15%: <b>{len(ddisc)} dòng ({pdisc:.1f}%)</b><br>"
               f"<b>→ Nguyên nhân:</b> Chiết khấu đặc biệt theo hợp đồng dự án, "
               f"giá thương lượng cho KH lớn mua số lượng lớn, hoặc sai sót nhập liệu giá bán. "
               f"Cần đối chiếu với phê duyệt chiết khấu từ cấp quản lý.")
    dabn=BAN[zagb.abs()>2.5][["Ngày chứng từ","Tên khách hàng","Tên hàng","GB_cai","SP_tb","Disc","Số lượng","Thành tiền bán"]].copy()
    dabn=dabn.rename(columns={"GB_cai":"GB/cái","SP_tb":"TB thị trường","Disc":"Giảm%"})
    RISKS.append(("💰 Giá bán bất thường",20,round(r3,1),lv3,detail_r3,
                  dabn if not dabn.empty else None))

    # R4 – Giá vốn/kg bất thường (15 điểm)
    zagv=BAN.get("Z_gv",pd.Series(0,index=BAN.index)).fillna(0)
    n_gv=int((zagv.abs()>2.5).sum()); p_gv=(n_gv/len(BAN)*100) if len(BAN) else 0
    r4=min(15,p_gv*4)
    lv4="h" if r4>=10 else "m" if r4>=4 else "l"
    detail_r4=(f"Giá vốn/kg bất thường (Z>2.5σ): <b>{n_gv} dòng ({p_gv:.1f}%)</b><br>"
               f"<b>→ Nguyên nhân:</b> Xuất lô hàng tồn kho cũ nhập giá khác, "
               f"phân bổ chi phí sản xuất bất thường (lô sản xuất nhỏ tốn phí hơn), "
               f"hoặc sai sót phân bổ chi phí trong hệ thống ERP.")
    dgv=BAN[zagv.abs()>2.5][["Ngày chứng từ","Tên khách hàng","Tên hàng","GV_kg","Khối lượng","Thành tiền vốn"]].copy()
    dgv=dgv.rename(columns={"GV_kg":"GV/kg"})
    RISKS.append(("🏭 Giá vốn/kg bất thường",15,round(r4,1),lv4,detail_r4,
                  dgv if not dgv.empty else None))

    # R5 – Tập trung cuối tháng & đột biến KL (10 điểm)
    dt_cuoi=BAN[BAN["Cuoi"]]["Thành tiền bán"].sum(); tl_cuoi=(dt_cuoi/tDT_*100) if tDT_ else 0
    r5a=min(6,tl_cuoi/8)
    # KL đột biến
    mkl=dm["KL"].mean(); skl=dm["KL"].std() or 1
    n_db=len(dm[dm["KL"].sub(mkl).div(skl).abs()>1.5])
    r5b=min(4,n_db*2)
    r5=r5a+r5b
    lv5="h" if r5>=7 else "m" if r5>=3 else "l"
    detail_r5=(f"DT tập trung cuối tháng (ngày 28–31): <b>{tl_cuoi:.1f}%</b> ({f(dt_cuoi)} VNĐ)<br>"
               f"Số tháng KL đột biến (>1.5σ): <b>{n_db} tháng</b><br>"
               f"<b>→ Nguyên nhân:</b> Đẩy doanh số hoàn thành chỉ tiêu cuối kỳ, "
               f"ghi nhận doanh thu trước khi kết sổ, hoặc dự án nhận hàng theo đợt cuối tháng. "
               f"KL đột biến thường gắn với đơn hàng dự án lớn thi công tập trung.")
    RISKS.append(("📅 Tập trung cuối tháng & KL đột biến",10,round(r5,1),lv5,detail_r5,None))

    # R6 – Biến động biên LN theo tháng (5 điểm)
    mb2=dlnm["Bien"].mean(); sb2=dlnm["Bien"].std() or 1
    n_a=len(dlnm[(dlnm["Bien"]-mb2).div(sb2)<-1.2])
    r6=min(5,n_a*2)
    lv6="h" if r6>=4 else "m" if r6>=2 else "l"
    detail_r6=(f"Số tháng Biên LN thấp bất thường (Z<-1.2σ): <b>{n_a} tháng</b><br>"
               f"<b>→ Nguyên nhân:</b> Chính sách chiết khấu theo mùa/quý, "
               f"cạnh tranh giá gay gắt từ đối thủ trong kỳ đó, "
               f"hoặc mix sản phẩm dịch chuyển sang SP biên thấp (ống lớn HDPE).")
    RISKS.append(("📉 Biến động Biên LN bất thường",5,round(r6,1),lv6,detail_r6,None))

    # ── TỔNG ĐIỂM (thang 100)
    total_w=sum(r[1] for r in RISKS)   # = 100
    total_s=sum(r[2] for r in RISKS)
    score=round(total_s/total_w*100) if total_w else 0
    nh=sum(1 for r in RISKS if r[3]=="h")
    nm_=sum(1 for r in RISKS if r[3]=="m")
    nl=sum(1 for r in RISKS if r[3]=="l")
    rc="#f87171" if score>=60 else "#fbbf24" if score>=30 else "#34d399"
    rl="RỦI RO CAO" if score>=60 else "RỦI RO TRUNG BÌNH" if score>=30 else "RỦI RO THẤP"

    # ── Layout: Gauge bên trái, bars bên phải
    st.markdown("---")
    cg,cb=st.columns([1,2.2])

    with cg:
        # Gauge dạng Indicator
        fg=go.Figure(go.Indicator(
            mode="gauge+number",value=score,
            number={"font":{"size":54,"color":rc,"family":"JetBrains Mono"}},
            gauge={"axis":{"range":[0,100],"tickfont":{"size":10,"color":FC},"tickcolor":FC},
                   "bar":{"color":rc,"thickness":0.7},
                   "bgcolor":"#0b1829","borderwidth":0,
                   "steps":[{"range":[0,30],"color":"#081a0f"},
                             {"range":[30,60],"color":"#271a08"},
                             {"range":[60,100],"color":"#2a0e0e"}],
                   "threshold":{"line":{"color":"#fff","width":2},"thickness":0.85,"value":score}}))
        fg.update_layout(paper_bgcolor="#0b1829",plot_bgcolor="#0b1829",
                          font_color=FC,height=240,
                          margin=dict(l=16,r=16,t=16,b=16),
                          annotations=[dict(text=rl,x=0.5,y=-0.12,showarrow=False,
                                             font=dict(size=12,color=rc,family="Be Vietnam Pro",weight=700),
                                             xanchor="center")])
        st.markdown('<div class="gbox">', unsafe_allow_html=True)
        st.plotly_chart(fg,use_container_width=True)
        st.markdown(f'<div class="gsub">Điểm: {score}/100 &nbsp;·&nbsp; '
                    f'🔴 {nh} &nbsp;🟡 {nm_} &nbsp;🟢 {nl}</div></div>',
                    unsafe_allow_html=True)

    with cb:
        # Risk bars
        for rname,rw,rs,rlv,_,_ in RISKS:
            pct=(rs/rw*100) if rw else 0
            bc="#f87171" if rlv=="h" else "#fbbf24" if rlv=="m" else "#34d399"
            badge=f'<span class="badge-{rlv}" style="background:{bc};color:{"#fff" if rlv!="m" else "#1a1a00"};'
            badge+=f'font-size:9px;font-weight:700;padding:2px 6px;border-radius:99px;">'
            badge+=f'{"CAO" if rlv=="h" else "TB" if rlv=="m" else "OK"}</span>'
            st.markdown(f"""<div class="rb">
                <div class="rb-row">
                    <span class="rb-n">{rname}</span>
                    <span style="display:flex;align-items:center;gap:6px;">
                        {badge}
                        <span class="rb-s" style="color:{bc}">{rs:.1f}<span style="font-size:10px;color:{FC}">/{rw}</span></span>
                    </span>
                </div>
                <div class="rb-bg"><div class="rb-f" style="width:{pct:.0f}%;background:{bc};"></div></div>
            </div>""", unsafe_allow_html=True)

    # ── Chi tiết từng rủi ro
    st.markdown("---")
    sh("🔍 Phân tích chi tiết – Nguyên nhân & Bằng chứng")

    for rname,rw,rs,rlv,detail,ddet in RISKS:
        ico="🔴" if rlv=="h" else "🟡" if rlv=="m" else "🟢"
        cls="ah" if rlv=="h" else "am" if rlv=="m" else "al"
        al(cls,f"{ico} <b>{rname}</b> &nbsp;·&nbsp; Điểm: <b>{rs:.1f}/{rw}</b><br>{detail}")
        if ddet is not None and not ddet.empty and rlv in ["h","m"]:
            with st.expander(f"📋 Xem {min(len(ddet),40)} bằng chứng – {rname}"):
                ds=ddet.head(40).copy()
                # Format số
                for c in ["Thành tiền bán","Lợi nhuận","GB/kg","GV/kg","Margin/kg",
                           "GB/cái","TB thị trường","Giảm%"]:
                    if c in ds.columns:
                        ds[c]=pd.to_numeric(ds[c],errors="coerce").apply(
                            lambda v: f"{v:,.0f}" if pd.notna(v) else "")
                st.dataframe(ds,use_container_width=True,hide_index=True)

    # ── Công nợ placeholder
    st.markdown("---")
    sh("🏦 Công nợ (chưa cập nhật)")
    al("ai","📋 <b>Module Công nợ chưa có dữ liệu.</b> Cần bổ sung file:<br>"
           "&nbsp;&nbsp;• <b>AR Aging Report</b>: ngày tồn đọng, quá hạn từng dự án/KH<br>"
           "&nbsp;&nbsp;• <b>Lịch sử thanh toán</b>: thói quen NET 30/60/90 ngày<br>"
           "&nbsp;&nbsp;• <b>Hạn mức tín dụng</b>: so sánh dư nợ vs hạn mức phê duyệt<br>"
           "<b>Nhận xét từ dữ liệu hiện có:</b> Đơn hàng PKD dự án thường thanh toán theo tiến độ công trình "
           "(30–90 ngày sau nghiệm thu), đơn có PO/hợp đồng lớn rủi ro tập trung công nợ cao.")