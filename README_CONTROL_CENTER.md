# NPP Business Risk Analytics

Streamlit application for distributor (NPP) business-risk screening and internal-control follow-up.

## Main application

Run locally:

    pip install -r requirements.txt
    streamlit run app_v3.py

## New control-management functions

The **Quản lý kiểm soát** tab adds:
- Save an analysis session with file name, SHA-256 hash, date range, summary KPIs and risk-level counts.
- Auto-create findings by NPP and control theme: warehouse, shared vehicle on the same day, shared vehicle across multiple days, shared address, monthly business movement, product-shift signals, monthly spikes/drops and data-quality gaps.
- Assign an owner, due date and workflow status to each finding.
- Record explanations and verification / corrective-action results.
- Attach supporting files to a finding (maximum 10 MB per file).
- View archived sessions, findings by session and user activity logs.
- Export the finding register and activity log to CSV.

The original workbook is **not** copied into the control database. The app stores a file hash and summary metadata, plus evidence descriptions and files explicitly attached by the user.

## Database setup

### Local development

If DATABASE_URL is not configured, the app uses:

    sqlite:///./npp_control_center.db

This is for local testing only.

### Streamlit Community Cloud (recommended)

For persistent records, provision a PostgreSQL database (for example, Supabase PostgreSQL), then add a secret named DATABASE_URL in:

**Streamlit Cloud → App → Settings → Secrets**

Example format (replace every placeholder with your real database details):

    DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"

Do not commit a real secrets.toml, password, token or database URL to GitHub. The app automatically creates its tables on first run:
- npp_control_sessions
- npp_control_findings
- npp_control_activity
- npp_control_attachments

The SQLite fallback on Streamlit Cloud may be lost when the app container is restarted or rebuilt. Configure PostgreSQL before using this as the official long-term audit log.

## Deployment

The Streamlit app entry point remains app_v3.py. When the GitHub repository is connected to Streamlit Cloud, commits to main should be picked up by the deployment. If it does not update automatically, open the app management panel and reboot it.

## Important control limitations

- The risk score is a screening priority, not a finding of fraud or policy breach.
- Shared vehicles, shared addresses, warehouse exceptions and sales changes require corroborating documents and explanation before a conclusion.
- The Người thực hiện / Người cập nhật fields record the operator name entered by the user. They are not a secure authentication system or role-based access control. Use Streamlit access controls or add an authenticated identity provider before exposing sensitive records to a wider audience.
- Evidence files are stored in the configured database. Confirm database access controls, retention and backup arrangements before using confidential company documents.
