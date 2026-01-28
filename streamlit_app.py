import streamlit as st
import pandas as pd
from auth import require_login, logout_button
from duplicate_engine import check_internal_duplicate, classify_status, purge_user_duplicates
from utils import clean_text
from db_check import fetch_db_snapshot, check_main_db
from db import add_company, SessionLocal, StagingCompany, delete_company
from utils import norm_name, norm_web
from export import export_excel, get_user_status_summary, get_user_upload_counts

st.set_page_config("Company Validation Portal", layout="wide")

# ---------------- LOGIN ----------------
user, role = require_login()
st.sidebar.write(f"👤 Logged in as: {user}")
logout_button()

# ---------------- LOAD MAIN DB SNAPSHOT ONCE ----------------
if "main_db" not in st.session_state:
    st.session_state.main_db = fetch_db_snapshot()

main_db_df = st.session_state.main_db

# ---------------- SIDEBAR USER STATS ----------------
st.sidebar.markdown("### 👥 Upload Contributions")
counts = get_user_upload_counts()
if counts:
    for u, c in counts.items():
        st.sidebar.write(f"{u} — {c}")
else:
    st.sidebar.write("No uploads yet")

# ---------------- TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs(["Submit", "Bulk Upload", "My Uploads", "Admin Export"])

# =========================================================
# TAB 1 — SUBMIT SINGLE COMPANY
# =========================================================
with tab1:
    st.subheader("Submit Company")

    name = st.text_input("Company Name")
    website = st.text_input("Website")

    if st.button("Submit Company"):
        name = clean_text(name)
        website = clean_text(website)

        if not name or not website:
            st.warning("Both fields required")
        else:
            dup = check_internal_duplicate(name, website)

            if dup["is_duplicate"]:
                status = "DUPLICATE_USER"
                owner = dup["original_user"]
                st.warning(f"⚠️ Duplicate already uploaded by {owner}")
            else:
                hit = check_main_db(name, website, main_db_df)
                status = classify_status(hit)
                owner = None
                st.success(f"✅ Saved with status: {status}")

            add_company(
                name=clean_text(name),
                website=clean_text(website),
                norm_name=norm_name(name),
                norm_web=norm_web(website),
                added_by=user,
                status=status,
                duplicate_owner=owner
            )

# =========================================================
# TAB 2 — BULK UPLOAD + ANALYTICS
# =========================================================
with tab2:
    st.subheader("📂 Bulk Upload Companies")

    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        df.columns = df.columns.str.lower().str.strip()

        if "name" not in df.columns or "website" not in df.columns:
            st.error("File must contain 'name' and 'website' columns")
        else:
            st.success(f"{len(df)} rows loaded")

            if st.button("🔍 Analyze File"):
                results = []
                progress = st.progress(0)

                for i, row in df.iterrows():
                    name = clean_text(row["name"])
                    website = clean_text(row["website"])

                    # Skip invalid rows
                    if not name or not website:
                        continue

                    dup = check_internal_duplicate(name, website)
                    if dup["is_duplicate"]:
                        status = "DUPLICATE_USER"
                        owner = dup["original_user"]
                    else:
                        hit = check_main_db(name, website, main_db_df)
                        status = classify_status(hit)
                        owner = None

                    results.append({
                        "name": name,
                        "website": website,
                        "status": status,
                        "duplicate_owner": owner
                    })

                    progress.progress((i + 1) / len(df))

                st.session_state.bulk_results = pd.DataFrame(results)

    # ---- SHOW ANALYTICS ----
    if "bulk_results" in st.session_state:
        res = st.session_state.bulk_results

        st.subheader("📊 Status Breakdown")
        st.bar_chart(res["status"].value_counts())

        st.subheader("🔁 Duplicates")
        st.dataframe(res[res["status"] == "DUPLICATE_USER"])

        st.subheader("🆕 Unique Entries")
        st.dataframe(res[res["status"] == "UNIQUE"])

        if st.button("✅ Confirm Upload to Staging"):
            db = SessionLocal()
            try:
                for _, row in res.iterrows():
                    db.add(StagingCompany(
                        name=clean_text(row["name"]),
                        website=clean_text(row["website"]),
                        norm_name=norm_name(row["name"]),
                        norm_web=norm_web(row["website"]),
                        added_by=user,
                        status=row["status"],
                        duplicate_owner=row["duplicate_owner"]
                    ))
                db.commit()
                st.success("Bulk upload saved!")
                del st.session_state.bulk_results
            finally:
                db.close()

# =========================================================
# TAB 3 — MY UPLOADS
# =========================================================
with tab3:
    st.subheader("📄 Uploaded Companies")

    db = SessionLocal()
    try:
        rows = db.query(StagingCompany).all() if role == "admin" else \
               db.query(StagingCompany).filter_by(added_by=user).all()
    finally:
        db.close()

    if not rows:
        st.info("No uploads yet.")
    else:
        for r in rows:
            col1, col2, col3, col4, col5 = st.columns([3,3,2,2,1])
            col1.write(r.name)
            col2.write(r.website)
            col3.write(r.status)
            col4.write(r.added_by)

            if col5.button("🗑", key=f"del_{r.id}"):
                delete_company(r.id)
                st.rerun()

        # 👇 PURGE SECTION MUST BE INSIDE TAB
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🧹 Clean My Duplicate Entries")

        if st.sidebar.button("Remove My Duplicate Companies"):
            removed = purge_user_duplicates(user)
            st.sidebar.success(f"{removed} duplicate entries removed from your uploads.")
            st.rerun()

# =========================================================
# TAB 4 — ADMIN EXPORT & ANALYTICS
# =========================================================
with tab4:
    if role != "admin":
        st.warning("Admin only")
    else:
        st.subheader("📊 Upload Summary by User")
        summary = get_user_status_summary()

        if summary:
            st.dataframe(pd.DataFrame(summary).T.fillna(0).astype(int))
        else:
            st.info("No data yet")

        st.subheader("📥 Export Data")
        options = st.multiselect("Select statuses to export", [
            "UNIQUE", "DB_MATCH_ACTIVE_N", "DB_MATCH_INACTIVE_N",
            "DB_MATCH_ACTIVE_Y", "DB_MATCH_INACTIVE_Y"
        ])

        if st.button("Generate Excel"):
            path = export_excel(options)
            if path:
                with open(path, "rb") as f:
                    st.download_button("Download Excel", f.read(), "export.xlsx")
            else:
                st.info("No records found")
