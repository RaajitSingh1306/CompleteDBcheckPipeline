import pandas as pd
import tempfile
from db import SessionLocal, StagingCompany

SHEET_MAP = {
    "UNIQUE": "Approved",
    "DB_MATCH_ACTIVE_N": "Active_N",
    "DB_MATCH_INACTIVE_N": "Inactive_N",
    "DB_MATCH_ACTIVE_Y": "Active_Y",
    "DB_MATCH_INACTIVE_Y": "Inactive_Y"
}

def fetch_all():
    db = SessionLocal()
    rows = db.query(StagingCompany).all()
    db.close()

    return pd.DataFrame([{
        "name": r.name,
        "website": r.website,
        "status": (r.status or "").strip().upper(),
        "added_by": r.added_by
    } for r in rows])


def get_counts():
    df = fetch_all()
    if df.empty:
        return {}
    return df["status"].value_counts().to_dict()


def export_excel(selected_statuses):
    df = fetch_all()
    if df.empty:
        return None

    selected_statuses = [s.strip().upper() for s in selected_statuses]
    df = df[df["status"].isin(selected_statuses)]

    if df.empty:
        return None

    # Create a REAL temporary file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

    with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
        for status in selected_statuses:
            subset = df[df["status"] == status]
            if not subset.empty and status in SHEET_MAP:
                subset.to_excel(writer, sheet_name=SHEET_MAP[status], index=False)

    return tmp.name

def get_user_status_summary():
    df = fetch_all()
    if df.empty:
        return {}

    # Group by user and status
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

def get_user_upload_counts():
    df = fetch_all()
    if df.empty:
        return {}

    counts = df["added_by"].value_counts().to_dict()
    return counts