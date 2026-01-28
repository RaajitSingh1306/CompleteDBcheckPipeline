import pandas as pd
import tempfile
from db import SessionLocal, StagingCompany

SHEET_MAP = {
    "UNIQUE": "Approved",
    "DB_MATCH_ACTIVE_N": "Active_N",
    "DB_MATCH_INACTIVE_N": "Inactive_N",
    "DB_MATCH_ACTIVE_Y": "Active_Y",
    "DB_MATCH_INACTIVE_Y": "Inactive_Y",
    "DUPLICATE_USER": "User_Duplicates"
}

# ---------------------------------------------------
# FETCH ALL STAGING DATA
# ---------------------------------------------------
def fetch_all():
    db = SessionLocal()
    try:
        rows = db.query(StagingCompany).all()
        return pd.DataFrame([{
            "name": r.name,
            "website": r.website,
            "status": (r.status or "").strip().upper(),
            "added_by": r.added_by
        } for r in rows])
    finally:
        db.close()


# ---------------------------------------------------
# USER UPLOAD COUNTS (SIDEBAR)
# ---------------------------------------------------
def get_user_upload_counts():
    df = fetch_all()
    if df.empty:
        return {}
    return df["added_by"].value_counts().to_dict()


# ---------------------------------------------------
# ADMIN STATUS SUMMARY TABLE
# ---------------------------------------------------
def get_user_status_summary():
    df = fetch_all()
    if df.empty:
        return {}

    grouped = df.groupby(["added_by", "status"]).size().reset_index(name="count")

    result = {}
    for _, row in grouped.iterrows():
        user = row["added_by"]
        status = row["status"]
        count = int(row["count"])

        if user not in result:
            result[user] = {}
        result[user][status] = count

    return result


# ---------------------------------------------------
# EXPORT TO EXCEL BY STATUS
# ---------------------------------------------------
def export_excel(statuses):
    df = fetch_all()
    if df.empty:
        return None

    statuses = [s.strip().upper() for s in statuses]
    df = df[df["status"].isin(statuses)]

    if df.empty:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

    with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
        for status in statuses:
            subset = df[df["status"] == status]
            if not subset.empty:
                sheet = SHEET_MAP.get(status, status)
                subset.to_excel(writer, sheet_name=sheet, index=False)

    return tmp.name
