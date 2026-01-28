import streamlit as st
from passlib.context import CryptContext
from db import SessionLocal, User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin123"

# ---------------- PASSWORD HELPERS ----------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ---------------- ENSURE ADMIN EXISTS ----------------
def ensure_admin():
    db = SessionLocal()
    admin_exists = db.query(User).filter(User.role == "admin").first()
    if not admin_exists:
        db.add(User(
            username=DEFAULT_ADMIN_USER,
            password_hash=get_password_hash(DEFAULT_ADMIN_PASS),
            role="admin",
            is_active=True
        ))
        db.commit()
        print("✅ Default admin created (admin / admin123)")
    db.close()

ensure_admin()

# ---------------- SIGNUP FUNCTION ----------------
def signup_user(username, password):
    if not username or not password:
        st.error("Username and password required")
        return

    db = SessionLocal()
    if db.query(User).filter(User.username == username).first():
        st.error("Username already exists")
        db.close()
        return

    db.add(User(
        username=username,
        password_hash=get_password_hash(password),
        role="user",
        is_active=True
    ))
    db.commit()
    db.close()
    st.success("Account created. Please login.")

# ---------------- LOGIN FUNCTION ----------------
def login_user(username, password):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    db.close()

    if user and verify_password(password, user.password_hash):
        st.session_state.user = user.username
        st.session_state.role = user.role
        st.rerun()
    else:
        st.error("Invalid username or password")

# ---------------- LOGIN SCREEN UI ----------------
def login_screen():
    st.title("🔐 Company Validation Portal")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            login_user(u, p)

    with tab2:
        new_u = st.text_input("New Username", key="signup_user")
        new_p = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            signup_user(new_u, new_p)

# ---------------- REQUIRE LOGIN ----------------
def require_login():
    if "user" not in st.session_state:
        st.session_state.user = None
        st.session_state.role = None

    if not st.session_state.user:
        login_screen()
        st.stop()

    return st.session_state.user, st.session_state.role

# ---------------- LOGOUT ----------------
def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()
