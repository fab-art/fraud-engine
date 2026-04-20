import streamlit as st
from utils import authenticate, check_auth, get_db_connection, log_audit

def main():
    st.set_page_config(page_title="POS System", layout="wide")
    
    # Check authentication
    if not check_auth():
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if authenticate(username, password):
                st.session_state['authenticated'] = True
                st.session_state['username'] = username
                log_audit(username, "login", "User logged in")
                st.rerun()
            else:
                st.error("Invalid credentials")
        return
    
    # Dashboard
    st.sidebar.title(f"Welcome, {st.session_state['username']}")
    if st.sidebar.button("Logout"):
        log_audit(st.session_state['username'], "logout", "User logged out")
        st.session_state['authenticated'] = False
        st.rerun()
    
    st.title("Dashboard")
    
    # User Management Section
    st.header("User Management")
    conn = get_db_connection()
    
    # Add user form
    with st.expander("Add New User"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Create User"):
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                             (new_username, new_password))
                conn.commit()
                log_audit(st.session_state['username'], "user_create", f"Created user: {new_username}")
                st.success("User created successfully")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # List users
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()
    st.subheader("Existing Users")
    for user in users:
        st.write(f"- {user[1]}")

if __name__ == "__main__":
    main()
