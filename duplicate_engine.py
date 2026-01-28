from db import SessionLocal, StagingCompany
from utils import norm_name, norm_web
from db_check import fetch_db_snapshot, check_main_db


def check_internal_duplicate(name, website):
    db = SessionLocal()
    try:
        n_name, n_web = norm_name(name), norm_web(website)

        exact = db.query(StagingCompany).filter(
            StagingCompany.norm_name == n_name,
            StagingCompany.norm_web == n_web
        ).first()
        if exact:
            return {"is_duplicate": True, "original_user": exact.added_by}

        name_only = db.query(StagingCompany).filter_by(norm_name=n_name).first()
        if name_only:
            return {"is_duplicate": True, "original_user": name_only.added_by}

        web_only = db.query(StagingCompany).filter_by(norm_web=n_web).first()
        if web_only:
            return {"is_duplicate": True, "original_user": web_only.added_by}

        return {"is_duplicate": False, "original_user": None}
    finally:
        db.close()


def classify_status(db_hit):
    if db_hit is None:
        return "UNIQUE"

    status = str(db_hit.get("status", "")).lower()
    deleted = str(db_hit.get("deleted", "n")).lower()

    if status == "active" and deleted == "n":
        return "DB_MATCH_ACTIVE_N"
    if status == "inactive" and deleted == "n":
        return "DB_MATCH_INACTIVE_N"
    if status == "active" and deleted == "y":
        return "DB_MATCH_ACTIVE_Y"
    return "DB_MATCH_INACTIVE_Y"

def purge_user_duplicates(username):
    db = SessionLocal()
    try:
        rows = db.query(StagingCompany).filter_by(added_by=username).all()
        seen = {}
        removed = 0

        # Load main DB snapshot once
        main_db_df = fetch_db_snapshot()

        for r in rows:
            n_name = norm_name(r.name)
            n_web = norm_web(r.website)
            key = (n_name, n_web)

            if key in seen:
                db.delete(r)
                removed += 1
            else:
                seen[key] = r.id
                r.norm_name = n_name
                r.norm_web = n_web

                # Re-check against main DB
                hit = check_main_db(r.name, r.website, main_db_df)
                r.status = classify_status(hit)

        db.commit()
        return removed

    finally:
        db.close()
