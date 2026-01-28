import pandas as pd
from utils import norm_name, norm_web
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")

def fetch_db():
    return pd.read_sql("SELECT name, website, status, deleted FROM ts_entity_company_profile", engine)

def check_main_db(name, website):
    df = fetch_db()
    df["_name"] = df["name"].map(norm_name)
    df["_web"] = df["website"].map(norm_web)

    n_name, n_web = norm_name(name), norm_web(website)
    hit = df[(df["_name"] == n_name) | (df["_web"] == n_web)]
    return None if hit.empty else hit.iloc[0]
