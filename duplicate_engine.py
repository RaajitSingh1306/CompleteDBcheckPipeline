from db import SessionLocal, StagingCompany
from utils import norm_name, norm_web

def check_internal_duplicate(name, website, current_user):
    n_name = norm_name(name)
    n_web = norm_web(website)

    db = SessionLocal()

    match = db.query(StagingCompany).filter(
        StagingCompany.norm_name == n_name,
        StagingCompany.norm_web == n_web
    ).first()

    db.close()

    if match:
        # If same user re-uploads, still duplicate but no need to blame themselves
        owner = match.added_by
        return {
            "is_duplicate": True,
            "original_user": owner
        }

    return {
        "is_duplicate": False,
        "original_user": None
    }

def classify_status(db_hit):
    if db_hit is None:
        return "UNIQUE"

    status = str(db_hit.get("status", "")).lower()
    deleted = str(db_hit.get("deleted", "n")).lower()

    if status == "active" and deleted == "n":
        return "DB_MATCH_ACTIVE_N"
    elif status == "inactive" and deleted == "n":
        return "DB_MATCH_INACTIVE_N"
    elif status == "active" and deleted == "y":
        return "DB_MATCH_ACTIVE_Y"
    else:
        return "DB_MATCH_INACTIVE_Y"
