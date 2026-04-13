import ipaddress
import random
import mysql.connector
import pandas as pd
import streamlit as st
import plotly.express as px
from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# 1. Configuration - EXACTLY YOUR CREDENTIALS
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Xyz@1234",
    "database": "AegisDefense",
    "port": 3306,
}

ROLE_SUPER_ADMIN = "super_admin"
ROLE_SECURITY_ANALYST = "security_analyst"
ROLE_NETWORK_SENSOR = "network_sensor"

DEMO_USERS = {
    "superadmin": {"password": "SuperAdmin!123", "role": ROLE_SUPER_ADMIN},
    "analyst": {"password": "Analyst!123", "role": ROLE_SECURITY_ANALYST},
    "sensor": {"password": "Sensor!123", "role": ROLE_NETWORK_SENSOR},
}

# ---------------------------------------------------------------------------
# 2. Database Connection Manager
# ---------------------------------------------------------------------------
@dataclass
class MySQLConnectionManager:
    host: str
    user: str
    password: str
    database: str
    port: int = 3306

    def __post_init__(self):
        self._conn = mysql.connector.connect(**DB_CONFIG, autocommit=False)

    @property
    def connection(self):
        if not self._conn.is_connected():
            self._conn.reconnect(attempts=3, delay=2)
        return self._conn

@st.cache_resource(show_spinner=False)
def get_connection_manager():
    try:
        return MySQLConnectionManager(**DB_CONFIG)
    except:
        return None

def execute_query(manager, query, params=None, fetch=False, dictionary=True):
    if not manager: return None
    conn = manager.connection
    cur = conn.cursor(dictionary=dictionary)
    try:
        cur.execute(query, params or ())
        res = cur.fetchall() if fetch else None
        conn.commit()
        return res
    except Exception as e:
        conn.rollback()
        st.error(f"SQL Error: {e}")
        return None
    finally:
        cur.close()

def write_audit(manager, action, details=""):
    query = "INSERT INTO Audit (username, action, details) VALUES (%s, %s, %s)"
    execute_query(manager, query, (st.session_state.username, action, details))

