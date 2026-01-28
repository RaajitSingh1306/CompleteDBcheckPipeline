import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"mysql+pymysql://{os.getenv('STAGING_DB_USER')}:{os.getenv('STAGING_DB_PASSWORD')}@{os.getenv('STAGING_DB_HOST')}:{os.getenv('STAGING_DB_PORT')}/{os.getenv('STAGING_DB_NAME')}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)

class StagingCompany(Base):
    __tablename__ = "staging_companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    website = Column(String(255))
    norm_name = Column(String(255), index=True)
    norm_web = Column(String(255), index=True)
    added_by = Column(String(100))
    status = Column(String(50))

Base.metadata.create_all(bind=engine)

def add_company(name, website, norm_name, norm_web, user, status):
    db = SessionLocal()
    db.add(StagingCompany(
        name=name,
        website=website,
        norm_name=norm_name,
        norm_web=norm_web,
        added_by=user,
        status=status
    ))
    db.commit()
    db.close()
    
def delete_company(company_id):
    db = SessionLocal()
    obj = db.query(StagingCompany).filter(StagingCompany.id == company_id).first()
    if obj:
        db.delete(obj)
        db.commit()
    db.close()