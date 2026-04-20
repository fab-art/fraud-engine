import streamlit as st
from utils import check_auth, get_db_connection, log_audit, get_current_user
from styles import inject_css
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Finance", layout="wide")
    inject_css()
    
    if not check_auth():
        st.warning("Please login to access this page")
        st.switch_page("Home.py")
        return
    
    st.title("Finance Management")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabs for finance sections
    tab1, tab2, tab3, tab4 = st.tabs(["P&L Overview", "Revenue", "Expenses", "Payables"])
    
    with tab1:
        st.header("Profit & Loss Statement")
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        # Calculate revenue
        cursor.execute("""
            SELECT SUM(total) FROM sales 
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_date, end_date))
        revenue = cursor.fetchone()[0] or 0
        
        # Calculate COGS (Cost of Goods Sold)
        cursor.execute("""
            SELECT SUM(ol.quantity * p.cost) 
            FROM order_lines ol
            JOIN products p ON ol.product_id = p.id
            JOIN orders o ON ol.order_id = o.id
            WHERE o.status = 'completed' 
            AND DATE(o.order_date) BETWEEN %s AND %s
        """, (start_date, end_date))
        cogs = cursor.fetchone()[0] or 0
        
        # Calculate expenses
        cursor.execute("""
            SELECT SUM(amount) FROM expenses 
            WHERE DATE(date) BETWEEN %s AND %s
        """, (start_date, end_date))
        expenses = cursor.fetchone()[0] or 0
        
        # Calculate gross and net profit
        gross_profit = revenue - cogs
        net_profit = gross_profit - expenses
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Revenue", f"${revenue:,.2f}")
        with col2:
            st.metric("COGS", f"${cogs:,.2f}")
        with col3:
            st.metric("Gross Profit", f"${gross_profit:,.2f}", 
                     delta=f"{(gross_profit/revenue*100) if revenue > 0 else 0:.1f}% margin")
        with col4:
            st.metric("Net Profit", f"${net_profit:,.2f}",
                     delta=f"{(net_profit/revenue*100) if revenue > 0 else 0:.1f}% margin")
        
        # P&L Summary Table
        st.subheader("P&L Summary")
        pnl_data = {
            'Category': ['Revenue', 'COGS', 'Gross Profit', 'Expenses', 'Net Profit'],
            'Amount': [revenue, cogs, gross_profit, expenses, net_profit]
        }
        pnl_df = pd.DataFrame(pnl_data)
        st.dataframe(pnl_df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.header("Revenue Analysis")
        
        # Revenue by product
        cursor.execute("""
            SELECT p.name, SUM(ol.quantity) as qty_sold, SUM(ol.total) as revenue
            FROM order_lines ol
            JOIN products p ON ol.product_id = p.id
            JOIN orders o ON ol.order_id = o.id
            WHERE o.status = 'completed'
            GROUP BY p.name
            ORDER BY revenue DESC
            LIMIT 20
        """)
        products = cursor.fetchall()
        
        if products:
            rev_df = pd.DataFrame(products, columns=['Product', 'Qty Sold', 'Revenue'])
            st.dataframe(rev_df, use_container_width=True, hide_index=True)
            
            # Chart
            st.bar_chart(rev_df.set_index('Product')['Revenue'])
        else:
            st.info("No revenue data available")
    
    with tab3:
        st.header("Expense Management")
        
        # Add expense form
        with st.expander("Add New Expense"):
            with st.form("add_expense"):
                category = st.selectbox("Category", 
                                       ["Rent", "Utilities", "Salaries", "Supplies", 
                                        "Marketing", "Maintenance", "Other"])
                description = st.text_area("Description")
                amount = st.number_input("Amount", min_value=0.01, step=0.01)
                date = st.date_input("Date", datetime.now())
                
                submitted = st.form_submit_button("Record Expense")
                if submitted:
                    try:
                        cursor.execute("""
                            INSERT INTO expenses (category, description, amount, date)
                            VALUES (%s, %s, %s, %s)
                        """, (category, description, amount, date))
                        conn.commit()
                        log_audit(get_current_user(), "expense_create", 
                                 f"Recorded expense: {category} ${amount}")
                        st.success("Expense recorded!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error recording expense: {e}")
        
        # List expenses
        cursor.execute("""
            SELECT id, category, description, amount, date 
            FROM expenses 
            ORDER BY date DESC
            LIMIT 50
        """)
        expenses = cursor.fetchall()
        
        if expenses:
            exp_df = pd.DataFrame(expenses, 
                                 columns=['ID', 'Category', 'Description', 'Amount', 'Date'])
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
            
            # Expenses by category
            st.subheader("Expenses by Category")
            cursor.execute("""
                SELECT category, SUM(amount) as total
                FROM expenses
                GROUP BY category
                ORDER BY total DESC
            """)
            cat_expenses = cursor.fetchall()
            cat_df = pd.DataFrame(cat_expenses, columns=['Category', 'Total'])
            st.bar_chart(cat_df.set_index('Category'))
        else:
            st.info("No expenses recorded")
    
    with tab4:
        st.header("Accounts Payable")
        
        # Add payable
        with st.expander("Add New Payable"):
            with st.form("add_payable"):
                vendor = st.text_input("Vendor Name")
                description = st.text_area("Description")
                amount = st.number_input("Amount Due", min_value=0.01, step=0.01)
                due_date = st.date_input("Due Date")
                
                submitted = st.form_submit_button("Create Payable")
                if submitted:
                    try:
                        cursor.execute("""
                            INSERT INTO payables (vendor, description, amount, due_date, status)
                            VALUES (%s, %s, %s, %s, 'pending')
                        """, (vendor, description, amount, due_date))
                        conn.commit()
                        log_audit(get_current_user(), "payable_create", 
                                 f"Created payable: {vendor} ${amount}")
                        st.success("Payable created!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error creating payable: {e}")
        
        # List payables
        cursor.execute("""
            SELECT id, vendor, description, amount, due_date, status 
            FROM payables 
            ORDER BY due_date ASC
        """)
        payables = cursor.fetchall()
        
        if payables:
            pay_df = pd.DataFrame(payables, 
                                 columns=['ID', 'Vendor', 'Description', 'Amount', 'Due Date', 'Status'])
            st.dataframe(pay_df, use_container_width=True, hide_index=True)
            
            # Mark as paid
            st.subheader("Mark Payable as Paid")
            pending = [p for p in payables if p[5] == 'pending']
            if pending:
                payable_to_pay = st.selectbox(
                    "Select Payable",
                    [p[0] for p in pending],
                    format_func=lambda x: next(f"{p[1]} - ${p[3]:.2f}" for p in pending if p[0] == x)
                )
                
                if st.button("Mark as Paid"):
                    try:
                        cursor.execute("""
                            UPDATE payables SET status = 'paid', paid_date = %s 
                            WHERE id = %s
                        """, (datetime.now(), payable_to_pay))
                        conn.commit()
                        log_audit(get_current_user(), "payable_paid", 
                                 f"Paid payable {payable_to_pay}")
                        st.success("Payable marked as paid!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error updating payable: {e}")
            else:
                st.info("No pending payables")
        else:
            st.info("No payables recorded")
    
    conn.close()

if __name__ == "__main__":
    main()
