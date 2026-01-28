import streamlit as st
from passlib.context import CryptContext
from db import SessionLocal, User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(p, h): return pwd_context.verify(p, h)
def hash_password(p): return pwd_context.hash(p)


def login_user(username, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username, is_active=True).first()
        if user and verify_password(password, user.password_hash):
            st.session_state.user = user.username
            st.session_state.role = user.role
            st.rerun()
        else:
            st.error("Invalid credentials")
    finally:
        db.close()


def require_login():
    if "user" not in st.session_state:
        st.session_state.user = None
        st.session_state.role = None

    if not st.session_state.user:
        st.title("Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            login_user(u, p)
        st.stop()

    return st.session_state.user, st.session_state.role


def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()
