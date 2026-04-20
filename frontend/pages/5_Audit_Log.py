import streamlit as st
from utils import check_auth, get_db_connection, get_current_user
from styles import inject_css
import pandas as pd

def main():
    st.set_page_config(page_title="Audit Log", layout="wide")
    inject_css()
    
    if not check_auth():
        st.warning("Please login to access this page")
        st.switch_page("Home.py")
        return
    
    st.title("Audit Log - Immutable Change History")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Filters
    st.header("Filters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        user_filter = st.multiselect(
            "Filter by User",
            options=set(cursor.execute("SELECT DISTINCT username FROM audit_log").fetchall()),
            format_func=lambda x: x[0] if isinstance(x, tuple) else x
        )
    
    with col2:
        action_filter = st.multiselect(
            "Filter by Action",
            options=set(cursor.execute("SELECT DISTINCT action FROM audit_log").fetchall()),
            format_func=lambda x: x[0] if isinstance(x, tuple) else x
        )
    
    with col3:
        date_range = st.date_input("Date Range", value=None)
    
    # Build query
    query = """
        SELECT id, username, action, details, timestamp, ip_address
        FROM audit_log
        WHERE 1=1
    """
    params = []
    
    if user_filter:
        placeholders = ','.join(['%s'] * len(user_filter))
        query += f" AND username IN ({placeholders})"
        params.extend([u[0] if isinstance(u, tuple) else u for u in user_filter])
    
    if action_filter:
        placeholders = ','.join(['%s'] * len(action_filter))
        query += f" AND action IN ({placeholders})"
        params.extend([a[0] if isinstance(a, tuple) else a for a in action_filter])
    
    query += " ORDER BY timestamp DESC LIMIT 500"
    
    # Execute query
    cursor.execute(query, params)
    logs = cursor.fetchall()
    
    # Display audit log
    if logs:
        log_df = pd.DataFrame(logs, 
                             columns=['ID', 'User', 'Action', 'Details', 'Timestamp', 'IP Address'])
        
        # Display as table with styling
        st.dataframe(
            log_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID"),
                "User": st.column_config.TextColumn("User"),
                "Action": st.column_config.TextColumn("Action"),
                "Details": st.column_config.TextColumn("Details", width="medium"),
                "Timestamp": st.column_config.DatetimeColumn("Timestamp"),
                "IP Address": st.column_config.TextColumn("IP Address")
            }
        )
        
        # Statistics
        st.header("Audit Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Log Entries", len(log_df))
        
        with col2:
            unique_users = log_df['User'].nunique()
            st.metric("Unique Users", unique_users)
        
        with col3:
            unique_actions = log_df['Action'].nunique()
            st.metric("Unique Actions", unique_actions)
        
        # Action breakdown
        st.subheader("Actions by Type")
        action_counts = log_df['Action'].value_counts()
        st.bar_chart(action_counts)
        
        # User activity
        st.subheader("Activity by User")
        user_counts = log_df['User'].value_counts()
        st.bar_chart(user_counts)
        
        # Export option
        st.header("Export")
        csv = log_df.to_csv(index=False)
        st.download_button(
            label="Download Audit Log (CSV)",
            data=csv,
            file_name=f"audit_log_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Immutability notice
        st.info("""
        🔒 **Immutable Audit Trail**
        
        This audit log is designed to be immutable. All system actions are recorded 
        and cannot be modified or deleted through the application interface. This 
        ensures a complete and trustworthy history of all changes made to the system.
        
        For compliance purposes, audit logs are retained according to your 
        organization's data retention policy.
        """)
    else:
        st.info("No audit log entries found")
    
    conn.close()

if __name__ == "__main__":
    main()
