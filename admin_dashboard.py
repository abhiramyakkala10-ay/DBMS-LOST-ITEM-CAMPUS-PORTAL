"""
admin_dashboard.py — Streamlit admin panel.
Run with: streamlit run admin_dashboard.py
"""
import streamlit as st
import pandas as pd
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'campus_lf.db')

st.set_page_config(page_title="Campus L&F Admin", layout="wide", page_icon="🎒")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def query(sql, params=()):
    conn = get_conn()
    df   = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def execute(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("🎒 Campus L&F")
st.sidebar.markdown("**Admin Dashboard**")
page = st.sidebar.radio("Navigate", ["Overview", "Items", "Claims", "Matches", "CCTV Events", "Users"])

# ── Overview ─────────────────────────────────────────────────────────────────
if page == "Overview":
    st.title("📊 Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lost Items",   query("SELECT COUNT(*) n FROM items WHERE type='lost'")['n'][0])
    c2.metric("Found Items",  query("SELECT COUNT(*) n FROM items WHERE type='found'")['n'][0])
    c3.metric("Claimed",      query("SELECT COUNT(*) n FROM items WHERE status='claimed'")['n'][0])
    c4.metric("Users",        query("SELECT COUNT(*) n FROM users")['n'][0])

    st.subheader("Recent Activity")
    df = query("""
        SELECT i.item_id, i.type, i.category, i.status, i.date,
               u.name as reported_by, l.name as location
        FROM items i
        LEFT JOIN users u ON i.reported_by = u.user_id
        LEFT JOIN locations l ON i.location_id = l.location_id
        ORDER BY i.date DESC LIMIT 15
    """)
    st.dataframe(df, use_container_width=True)

    st.subheader("Category Breakdown")
    cat_df = query("SELECT category, COUNT(*) as count FROM items GROUP BY category ORDER BY count DESC")
    st.bar_chart(cat_df.set_index('category'))

# ── Items ─────────────────────────────────────────────────────────────────────
elif page == "Items":
    st.title("📦 All Items")
    filter_type   = st.selectbox("Filter type", ["all","lost","found"])
    filter_status = st.selectbox("Filter status", ["all","open","claimed","closed"])

    where = []
    if filter_type   != 'all': where.append(f"i.type='{filter_type}'")
    if filter_status != 'all': where.append(f"i.status='{filter_status}'")
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    df = query(f"""
        SELECT i.item_id, i.type, i.category, i.description, i.status,
               i.date, u.name as reporter, l.name as location
        FROM items i
        LEFT JOIN users u ON i.reported_by = u.user_id
        LEFT JOIN locations l ON i.location_id = l.location_id
        {clause}
        ORDER BY i.date DESC
    """)
    st.dataframe(df, use_container_width=True)

    st.subheader("Update Item Status")
    item_id = st.number_input("Item ID", min_value=1, step=1)
    new_status = st.selectbox("New status", ["open","claimed","closed"])
    if st.button("Update"):
        execute("UPDATE items SET status=? WHERE item_id=?", (new_status, item_id))
        st.success(f"Item {item_id} updated to '{new_status}'")
        st.rerun()

# ── Claims ────────────────────────────────────────────────────────────────────
elif page == "Claims":
    st.title("✋ Pending Claims")
    df = query("""
        SELECT c.claim_id, c.status, c.timestamp, c.notes,
               i.category, i.type,
               u.name as claimant, u.email
        FROM claims c
        JOIN items i ON c.item_id = i.item_id
        JOIN users u ON c.claimant_id = u.user_id
        ORDER BY c.timestamp DESC
    """)
    st.dataframe(df, use_container_width=True)

    st.subheader("Approve / Reject Claim")
    claim_id = st.number_input("Claim ID", min_value=1, step=1)
    action   = st.radio("Action", ["approve","reject"])
    if st.button("Submit"):
        new_status = 'approved' if action == 'approve' else 'rejected'
        execute("UPDATE claims SET status=? WHERE claim_id=?", (new_status, claim_id))
        if action == 'approve':
            execute("""
                UPDATE items SET status='claimed'
                WHERE item_id = (SELECT item_id FROM claims WHERE claim_id=?)
            """, (claim_id,))
        st.success(f"Claim {claim_id} {new_status}")
        st.rerun()

# ── Matches ───────────────────────────────────────────────────────────────────
elif page == "Matches":
    st.title("🔗 Auto-Matches")
    df = query("""
        SELECT m.match_id, m.score, m.verified,
               l.category AS lost_cat, l.description AS lost_desc,
               f.category AS found_cat, f.description AS found_desc
        FROM matches m
        JOIN items l ON m.lost_item_id  = l.item_id
        JOIN items f ON m.found_item_id = f.item_id
        ORDER BY m.score DESC
    """)
    st.dataframe(df, use_container_width=True)

    match_id = st.number_input("Mark Match ID as Verified", min_value=1, step=1)
    if st.button("Verify"):
        execute("UPDATE matches SET verified=1 WHERE match_id=?", (match_id,))
        st.success("Match verified!")
        st.rerun()

# ── CCTV Events ───────────────────────────────────────────────────────────────
elif page == "CCTV Events":
    st.title("📷 CCTV Events")
    df = query("""
        SELECT e.event_id, e.camera_id, e.timestamp, e.clip_path,
               l.name as location
        FROM cctv_events e
        LEFT JOIN locations l ON e.location_id = l.location_id
        ORDER BY e.timestamp DESC
    """)
    st.dataframe(df, use_container_width=True)

    st.subheader("View Clip Detections")
    event_id = st.number_input("Event ID", min_value=1, step=1)
    if st.button("Load Detections"):
        row = query(f"SELECT detections, clip_path FROM cctv_events WHERE event_id={event_id}")
        if not row.empty:
            clip_path  = row['clip_path'][0]
            detections = row['detections'][0]
            st.write(f"**Clip:** `{clip_path}`")
            if detections:
                det = json.loads(detections) if isinstance(detections, str) else detections
                if det:
                    st.dataframe(pd.DataFrame(det))
                else:
                    st.info("No detections recorded.")
            else:
                st.info("No detections recorded.")
        else:
            st.error("Event not found.")

# ── Users ─────────────────────────────────────────────────────────────────────
elif page == "Users":
    st.title("👥 Users")
    df = query("SELECT user_id, name, email, phone, role, created FROM users ORDER BY created DESC")
    st.dataframe(df, use_container_width=True)

    st.subheader("Change User Role")
    user_id  = st.number_input("User ID", min_value=1, step=1)
    new_role = st.selectbox("Role", ["student","admin"])
    if st.button("Update Role"):
        execute("UPDATE users SET role=? WHERE user_id=?", (new_role, user_id))
        st.success(f"User {user_id} role set to '{new_role}'")
        st.rerun()
