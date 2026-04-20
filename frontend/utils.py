import streamlit as st
import psycopg2
from datetime import datetime
import hashlib

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pos_system',
    'user': 'postgres',
    'password': 'your_password'
}

def get_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DB_CONFIG)

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    """Authenticate a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = hash_password(password)
    cursor.execute("SELECT id FROM users WHERE username = %s AND password = %s", 
                   (username, hashed_pw))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def check_auth():
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)

def log_audit(username, action, details):
    """Log an audit trail entry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (username, action, details, timestamp)
        VALUES (%s, %s, %s, %s)
    """, (username, action, details, datetime.now()))
    conn.commit()
    conn.close()

def get_current_user():
    """Get the current logged-in username."""
    return st.session_state.get('username', None)
