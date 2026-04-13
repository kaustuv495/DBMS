import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import random
from datetime import datetime

# -------------------------------
# DATABASE (SQLite for Cloud)
# -------------------------------
DB_FILE = "aegis.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        ip_address TEXT,
        resource_type TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        severity TEXT,
        status TEXT DEFAULT 'Open',
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def execute_query(query, params=(), fetch=False):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        data = cur.fetchall() if fetch else None
        conn.commit()
        return data
    except Exception as e:
        st.error(f"SQL Error: {e}")
        return None
    finally:
        conn.close()

# -------------------------------
# INIT DB
# -------------------------------
init_db()

# -------------------------------
# AUTH
# -------------------------------
USERS = {
    "admin": "123",
    "user": "123"
}

# -------------------------------
# UI THEME
# -------------------------------
st.markdown("""
<style>
.stApp { background-color: #2B1B17; color: #FFDAB9; }
h1,h2,h3 { color:#ff4500; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# LOGIN
# -------------------------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 AEGIS LOGIN")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if USERS.get(u) == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.title(f"👤 {st.session_state.user}")

page = st.sidebar.radio("Menu", ["Dashboard","Resources","Incidents","Audit"])

if st.sidebar.button("Logout"):
    st.session_state.auth = False
    st.rerun()

# -------------------------------
# DASHBOARD
# -------------------------------
if page == "Dashboard":
    st.title("🛰️ AEGIS Global Command")

    res = execute_query("SELECT COUNT(*) FROM Incidents WHERE status!='Closed'", fetch=True)
    t_count = res[0][0] if res else 0

    res2 = execute_query("SELECT COUNT(*) FROM Resources", fetch=True)
    r_count = res2[0][0] if res2 else 0

    c1,c2 = st.columns(2)
    c1.metric("Active Threats", t_count)
    c2.metric("Resources", r_count)

    df = pd.DataFrame({
        "x": range(10),
        "y": [random.randint(1,10) for _ in range(10)]
    })

    st.plotly_chart(px.line(df, x="x", y="y"))

# -------------------------------
# RESOURCES
# -------------------------------
elif page == "Resources":
    st.header("Resources")

    name = st.text_input("Name")
    ip = st.text_input("IP")

    if st.button("Add Resource"):
        execute_query("INSERT INTO Resources(name,ip_address,resource_type) VALUES(?,?,?)",
                      (name,ip,"Server"))
        st.success("Added")

    data = execute_query("SELECT * FROM Resources", fetch=True)
    if data:
        st.dataframe(pd.DataFrame(data, columns=["ID","Name","IP","Type"]))

# -------------------------------
# INCIDENTS
# -------------------------------
elif page == "Incidents":
    st.header("Incidents")

    desc = st.text_input("Description")

    if st.button("Create Incident"):
        execute_query("INSERT INTO Incidents(description,severity) VALUES(?,?)",
                      (desc,"High"))
        st.success("Incident Created")

    data = execute_query("SELECT * FROM Incidents", fetch=True)
    if data:
        df = pd.DataFrame(data, columns=["ID","Desc","Severity","Status","Time"])
        st.dataframe(df)

# -------------------------------
# AUDIT
# -------------------------------
elif page == "Audit":
    st.header("Audit Logs")

    data = execute_query("SELECT * FROM Audit", fetch=True)
    if data:
        st.dataframe(pd.DataFrame(data))
    else:
        st.info("No logs yet")
