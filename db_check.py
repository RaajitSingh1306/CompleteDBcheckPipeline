import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from utils import norm_name, norm_web
import os
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    return create_engine(
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}",
        pool_pre_ping=True
    )


def fetch_db_snapshot():
    try:
        engine = get_engine()
        df = pd.read_sql(
            "SELECT name, website, status, deleted FROM ts_entity_company_profile",
            engine
        )
        df["_name"] = df["name"].map(norm_name)
        df["_web"] = df["website"].map(norm_web)
        return df
    except SQLAlchemyError as e:
        print("Main DB load failed:", e)
        return pd.DataFrame()


def check_main_db(name, website, df):
    if df.empty:
        return None

    n_name, n_web = norm_name(name), norm_web(website)

    exact = df[(df["_name"] == n_name) & (df["_web"] == n_web)]
    if not exact.empty:
        return exact.iloc[0]

    name_only = df[df["_name"] == n_name]
    if not name_only.empty:
        return name_only.iloc[0]

    web_only = df[df["_web"] == n_web]
    if not web_only.empty:
        return web_only.iloc[0]

    return None
