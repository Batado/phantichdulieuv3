"""Control workflow for NPP Business Risk Analytics.

Persistence:
- Use DATABASE_URL (PostgreSQL/Supabase) for durable Streamlit Cloud storage.
- Falls back to local SQLite for development only. Streamlit Cloud local files
  may be reset during a rebuild/restart; do not treat that fallback as durable.
The module stores control summaries and findings, not the uploaded workbook.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import (
    Column, Float, Integer, LargeBinary, MetaData, String, Table, Text,
    create_engine, delete, insert, select, update
)
from sqlalchemy.engine import Engine


META = MetaData()

SESSIONS = Table(
    "npp_control_sessions", META,
    Column("id", String(36), primary_key=True),
    Column("created_at", String(40), nullable=False),
    Column("operator", String(160), nullable=False),
    Column("file_name", String(255), nullable=False),
    Column("file_sha256", String(64), nullable=False),
    Column("sheet_name", String(160), nullable=True),
    Column("date_from", String(20), nullable=True),
    Column("date_to", String(20), nullable=True),
    Column("row_count", Integer, nullable=False, default=0),
    Column("npp_count", Integer, nullable=False, default=0),
    Column("revenue", Float, nullable=False, default=0),
    Column("quantity", Float, nullable=False, default=0),
    Column("risk_counts_json", Text, nullable=False, default="{}"),
    Column("finding_count", Integer, nullable=False, default=0),
    Column("note", Text, nullable=True),
)

FINDINGS = Table(
    "npp_control_findings", META,
    Column("id", String(36), primary_key=True),
    Column("session_id", String(36), nullable=False),
    Column("finding_code", String(50), nullable=False),
    Column("domain", String(100), nullable=False),
    Column("customer_key", String(160), nullable=True),
    Column("customer_name", String(255), nullable=False),
    Column("risk_level", String(40), nullable=False),
    Column("risk_score", Integer, nullable=False, default=0),
    Column("evidence", Text, nullable=False),
    Column("recommendation", Text, nullable=False),
    Column("status", String(60), nullable=False, default="Mới phát hiện"),
    Column("owner", String(160), nullable=True),
    Column("due_date", String(20), nullable=True),
    Column("explanation", Text, nullable=True),
    Column("resolution", Text, nullable=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

ACTIVITY = Table(
    "npp_control_activity", META,
    Column("id", String(36), primary_key=True),
    Column("session_id", String(36), nullable=True),
    Column("finding_id", String(36), nullable=True),
    Column("created_at", String(40), nullable=False),
    Column("actor", String(160), nullable=False),
    Column("action", String(100), nullable=False),
    Column("detail", Text, nullable=True),
)

ATTACHMENTS = Table(
    "npp_control_attachments", META,
    Column("id", String(36), primary_key=True),
    Column("finding_id", String(36), nullable=False),
    Column("file_name", String(255), nullable=False),
    Column("mime_type", String(160), nullable=True),
    Column("size_bytes", Integer, nullable=False, default=0),
    Column("content", LargeBinary, nullable=False),
    Column("uploaded_by", String(160), nullable=False),
    Column("created_at", String(40), nullable=False),
)


STATUS_OPTIONS = [
    "Mới phát hiện",
    "Đang xác minh",
    "Chờ giải trình",
    "Đề xuất xử lý",
    "Đang khắc phục",
    "Đã đóng",
    "Theo dõi thêm",
]
RISK_RANK = {"Rất cao": 5, "Cao": 4, "Theo dõi": 3, "Thấp": 2, "Chưa đủ dữ liệu": 1}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _number(value: Any) -> float:
    try:
        number = float(value)
        return number if pd.notna(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _secret_database_url() -> str:
    try:
        value = st.secrets.get("DATABASE_URL", "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.getenv("DATABASE_URL", "").strip()


def _normalize_database_url(raw: str) -> str:
    """Normalize Supabase URLs and safely encode special characters in passwords.

    A raw '@' in a password is otherwise mistaken for the end of user-info,
    causing DNS errors against a host such as '...@aws-...pooler.supabase.com'.
    """
    from urllib.parse import quote, unquote

    raw = (raw or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raise ValueError("DATABASE_URL không đúng định dạng URL PostgreSQL.")
    scheme, remainder = raw.split("://", 1)
    user_info, at_sign, host_and_path = remainder.rpartition("@")
    if not at_sign:
        raise ValueError("DATABASE_URL thiếu phần @HOST. Kiểm tra lại chuỗi kết nối Supabase.")
    host, slash, path = host_and_path.partition("/")
    username, colon, password = user_info.partition(":")
    if not colon or not username or not host:
        raise ValueError("DATABASE_URL thiếu username, password hoặc hostname.")
    # Decode first so already URL-encoded passwords are not double-encoded.
    # Splitting at the final @ before parsing the host also supports raw @ and /
    # characters in the password; the password is then percent-encoded safely.
    username = quote(unquote(username), safe="")
    password = quote(unquote(password), safe="")
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+psycopg"
    suffix = ("/" + path) if slash else ""
    return f"{scheme}://{username}:{password}@{host}{suffix}"


@st.cache_resource(show_spinner=False)
def _engine_and_mode() -> tuple[Engine, str]:
    raw_url = _secret_database_url()
    if raw_url:
        url = _normalize_database_url(raw_url)
        engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800)
        mode = "PostgreSQL"
    else:
        engine = create_engine(
            "sqlite:///./npp_control_center.db",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        mode = "SQLite cục bộ"
    META.create_all(engine)
    return engine, mode


def _db_ready() -> tuple[Engine | None, str | None, str | None]:
    try:
        engine, mode = _engine_and_mode()
        with engine.connect() as conn:
            conn.execute(select(SESSIONS.c.id).limit(1))
        return engine, mode, None
    except Exception as exc:
        return None, None, str(exc)


def _log(conn, actor: str, action: str, detail: str,
         session_id: str | None = None, finding_id: str | None = None) -> None:
    conn.execute(insert(ACTIVITY).values(
        id=str(uuid.uuid4()),
        session_id=session_id,
        finding_id=finding_id,
        created_at=_now(),
        actor=actor or "Người dùng",
        action=action,
        detail=(detail or "")[:5000],
    ))


def _safe_rows(frame: pd.DataFrame | None, limit: int = 8) -> list[dict]:
    if frame is None or frame.empty:
        return []
    view = frame.head(limit).copy()
    view = view.astype(object).where(pd.notna(view), None)
    return view.to_dict(orient="records")


def _make_findings(data: dict) -> list[dict]:
    risk = data.get("risk_summary")
    if risk is None or risk.empty:
        return []

    warehouse = data.get("warehouse_evidence", pd.DataFrame())
    vehicle = data.get("customer_vehicle", pd.DataFrame())
    day_shared = data.get("vehicle_day_shared", pd.DataFrame())
    period_shared = data.get("vehicle_period_shared", pd.DataFrame())
    address_pairs = data.get("address_pairs", pd.DataFrame())
    address_shared = data.get("address_shared", pd.DataFrame())
    monthly = data.get("customer_monthly_review", pd.DataFrame())
    anomalies = data.get("monthly_anomalies", pd.DataFrame())
    shifts = data.get("product_shift_review", pd.DataFrame())

    def group_by_customer(frame: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
        if frame is None or frame.empty or "_customer_key" not in frame.columns:
            return {}
        return {
            str(key): group
            for key, group in frame.groupby("_customer_key", sort=False)
        }

    # Build lookup maps once. Avoid rescanning the entire transaction dataset
    # for every distributor when a workbook contains many NPP.
    warehouse_map = group_by_customer(warehouse)
    monthly_map = group_by_customer(monthly)
    anomaly_map = group_by_customer(anomalies)

    vehicle_valid = pd.DataFrame()
    if vehicle is not None and not vehicle.empty and {
        "_customer_key", "_bien_so", "_bien_so_hop_le"
    }.issubset(vehicle.columns):
        vehicle_valid = vehicle[vehicle["_bien_so_hop_le"].fillna(False)].copy()

    day_events = pd.DataFrame()
    if (
        not vehicle_valid.empty and day_shared is not None and not day_shared.empty
        and {"_bien_so", "_ngay_only"}.issubset(vehicle_valid.columns)
        and {"_bien_so", "_ngay_only"}.issubset(day_shared.columns)
    ):
        day_events = vehicle_valid.merge(
            day_shared[["_bien_so", "_ngay_only"]].drop_duplicates(),
            on=["_bien_so", "_ngay_only"], how="inner"
        )
    day_map = group_by_customer(day_events)

    period_events = pd.DataFrame()
    if (
        not vehicle_valid.empty and period_shared is not None and not period_shared.empty
        and "_bien_so" in vehicle_valid.columns and "_bien_so" in period_shared.columns
    ):
        period_events = vehicle_valid.merge(
            period_shared[["_bien_so"]].drop_duplicates(),
            on="_bien_so", how="inner"
        )
    period_map = group_by_customer(period_events)

    address_events = pd.DataFrame()
    if (
        address_pairs is not None and not address_pairs.empty
        and address_shared is not None and not address_shared.empty
        and {"_customer_key", "_dia_chi_norm"}.issubset(address_pairs.columns)
        and "_dia_chi_norm" in address_shared.columns
    ):
        address_events = address_pairs.merge(
            address_shared[["_dia_chi_norm", "So_NPP", "Danh_sach_NPP"]].drop_duplicates(),
            on="_dia_chi_norm", how="inner"
        )
    address_map = group_by_customer(address_events)

    shift_map: dict[str, list[dict]] = {}
    if (
        shifts is not None and not shifts.empty
        and {"_customer_key_A", "_customer_key_B"}.issubset(shifts.columns)
    ):
        for item in shifts.to_dict(orient="records"):
            for key_column in ["_customer_key_A", "_customer_key_B"]:
                key_value = _text(item.get(key_column))
                if key_value:
                    shift_map.setdefault(key_value, []).append(item)

    def add(record: dict, code: str, domain: str, level: str,
            evidence: str, recommendation: str) -> None:
        record_copy = {
            "finding_code": code,
            "domain": domain,
            "risk_level": level,
            "risk_score": int(_number(record.get("Điểm sàng lọc", 0))),
            "evidence": evidence[:12000],
            "recommendation": recommendation,
        }
        findings.append({
            **record_copy,
            "customer_key": _text(record.get("Mã khách hàng")),
            "customer_name": _text(record.get("NPP")) or "(Chưa có tên NPP)",
        })

    findings: list[dict] = []
    for _, row in risk.iterrows():
        record = row.to_dict()
        key = _text(record.get("Mã khách hàng"))
        name = _text(record.get("NPP")) or "(Chưa có tên NPP)"
        npp_level = _text(record.get("Mức độ")) or "Chưa đủ dữ liệu"

        wh = warehouse_map.get(str(key), pd.DataFrame())
        if _number(record.get("Dòng kho ngoài danh sách")) > 0:
            sample = []
            for _, x in wh.head(8).iterrows():
                sample.append(
                    f"CT {_text(x.get('_chung_tu'))}; kho {_text(x.get('_ma_kho'))} "
                    f"({_text(x.get('_ten_kho'))}); vùng {_text(x.get('_vung'))}; "
                    f"địa chỉ {_text(x.get('_dia_chi'))}; kết quả {_text(x.get('_doi_chieu_kho_tong_hop'))}"
                )
            evidence = (
                f"NPP {name}: {int(_number(record.get('Dòng kho ngoài danh sách')))} chứng từ "
                "có mã kho ngoài ma trận địa chỉ hoặc có mâu thuẫn với ghi chú/danh sách kho. "
                + " | ".join(sample)
            )
            add(record, "NPP-WH-01", "Kho lấy hàng", npp_level, evidence,
                "Đối chiếu địa chỉ đăng ký, mã kho 3 số đầu chứng từ, phiếu xuất kho, tồn kho, "
                "tuyến đường, điều phối và phê duyệt ngoại lệ. Chỉ kết luận sau khi xác minh.")

        day_rows = day_map.get(str(key), pd.DataFrame())
        if _number(record.get("Dòng xe dùng chung cùng ngày")) > 0:
            sample = []
            for _, x in day_rows.head(8).iterrows():
                sample.append(
                    f"Biển số {_text(x.get('_bien_so_goc'))}; ngày {_text(x.get('_ngay_only'))}; "
                    f"chứng từ {_text(x.get('_chung_tu'))}; kho {_text(x.get('_ma_kho'))}"
                )
            evidence = (
                f"NPP {name}: có {int(_number(record.get('Dòng xe dùng chung cùng ngày')))} sự kiện "
                "biển số xe khách hàng xuất hiện ở từ hai NPP trong cùng ngày. "
                + " | ".join(sample)
            )
            add(record, "NPP-VEH-01", "Vận chuyển", npp_level, evidence,
                "Kiểm tra giờ lấy hàng, lộ trình, chủ xe, tài xế, người nhận, số chứng từ "
                "và khả năng xe giao/nhận nhiều điểm trong ngày.")

        period_rows = period_map.get(str(key), pd.DataFrame())
        if _number(record.get("Dòng xe dùng chung nhiều ngày")) > 0:
            sample = []
            for _, x in period_rows.head(8).iterrows():
                sample.append(
                    f"Biển số {_text(x.get('_bien_so_goc'))}; ngày {_text(x.get('_ngay_only'))}; "
                    f"chứng từ {_text(x.get('_chung_tu'))}"
                )
            evidence = (
                f"NPP {name}: có {int(_number(record.get('Dòng xe dùng chung nhiều ngày')))} liên kết "
                "biển số với NPP khác qua nhiều ngày. " + " | ".join(sample)
            )
            add(record, "NPP-VEH-02", "Vận chuyển", npp_level, evidence,
                "Đối chiếu lịch sử xe, hợp đồng/thỏa thuận vận chuyển, tài xế, chủ phương tiện "
                "và mối liên hệ giữa các NPP có cùng xe.")

        addr_rows = address_map.get(str(key), pd.DataFrame())
        if _number(record.get("Dòng địa chỉ trùng")) > 0:
            sample = []
            for _, x in addr_rows.head(5).iterrows():
                sample.append(
                    f"Địa chỉ {_text(x.get('_dia_chi'))}; cùng địa chỉ với {_text(x.get('Danh_sach_NPP'))}"
                )
            add(record, "NPP-ADDR-01", "Địa điểm NPP", npp_level,
                f"NPP {name}: phát hiện địa chỉ dùng chung với NPP khác. " + " | ".join(sample),
                "Đối chiếu hồ sơ pháp lý, địa chỉ đăng ký kinh doanh, kho/điểm bán thực tế, "
                "người đại diện và quan hệ sở hữu/vận hành giữa các NPP.")

        monthly_rows = monthly_map.get(str(key), pd.DataFrame())
        if _text(record.get("Biến động kinh doanh cần kiểm tra")).lower() in {"true", "1", "yes"}:
            detail = ""
            if not monthly_rows.empty:
                x = monthly_rows.iloc[0]
                detail = (
                    f" Mẫu hình: {_text(x.get('Mẫu hình'))}; doanh thu kỳ trước "
                    f"{_number(x.get('Doanh thu kỳ trước')):,.0f}, kỳ sau "
                    f"{_number(x.get('Doanh thu kỳ sau')):,.0f}; sản lượng kỳ trước "
                    f"{_number(x.get('Sản lượng kỳ trước')):,.2f}, kỳ sau "
                    f"{_number(x.get('Sản lượng kỳ sau')):,.2f}; biến động SL "
                    f"{_text(x.get('Biến động sản lượng %'))}%."
                )
            add(record, "NPP-SALES-01", "Biến động kinh doanh", npp_level,
                f"NPP {name}: doanh thu/sản lượng thay đổi mạnh giữa hai kỳ." + detail,
                "Kiểm tra nguyên nhân thay đổi địa bàn, tồn kho, công nợ, chính sách bán hàng, "
                "nguồn cung, thay đổi NPP phụ trách và nhu cầu tiêu thụ thực tế.")

        shift_rows = pd.DataFrame(shift_map.get(str(key), [])[:8])
        if bool(record.get("Liên quan dịch chuyển mặt hàng", False)):
            samples = []
            for _, x in shift_rows.iterrows():
                samples.append(
                    f"Mã hàng {_text(x.get('Mã hàng'))}; vùng {_text(x.get('Vùng'))}; "
                    f"NPP giảm {_text(x.get('NPP giảm'))}; NPP tăng {_text(x.get('NPP tăng'))}; "
                    f"mức bù trừ {_number(x.get('Mức bù trừ tương đối %')):.1f}%"
                )
            add(record, "NPP-SHIFT-01", "Liên kết NPP/mặt hàng", npp_level,
                f"NPP {name}: nằm trong cặp NPP cùng vùng/cùng mã hàng có biến động sản lượng trái chiều. "
                + " | ".join(samples),
                "Đối chiếu địa bàn phân phối, khách hàng cuối, chính sách bán hàng, lịch sử giao dịch "
                "và quyết định điều chuyển. Đây là tín hiệu cần xác minh, không phải bằng chứng chuyển giao.")

        anomaly_rows = anomaly_map.get(str(key), pd.DataFrame())
        if _number(record.get("Số tháng biến động đột ngột")) > 0:
            samples = []
            for _, x in anomaly_rows.head(8).iterrows():
                samples.append(
                    f"Tháng {_text(x.get('Tháng bất thường'))}: {_text(x.get('Loại bất thường'))}; "
                    f"SL {_number(x.get('Sản lượng tháng')):,.2f}; DT {_number(x.get('Doanh thu tháng')):,.0f}"
                )
            add(record, "NPP-SALES-02", "Biến động theo tháng", npp_level,
                f"NPP {name}: có {int(_number(record.get('Số tháng biến động đột ngột')))} tháng "
                "tăng/giảm đột ngột so với trung vị 3 tháng trước. " + " | ".join(samples),
                "Kiểm tra đơn hàng, chứng từ, tồn kho, thời điểm ghi nhận, tiến độ giao hàng, "
                "công nợ và các chương trình kinh doanh tại tháng phát sinh.")

        if npp_level == "Chưa đủ dữ liệu" and not any(
            x["customer_key"] == key for x in findings
        ):
            add(record, "NPP-DATA-01", "Chất lượng dữ liệu", "Chưa đủ dữ liệu",
                f"NPP {name}: chưa đạt điều kiện dữ liệu để kết luận mức rủi ro. "
                f"Độ phủ dữ liệu: {_number(record.get('Độ phủ dữ liệu')):.0%}.",
                "Bổ sung địa chỉ, ngày chứng từ, số chứng từ, hình thức vận chuyển, biển số "
                "và thông tin kho trước khi đánh giá lại.")

    return findings


def _insert_findings(conn, session_id: str, records: list[dict], actor: str) -> None:
    now = _now()
    for item in records:
        conn.execute(insert(FINDINGS).values(
            id=str(uuid.uuid4()),
            session_id=session_id,
            finding_code=item["finding_code"],
            domain=item["domain"],
            customer_key=item["customer_key"],
            customer_name=item["customer_name"],
            risk_level=item["risk_level"],
            risk_score=item["risk_score"],
            evidence=item["evidence"],
            recommendation=item["recommendation"],
            status="Mới phát hiện",
            owner="",
            due_date="",
            explanation="",
            resolution="",
            created_at=now,
            updated_at=now,
        ))
    _log(conn, actor, "Tạo phát hiện tự động",
         f"Đã tạo {len(records)} phát hiện từ kết quả phân tích.", session_id=session_id)


def _read_table(engine: Engine, table: Table, where=None, order_by=None, limit=500) -> list[dict]:
    stmt = select(table)
    if where is not None:
        stmt = stmt.where(where)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    stmt = stmt.limit(limit)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(x) for x in rows]


def _session_findings(data: dict) -> list[dict]:
    risk = data["risk_summary"]
    levels = risk["Mức độ"].value_counts().to_dict() if not risk.empty else {}
    dates = data.get("monthly_sales", pd.DataFrame())
    months = dates["_thang"].dropna().astype(str).tolist() if dates is not None and not dates.empty else []
    if not months:
        return []
    return [
        {"name": str(level), "count": int(count)}
        for level, count in levels.items()
    ]


def _summary_payload(data: dict, session_id: str, operator: str, file_name: str,
                     file_bytes: bytes, note: str) -> dict:
    filtered = data.get("filtered", pd.DataFrame())
    risk = data.get("risk_summary", pd.DataFrame())
    monthly = data.get("monthly_sales", pd.DataFrame())
    months = monthly["_thang"].dropna().astype(str).tolist() if monthly is not None and not monthly.empty else []
    counts = risk["Mức độ"].value_counts().to_dict() if risk is not None and not risk.empty else {}
    return {
        "id": session_id,
        "created_at": _now(),
        "operator": operator,
        "file_name": file_name or "workbook.xlsx",
        "file_sha256": hashlib.sha256(file_bytes).hexdigest(),
        "sheet_name": _text(data.get("sheet_name")),
        "date_from": min(months) if months else "",
        "date_to": max(months) if months else "",
        "row_count": int(len(filtered)) if filtered is not None else 0,
        "npp_count": int(risk["Mã khách hàng"].nunique()) if risk is not None and not risk.empty and "Mã khách hàng" in risk.columns else 0,
        "revenue": _number(data.get("revenue", 0)),
        "quantity": _number(data.get("quantity", 0)),
        "risk_counts_json": json.dumps(counts, ensure_ascii=False),
        "finding_count": 0,
        "note": note[:5000],
    }


def _render_db_banner(mode: str) -> None:
    if mode == "SQLite cục bộ":
        st.warning(
            "Đang dùng SQLite cục bộ. Phù hợp thử nghiệm trên máy cá nhân; "
            "dữ liệu có thể mất khi Streamlit Cloud khởi động lại hoặc triển khai lại. "
            "Muốn lưu hồ sơ lâu dài trên Cloud, cần cấu hình DATABASE_URL của PostgreSQL/Supabase."
        )
    else:
        st.success("Đã kết nối PostgreSQL. Phiên phân tích, phát hiện và nhật ký được lưu trong cơ sở dữ liệu ngoài.")


def render_control_center(
    *,
    data_ready: bool = False,
    file_name: str = "",
    file_bytes: bytes = b"",
    data: dict | None = None,
) -> None:
    """Render session archive, finding register, evidence, and audit history."""
    st.markdown('<div class="section-title">HỒ SƠ KIỂM SOÁT & SỔ PHÁT HIỆN RỦI RO</div>', unsafe_allow_html=True)
    st.caption(
        "Lưu kết quả phân tích, tạo phát hiện theo từng dấu hiệu, ghi nhận giải trình, "
        "người phụ trách, hạn xử lý và lịch sử cập nhật. Workbook gốc không được lưu vào cơ sở dữ liệu."
    )
    engine, mode, error = _db_ready()
    if engine is None:
        st.error(f"Không khởi tạo được cơ sở dữ liệu kiểm soát: {error}")
        st.info("Kiểm tra requirements.txt và DATABASE_URL nếu đang triển khai trên Streamlit Cloud.")
        return
    _render_db_banner(mode)

    data = data or {}
    session_tab, finding_tab, history_tab, log_tab = st.tabs([
        "Lưu phiên phân tích",
        "Sổ phát hiện & giải trình",
        "Lịch sử phiên",
        "Nhật ký hoạt động",
    ])

    with session_tab:
        if not data_ready:
            st.info("Tải workbook và chạy phân tích để tạo một phiên kiểm soát mới. Các phiên đã lưu vẫn có thể xem ở hai tab bên cạnh.")
        else:
            risk = data.get("risk_summary", pd.DataFrame())
            total_npp = int(risk["Mã khách hàng"].nunique()) if not risk.empty and "Mã khách hàng" in risk.columns else 0
            levels = risk["Mức độ"].value_counts().to_dict() if not risk.empty else {}
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("NPP được đánh giá", f"{total_npp:,}")
            c2.metric("Phát hiện dự kiến", f"{len(_make_findings(data)):,}")
            c3.metric("NPP cao/rất cao", f"{sum(int(levels.get(x, 0)) for x in ['Cao', 'Rất cao']):,}")
            c4.metric("NPP chưa đủ dữ liệu", f"{int(levels.get('Chưa đủ dữ liệu', 0)):,}")

            with st.form("npp_save_session_form", clear_on_submit=False):
                operator = st.text_input("Người thực hiện", value=st.session_state.get("npp_operator", "Nhân viên KSNB"), key="npp_operator")
                note = st.text_area("Ghi chú phiên kiểm soát", placeholder="Ví dụ: Rà soát hoạt động NPP tháng 01–11/2026...")
                confirm = st.checkbox("Tôi xác nhận lưu thông tin tổng hợp và phát hiện; không lưu workbook gốc.")
                submitted = st.form_submit_button("LƯU PHIÊN & TẠO SỔ PHÁT HIỆN", type="primary", disabled=not confirm)
            if submitted:
                session_id = str(uuid.uuid4())
                records = _make_findings(data)
                payload = _summary_payload(data, session_id, operator.strip() or "Nhân viên KSNB", file_name, file_bytes, note)
                payload["finding_count"] = len(records)
                try:
                    with engine.begin() as conn:
                        conn.execute(insert(SESSIONS).values(**payload))
                        _insert_findings(conn, session_id, records, payload["operator"])
                        _log(
                            conn, payload["operator"], "Lưu phiên phân tích",
                            f"File: {payload['file_name']}; số dòng: {payload['row_count']}; "
                            f"NPP: {payload['npp_count']}; phát hiện: {len(records)}.",
                            session_id=session_id,
                        )
                    st.session_state["npp_last_session_id"] = session_id
                    st.success(f"Đã lưu phiên {session_id[:8]} với {len(records)} phát hiện.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Không lưu được phiên phân tích: {exc}")

    with finding_tab:
        all_findings = _read_table(engine, FINDINGS, order_by=FINDINGS.c.updated_at.desc(), limit=3000)
        if not all_findings:
            st.info("Chưa có phát hiện nào. Lưu một phiên phân tích để tự tạo sổ phát hiện.")
        else:
            frame = pd.DataFrame(all_findings)
            f1, f2, f3 = st.columns(3)
            statuses = sorted(frame["status"].dropna().unique().tolist())
            risks = sorted(frame["risk_level"].dropna().unique().tolist())
            status_filter = f1.multiselect("Trạng thái", statuses, default=statuses, key="cc_status_filter")
            risk_filter = f2.multiselect("Mức rủi ro", risks, default=risks, key="cc_risk_filter")
            search = f3.text_input("Tìm NPP / mã phát hiện", key="cc_finding_search")
            view = frame[
                frame["status"].isin(status_filter)
                & frame["risk_level"].isin(risk_filter)
            ].copy()
            if search.strip():
                q = search.strip().casefold()
                view = view[
                    view.apply(
                        lambda r: q in " ".join(str(r.get(c, "")) for c in [
                            "customer_name", "customer_key", "finding_code", "domain"
                        ]).casefold(),
                        axis=1
                    )
                ]
            st.dataframe(
                view[[
                    "finding_code", "domain", "customer_name", "risk_level",
                    "risk_score", "status", "owner", "due_date", "updated_at"
                ]].rename(columns={
                    "finding_code": "Mã phát hiện", "domain": "Mảng",
                    "customer_name": "NPP", "risk_level": "Mức độ",
                    "risk_score": "Điểm NPP", "status": "Trạng thái",
                    "owner": "Người phụ trách", "due_date": "Hạn xử lý",
                    "updated_at": "Cập nhật",
                }),
                use_container_width=True, hide_index=True
            )

            choices = view["id"].tolist()
            if choices:
                def label_for(fid: str) -> str:
                    row = view[view["id"] == fid].iloc[0]
                    return f"{row['finding_code']} | {row['customer_name']} | {row['domain']} | {row['status']}"
                selected_id = st.selectbox(
                    "Chọn phát hiện để cập nhật",
                    choices,
                    format_func=label_for,
                    key="cc_selected_finding"
                )
                selected = frame[frame["id"] == selected_id].iloc[0].to_dict()
                st.markdown("#### Chi tiết phát hiện")
                left, right = st.columns(2)
                with left:
                    st.write(f"**NPP:** {selected['customer_name']}")
                    st.write(f"**Nhóm:** {selected['domain']} · **Mã:** {selected['finding_code']}")
                    st.write(f"**Mức độ:** {selected['risk_level']} · **Điểm:** {selected['risk_score']}/100")
                    st.write("**Bằng chứng trích từ dữ liệu:**")
                    st.write(selected["evidence"])
                with right:
                    st.write("**Hướng xác minh đề xuất:**")
                    st.write(selected["recommendation"])

                old_due = selected.get("due_date") or ""
                try:
                    due_default = date.fromisoformat(old_due) if old_due else date.today()
                except ValueError:
                    due_default = date.today()
                status_index = STATUS_OPTIONS.index(selected["status"]) if selected["status"] in STATUS_OPTIONS else 0
                with st.form(f"npp_edit_finding_{selected_id}"):
                    new_status = st.selectbox("Trạng thái xử lý", STATUS_OPTIONS, index=status_index)
                    owner = st.text_input("Người phụ trách", value=selected.get("owner") or "")
                    due = st.date_input("Hạn xử lý", value=due_default)
                    explanation = st.text_area("Giải trình / nguyên nhân", value=selected.get("explanation") or "")
                    resolution = st.text_area("Kết quả xác minh / biện pháp khắc phục", value=selected.get("resolution") or "")
                    actor = st.text_input("Người cập nhật", value=st.session_state.get("npp_operator", "Nhân viên KSNB"), key=f"cc_actor_{selected_id}")
                    save_update = st.form_submit_button("LƯU CẬP NHẬT")
                if save_update:
                    now = _now()
                    actor_value = actor.strip() or "Người dùng"
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                update(FINDINGS).where(FINDINGS.c.id == selected_id).values(
                                    status=new_status,
                                    owner=owner.strip(),
                                    due_date=due.isoformat() if due else "",
                                    explanation=explanation,
                                    resolution=resolution,
                                    updated_at=now,
                                )
                            )
                            _log(
                                conn, actor_value, "Cập nhật phát hiện",
                                f"{selected['finding_code']} | {selected['customer_name']} | trạng thái: {new_status}",
                                session_id=selected["session_id"], finding_id=selected_id
                            )
                        st.success("Đã cập nhật phát hiện.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Không cập nhật được phát hiện: {exc}")

                st.markdown("#### Tài liệu / bằng chứng đính kèm")
                attachment = st.file_uploader(
                    "Tải file minh chứng (PDF, Excel, Word, ảnh)",
                    type=["pdf", "xlsx", "xls", "docx", "doc", "png", "jpg", "jpeg"],
                    key=f"cc_attachment_{selected_id}"
                )
                actor_upload = st.text_input(
                    "Người tải lên", value=st.session_state.get("npp_operator", "Nhân viên KSNB"),
                    key=f"cc_upload_actor_{selected_id}"
                )
                if st.button("LƯU FILE MINH CHỨNG", key=f"cc_save_attachment_{selected_id}", disabled=attachment is None):
                    payload = attachment.getvalue() if attachment else b""
                    if len(payload) > 10 * 1024 * 1024:
                        st.error("Mỗi file minh chứng tối đa 10 MB.")
                    elif payload:
                        try:
                            with engine.begin() as conn:
                                conn.execute(insert(ATTACHMENTS).values(
                                    id=str(uuid.uuid4()),
                                    finding_id=selected_id,
                                    file_name=attachment.name[:255],
                                    mime_type=attachment.type or "",
                                    size_bytes=len(payload),
                                    content=payload,
                                    uploaded_by=actor_upload.strip() or "Người dùng",
                                    created_at=_now(),
                                ))
                                _log(
                                    conn, actor_upload.strip() or "Người dùng",
                                    "Tải bằng chứng",
                                    attachment.name,
                                    session_id=selected["session_id"],
                                    finding_id=selected_id,
                                )
                            st.success("Đã lưu file minh chứng vào cơ sở dữ liệu.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Không lưu được file minh chứng: {exc}")

                attachments = _read_table(
                    engine, ATTACHMENTS,
                    where=ATTACHMENTS.c.finding_id == selected_id,
                    order_by=ATTACHMENTS.c.created_at.desc(),
                    limit=50
                )
                if attachments:
                    st.markdown("**File đã lưu**")
                    for item in attachments:
                        st.download_button(
                            f"Tải {item['file_name']} ({item['size_bytes'] / 1024:.0f} KB)",
                            data=item["content"],
                            file_name=item["file_name"],
                            mime=item.get("mime_type") or "application/octet-stream",
                            key=f"cc_download_{item['id']}",
                        )

            csv_bytes = view.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "TẢI SỔ PHÁT HIỆN (CSV)",
                data=csv_bytes,
                file_name="So_phat_hien_rui_ro_NPP.csv",
                mime="text/csv",
                key="cc_export_findings",
            )

    with history_tab:
        sessions = _read_table(engine, SESSIONS, order_by=SESSIONS.c.created_at.desc(), limit=300)
        if not sessions:
            st.info("Chưa có phiên phân tích được lưu.")
        else:
            sf = pd.DataFrame(sessions)
            sf["risk_counts"] = sf["risk_counts_json"].map(
                lambda x: json.loads(x) if x else {}
            )
            st.dataframe(sf[[
                "created_at", "operator", "file_name", "sheet_name",
                "date_from", "date_to", "row_count", "npp_count",
                "revenue", "quantity", "finding_count"
            ]].rename(columns={
                "created_at": "Thời điểm", "operator": "Người thực hiện",
                "file_name": "Tên file", "sheet_name": "Sheet",
                "date_from": "Từ tháng", "date_to": "Đến tháng",
                "row_count": "Số dòng", "npp_count": "Số NPP",
                "revenue": "Doanh thu", "quantity": "Sản lượng",
                "finding_count": "Số phát hiện",
            }), use_container_width=True, hide_index=True)
            session_ids = [x["id"] for x in sessions]
            selected_session = st.selectbox(
                "Xem phát hiện theo phiên",
                session_ids,
                format_func=lambda sid: next(
                    f"{x['created_at']} | {x['file_name']} | {sid[:8]}"
                    for x in sessions if x["id"] == sid
                ),
                key="cc_selected_session"
            )
            if selected_session:
                session_findings = _read_table(
                    engine, FINDINGS,
                    where=FINDINGS.c.session_id == selected_session,
                    order_by=FINDINGS.c.risk_score.desc(),
                    limit=1000
                )
                st.dataframe(pd.DataFrame(session_findings), use_container_width=True, hide_index=True)
                selected_meta = next(x for x in sessions if x["id"] == selected_session)
                st.caption(
                    f"SHA-256 file: {selected_meta['file_sha256']} · "
                    f"Người lưu: {selected_meta['operator']} · "
                    "Workbook gốc không được lưu trong cơ sở dữ liệu."
                )

    with log_tab:
        logs = _read_table(engine, ACTIVITY, order_by=ACTIVITY.c.created_at.desc(), limit=1000)
        if not logs:
            st.info("Chưa có nhật ký hoạt động.")
        else:
            log_frame = pd.DataFrame(logs).rename(columns={
                "created_at": "Thời gian", "actor": "Người thực hiện",
                "action": "Hành động", "detail": "Chi tiết",
                "session_id": "Mã phiên", "finding_id": "Mã phát hiện",
            })
            st.dataframe(
                log_frame[["Thời gian", "Người thực hiện", "Hành động", "Chi tiết", "Mã phiên", "Mã phát hiện"]],
                use_container_width=True, hide_index=True
            )
            st.download_button(
                "TẢI NHẬT KÝ (CSV)",
                data=log_frame.to_csv(index=False).encode("utf-8-sig"),
                file_name="Nhat_ky_kiem_soat_NPP.csv",
                mime="text/csv",
                key="cc_export_logs",
            )
