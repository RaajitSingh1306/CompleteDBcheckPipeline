import streamlit as st
import pandas as pd
from auth import require_login, logout_button
from duplicate_engine import check_internal_duplicate, classify_status
from db_check import check_main_db
from db import add_company, SessionLocal, StagingCompany
from utils import norm_name, norm_web
from export import export_excel, get_user_status_summary, get_user_upload_counts

st.set_page_config("Company Validation Portal")

user, role = require_login()
st.sidebar.write(f"Logged in as {user}")
logout_button()

st.sidebar.markdown("### 👥 Upload Contributions")

user_counts = get_user_upload_counts()

if user_counts:
    for u, c in user_counts.items():
        st.sidebar.write(f"{u} — {c}")
else:
    st.sidebar.write("No uploads yet")


tab1, tab2, tab3, tab4 = st.tabs(["Submit", "Bulk Upload", "Uploads", "Admin Export"])

# ---------------- SUBMIT ----------------
with tab1:
    st.subheader("Submit Company")
    name = st.text_input("Company Name")
    website = st.text_input("Website")

    if st.button("Submit"):
        if not name or not website:
            st.warning("Company name and website cannot be empty.")
        else:
            dup = check_internal_duplicate(name, website)
            if dup:
                st.error(f"Duplicate already added by {dup.added_by}")
            else:
                hit = check_main_db(name, website)
                status = classify_status(hit)
                add_company(name, website, norm_name(name), norm_web(website), user, status)
                st.success(f"Saved with status: {status}")

# ---------------- BULK ----------------
with tab2:
    file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
    if file:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

        for _, row in df.iterrows():
            name = row.get("name")
            website = row.get("website")
            if not name or not website or str(name).lower() == "nan" or str(website).lower() == "nan":
                continue  # skip empty rows

            if not check_internal_duplicate(name, website):
                hit = check_main_db(name, website)
                status = classify_status(hit)
                add_company(name, website, norm_name(name), norm_web(website), user, status)

        st.success("Bulk upload completed")

# ---------------- MY UPLOADS ----------------
with tab3:
    st.subheader("📄 My Uploaded Companies")

    db = SessionLocal()
    rows = db.query(StagingCompany).all() if role == "admin" else \
           db.query(StagingCompany).filter(StagingCompany.added_by == user).all()
    db.close()

    if not rows:
        st.info("No uploads yet.")
    else:
        # Header row
        h1, h2, h3, h4, h5, h6 = st.columns([1,3,3,2,2,1])
        h1.write("No.")
        h2.write("Company Name")
        h3.write("Website")
        h4.write("Status")
        h5.write("Added By")
        h6.write("")

        for idx, r in enumerate(rows, start=1):
            col1, col2, col3, col4, col5, col6 = st.columns([1,3,3,2,2,1])

            col1.write(idx)
            col2.write(r.name)
            col3.write(r.website)
            col4.write(r.status)
            col5.write(r.added_by)

            # Delete permission
            if role == "admin" or r.added_by == user:
                if col6.button("🗑", key=f"del_{r.id}"):
                    from db import delete_company
                    delete_company(r.id)
                    st.rerun()

# ---------------- ADMIN EXPORT ----------------
with tab4:
    if role != "admin":
        st.warning("Admin only")
    else:
        st.subheader("📊 Staging Summary by User")
        summary = get_user_status_summary()

        if not summary:
            st.info("No data yet.")
        else:
            df_summary = (
                pd.DataFrame(summary)
                .fillna(0)
                .astype(int)
                .T
                .sort_index()
            )

            # Optional: enforce column order
            status_order = [
                "UNIQUE",
                "DB_MATCH_ACTIVE_N",
                "DB_MATCH_INACTIVE_N",
                "DB_MATCH_ACTIVE_Y",
                "DB_MATCH_INACTIVE_Y"
            ]
            df_summary = df_summary.reindex(columns=status_order, fill_value=0)

            st.dataframe(df_summary, use_container_width=True)

        st.subheader("📥 Select Data to Export")

        # ---- Checkboxes ----
        export_approved   = st.checkbox("Unique", True)
        export_active_n   = st.checkbox("DB Match Active (deleted=N)")
        export_inactive_n = st.checkbox("DB Match Inactive (deleted=N)")
        export_active_y   = st.checkbox("DB Match Active (deleted=Y)")
        export_inactive_y = st.checkbox("DB Match Inactive (deleted=Y)")

        # ---- Build selected list ----
        selected = []
        if export_approved:
            selected.append("UNIQUE")
        if export_active_n:
            selected.append("DB_MATCH_ACTIVE_N")
        if export_inactive_n:
            selected.append("DB_MATCH_INACTIVE_N")
        if export_active_y:
            selected.append("DB_MATCH_ACTIVE_Y")
        if export_inactive_y:
            selected.append("DB_MATCH_INACTIVE_Y")

        # ---- Generate & Download ----
        if st.button("Generate Excel Export"):
            if not selected:
                st.warning("Select at least one category")
            else:
                file_path = export_excel(selected)

                if file_path:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()

                    st.download_button(
                        "📥 Download Excel",
                        data=file_bytes,
                        file_name="company_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("Export ready")
                else:
                    st.info("No records found for selected categories")