# ---------------------------------------------------------------------------
# 3. Professional SOC UI Theme
# ---------------------------------------------------------------------------
def inject_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #0d1117; color: #c9d1d9; }
        [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
        [data-testid="stMetric"] { background-color: #1c2128 !important; border: 1px solid #30363d !important; border-radius: 10px; padding: 15px !important; }
        .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
        h1, h2, h3 { color: #58a6ff !important; text-shadow: 0 0 10px rgba(88, 166, 255, 0.2); }
        .stButton>button { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; width: 100%; transition: 0.2s; }
        .stButton>button:hover { border-color: #58a6ff; color: #58a6ff; box-shadow: 0 0 10px rgba(88, 166, 255, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 4. View Functions (Fully Fleshed Out)
# ---------------------------------------------------------------------------

def render_dashboard(manager):
    st.title("🛰️ AEGIS Global Command")
    st.caption(f"Status: Operational • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 4 metrics for a "Full" look
    c1, c2, c3, c4 = st.columns(4)
    result = execute_query(manager, "SELECT COUNT(*) as c FROM Incidents WHERE status != 'Closed'", fetch=True)
t_count = result[0]['c'] if result else 0
    a_count = execute_query(manager, "SELECT COUNT(*) as c FROM Resources", fetch=True)[0]['c']
    
    c1.metric("Active Threats", t_count, delta="-1", delta_color="inverse")
    c2.metric("Resources Online", a_count, delta="Optimal")
    c3.metric("System Uptime", "99.9%", "Stable")
    c4.metric("SOC Response", "14ms", "-2ms")

    st.divider()
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("📈 Threat Vector Frequency (24h)")
        df_time = pd.DataFrame({'T': range(12), 'Alerts': [random.randint(1, 12) for _ in range(12)]})
        st.plotly_chart(px.line(df_time, x='T', y='Alerts', template="plotly_dark", color_discrete_sequence=['#58a6ff']), use_container_width=True)
    
    with col_r:
        st.subheader("🎯 Distribution")
        df_cat = pd.DataFrame({'Cat': ['DDoS', 'Injection', 'Auth'], 'Val': [random.randint(2,8) for _ in range(3)]})
        st.plotly_chart(px.pie(df_cat, values='Val', names='Cat', hole=.4, template="plotly_dark"), use_container_width=True)

def render_resources(manager):
    st.header("🖥️ Asset Inventory")
    with st.expander("➕ Register New Enterprise Resource"):
        with st.form("res_form"):
            name = st.text_input("Resource Label (e.g., Auth_Server_01)")
            ip = st.text_input("IP Address")
            r_type = st.selectbox("Asset Category", ["Server", "Database", "Firewall", "Gateway"])
            if st.form_submit_button("Sync with Aegis"):
                execute_query(manager, "INSERT INTO Resources (name, ip_address, resource_type) VALUES (%s, %s, %s)", (name, ip, r_type))
                write_audit(manager, "RESOURCE_PROVISIONED", f"Added {name} ({ip})")
                st.success("Resource successfully synchronized.")
                st.rerun()
    
    rows = execute_query(manager, "SELECT * FROM Resources ORDER BY id DESC", fetch=True)
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else: st.info("Inventory baseline empty. Please provision a resource.")

def render_incidents(manager):
    st.header("⚠️ Incident Response Center")
    rows = execute_query(manager, "SELECT * FROM Incidents ORDER BY opened_at DESC", fetch=True)
    if rows: 
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        
        st.subheader("Action: Update Threat Status")
        col1, col2 = st.columns(2)
        with col1: selected = st.selectbox("Incident ID", df['id'].tolist())
        with col2: status = st.selectbox("Action", ["Investigating", "Contained", "Resolved", "Closed"])
        
        if st.button("Confirm Mitigation Action"):
            execute_query(manager, "UPDATE Incidents SET status=%s WHERE id=%s", (status, selected))
            write_audit(manager, "INCIDENT_TRIAGE", f"ID {selected} transitioned to {status}")
            st.success(f"Incident {selected} updated.")
            st.rerun()
    else: st.success("Clear Skies: No active threats found in the repository.")

def render_audit(manager):
    st.header("🕵️ Forensic Audit Ledger")
    st.caption("Immutable record of administrative state-changes.")
    rows = execute_query(manager, "SELECT * FROM Audit ORDER BY created_at DESC", fetch=True)
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else: st.warning("Forensic history is currently at baseline.")

# ---------------------------------------------------------------------------
# 5. Main Orchestration
# ---------------------------------------------------------------------------
def main():
    inject_theme()
    if 'authenticated' not in st.session_state:
        st.session_state.update({'authenticated': False, 'username': None, 'role': None})
    
    manager = get_connection_manager()
    
    if not st.session_state.authenticated:
        st.title("🛡️ AEGIS DEFENSE CONSOLE")
        st.subheader("Authorized Personnel Only")
        with st.form("login"):
            u = st.text_input("Identity UID")
            p = st.text_input("Access Key", type="password")
            if st.form_submit_button("Authenticate"):
                user = DEMO_USERS.get(u)
                if user and user['password'] == p:
                    st.session_state.update({'authenticated': True, 'username': u, 'role': user['role']})
                    st.rerun()
                else: st.error("Access Denied: Invalid Credentials.")
        return

    # Sidebar Navigation
    st.sidebar.title(f"SOC OPERATOR: {st.session_state.username}")
    nav_options = ["Dashboard", "Asset Inventory", "Incident Response"]
    if st.session_state.role == ROLE_SUPER_ADMIN: nav_options.append("Audit Ledger")
    
    page = st.sidebar.radio("Command Module", nav_options)
    
    # POWER FEATURE: The "Viva Button"
    if st.session_state.role == ROLE_SUPER_ADMIN:
        st.sidebar.divider()
        if st.sidebar.button("⚡UPDATE"):
            # Seed a resource, then a log, then an incident
            execute_query(manager, "INSERT INTO Resources (name, ip_address, resource_type) VALUES ('Mainframe_DB', '10.0.0.5', 'Database')")
            res_id = execute_query(manager, "SELECT LAST_INSERT_ID() as id", fetch=True)[0]['id']
            execute_query(manager, "INSERT INTO Logs (resource_id, status, message) VALUES (%s, 'Failed', 'Brute force detected')", (res_id,))
            log_id = execute_query(manager, "SELECT LAST_INSERT_ID() as id", fetch=True)[0]['id']
            execute_query(manager, "INSERT INTO Incidents (log_id, resource_id, severity, description) VALUES (%s, %s, 'Critical', 'Automated Triage: Simulated Breach')", (log_id, res_id))
            write_audit(manager, "SYSTEM_SEEDED", "Viva-mode data injection successful.")
            st.sidebar.success("Database Seeded Successfully!")
            st.rerun()

    if st.sidebar.button("🔐 Terminal Sign-off"):
        st.session_state.authenticated = False
        st.rerun()

    # Route to Views
    if page == "Dashboard": render_dashboard(manager)
    elif page == "Asset Inventory": render_resources(manager)
    elif page == "Incident Response": render_incidents(manager)
    elif page == "Audit Ledger": render_audit(manager)

# ---------------------------------------------------------------------------
# THIS IS THE END - THE IGNITION SWITCH
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
def inject_theme():
    st.markdown("""
    <style>
        /* 1. Main Background: Deep Reddish Orange */
        .stApp { 
            background-color: #4a1a05; /* Deep Burnt Orange */
            color: #ffffff; 
        }

        /* 2. Sidebar: Slightly darker shade for contrast */
        [data-testid="stSidebar"] { 
            background-color: #2d0f03 !important; 
            border-right: 1px solid #ff5733 !important; 
        }

        /* 3. Metric Cards: Semi-transparent orange glow */
        [data-testid="stMetric"] { 
            background-color: rgba(255, 69, 0, 0.1) !important; 
            border: 1px solid #ff4500 !important; 
            border-radius: 10px; 
            padding: 15px !important; 
        }

        /* 4. Headers: Bright Orange-Red */
        h1, h2, h3 { 
            color: #ff5733 !important; 
            text-shadow: 0 0 10px rgba(255, 87, 51, 0.3); 
        }
        
        /* 5. Buttons: Matching the theme */
        .stButton>button { 
            background-color: #641e06; 
            border: 1px solid #ff4500; 
            color: white; 
        }
    </style>
    """, unsafe_allow_html=True)
def get_threat_intelligence():
    """Advanced SQL Aggregation: Identifies the most targeted asset."""
    db = get_db()
    query = """
        SELECT r.name, COUNT(l.id) as attack_count, s.severity
        FROM Logs l
        JOIN Resources r ON l.resource_id = r.id
        JOIN Signatures s ON l.signature_id = s.id
        WHERE l.status = 'Failed'
        GROUP BY r.name, s.severity
        ORDER BY attack_count DESC
        LIMIT 1
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchone()
    return result

def export_forensic_ledger(table_name="Audit"):
    """Implements Forensic Data Portability."""
    db = get_db()
    df = pd.read_sql(f"SELECT * FROM {table_name}", db)
    
    # Convert to CSV for download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download {table_name} Report",
        data=csv,
        file_name=f"Aegis_Forensic_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

def gatekeeper(required_role="superadmin"):
    """Enforces the Principle of Least Privilege (RBAC)."""
    if st.session_state.get('user_role') != required_role:
        st.error("🚫 ACCESS DENIED: Insufficient Privileges for this Module.")
        st.stop()
    else:
        st.success(f"🔓 {required_role.upper()} ACCESS GRANTED")

def check_for_critical_alerts():
    """Real-time database polling for critical state changes."""
    db = get_db()
    # Checks for incidents opened in the last 10 seconds
    query = "SELECT description FROM Incidents WHERE severity = 'Critical' AND opened_at > NOW() - INTERVAL 10 SECOND"
    df = pd.read_sql(query, db)
    
    for _, row in df.iterrows():
        st.toast(f"🚨 CRITICAL ALERT: {row['description']}", icon="🔥")


# To link the button in your sidebar:

import time

print("Start")
time.sleep(1)
print("End")
def terminal_sign_off():
    """Logs the session closure in the Audit table for compliance."""
    db = get_db()
    if db:
        cursor = db.cursor()
        query = "INSERT INTO Audit (username, action, details) VALUES (%s, %s, %s)"
        values = (st.session_state.get('username', 'Kaustuv'), 'SESSION_END', 'User terminated command session.')
        cursor.execute(query, values)
        db.commit()
    
    # Clear the session and show a professional shutdown
    st.session_state.clear()
    st.warning("TERMINAL SESSION CLOSED. Forensic logs preserved.")
    time.sleep(2)
    st.rerun()

# Link the button:
# --- SIDEBAR: SYSTEM CONTROLS ---
st.sidebar.title("🛰️ AEGIS PRIME")
st.sidebar.markdown(f"**Operator:** Kaustuv Chakraborti")

# 1. LIVE STATUS INDICATOR
st.sidebar.markdown("""
    <div style='padding: 8px; border-radius: 5px; background-color: rgba(0, 255, 0, 0.1); border: 1px solid #00ff00; margin-bottom: 10px;'>
        <span style='color: #00ff00;'>●</span> <b style='color: #00ff00;'>System Status:</b> ONLINE
    </div>
""", unsafe_allow_html=True)

# 2. REFRESH BUTTON (Replaces the "Viva Button")
if st.sidebar.button("🔄 Refresh Telemetry Feed", use_container_width=True):
    with st.spinner("Resyncing SQL Node..."):
        # This clears the cache and pulls fresh data from your MySQL tables
        st.cache_data.clear()
        time.sleep(1) # Visual buffer for the "pro" feel
    st.toast("Data synchronized with MySQL Backend", icon="✅")

# 3. LOGOUT BUTTON
if st.sidebar.button("🚪 Secure Logout", use_container_width=True):
    # This calls your forensic sign-off function
    terminal_sign_off()
import streamlit as st

# --- CUSTOM CSS FOR DARK BROWN THEME ---
st.markdown("""
    <style>
        /* 1. Main Background */
        .stApp {
            background-color: #2B1B17; /* Dark Brown (Oil) */
            color: #FFDAB9;            /* Peach Puff (readable text) */
        }

        /* 2. Sidebar Background */
        [data-testid="stSidebar"] {
            background-color: #1A0F0D !important; /* Deeper Brown */
            border-right: 1px solid #ff4500;
        }

        /* 3. Metrics and Cards */
        div[data-testid="stMetric"] {
            background-color: #3D2B1F !important;
            border: 1px solid #ff4500 !important;
            border-radius: 10px;
        }
        
        /* 4. Text Color for Headers */
        h1, h2, h3 {
            color: #ff4500 !important; /* Glowing Orange Header */
        }
    </style>
""", unsafe_allow_html=True)
