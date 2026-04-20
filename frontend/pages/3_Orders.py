import streamlit as st
from utils import check_auth, get_db_connection, log_audit, get_current_user
from styles import inject_css
import pandas as pd
from datetime import datetime

def main():
    st.set_page_config(page_title="Order Management", layout="wide")
    inject_css()
    
    if not check_auth():
        st.warning("Please login to access this page")
        st.switch_page("Home.py")
        return
    
    st.title("Order Management")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabs for order management
    tab1, tab2 = st.tabs(["Active Orders", "Order History"])
    
    with tab1:
        st.header("Active Orders")
        
        # Get active orders
        cursor.execute("""
            SELECT o.id, o.customer_name, o.order_date, o.status, 
                   SUM(ol.quantity * ol.price) as total
            FROM orders o
            LEFT JOIN order_lines ol ON o.id = ol.order_id
            WHERE o.status IN ('pending', 'processing')
            GROUP BY o.id, o.customer_name, o.order_date, o.status
            ORDER BY o.order_date DESC
        """)
        orders = cursor.fetchall()
        
        if orders:
            for order in orders:
                with st.expander(f"Order #{order[0]} - {order[1]} (${order[4]:.2f})"):
                    st.write(f"**Status:** {order[2]}")
                    st.write(f"**Date:** {order[3]}")
                    
                    # Get order lines
                    cursor.execute("""
                        SELECT ol.id, p.name, ol.quantity, ol.price, ol.total
                        FROM order_lines ol
                        JOIN products p ON ol.product_id = p.id
                        WHERE ol.order_id = %s
                    """, (order[0],))
                    lines = cursor.fetchall()
                    
                    if lines:
                        line_df = pd.DataFrame(lines, 
                                              columns=['Line ID', 'Product', 'Qty', 'Price', 'Total'])
                        st.dataframe(line_df, use_container_width=True)
                        
                        # Line voiding
                        st.subheader("Void Line Items")
                        line_to_void = st.selectbox(
                            "Select line to void",
                            [line[0] for line in lines],
                            format_func=lambda x: next(l[1] for l in lines if l[0] == x),
                            key=f"void_{order[0]}"
                        )
                        
                        if st.button("Void Selected Line", key=f"void_btn_{order[0]}"):
                            try:
                                # Get line details for stock restoration
                                cursor.execute("""
                                    SELECT product_id, quantity FROM order_lines WHERE id = %s
                                """, (line_to_void,))
                                line_info = cursor.fetchone()
                                
                                # Restore stock
                                cursor.execute("""
                                    UPDATE products SET stock = stock + %s WHERE id = %s
                                """, (line_info[1], line_info[0]))
                                
                                # Void the line
                                cursor.execute("""
                                    UPDATE order_lines SET status = 'voided' WHERE id = %s
                                """, (line_to_void,))
                                
                                conn.commit()
                                log_audit(get_current_user(), "line_void", 
                                         f"Voided line {line_to_void} from order {order[0]}")
                                st.success("Line item voided successfully!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Error voiding line: {e}")
                    
                    # Order actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Mark as Complete", key=f"complete_{order[0]}"):
                            try:
                                cursor.execute("""
                                    UPDATE orders SET status = 'completed' WHERE id = %s
                                """, (order[0],))
                                conn.commit()
                                log_audit(get_current_user(), "order_complete", 
                                         f"Completed order {order[0]}")
                                st.success("Order marked as complete!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Error completing order: {e}")
                    
                    with col2:
                        if st.button("Cancel Order", key=f"cancel_{order[0]}", type="primary"):
                            try:
                                # Restore all stock from order lines
                                cursor.execute("""
                                    SELECT product_id, quantity FROM order_lines 
                                    WHERE order_id = %s AND status != 'voided'
                                """, (order[0],))
                                lines = cursor.fetchall()
                                
                                for line in lines:
                                    cursor.execute("""
                                        UPDATE products SET stock = stock + %s WHERE id = %s
                                    """, (line[1], line[0]))
                                
                                cursor.execute("""
                                    UPDATE orders SET status = 'cancelled' WHERE id = %s
                                """, (order[0],))
                                conn.commit()
                                log_audit(get_current_user(), "order_cancel", 
                                         f"Cancelled order {order[0]}")
                                st.success("Order cancelled!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Error cancelling order: {e}")
        else:
            st.info("No active orders")
    
    with tab2:
        st.header("Order History")
        
        # Date filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")
        
        # Get completed/cancelled orders
        cursor.execute("""
            SELECT o.id, o.customer_name, o.order_date, o.status, 
                   SUM(ol.quantity * ol.price) as total
            FROM orders o
            LEFT JOIN order_lines ol ON o.id = ol.order_id
            WHERE o.status IN ('completed', 'cancelled')
            AND o.order_date BETWEEN %s AND %s
            GROUP BY o.id, o.customer_name, o.order_date, o.status
            ORDER BY o.order_date DESC
        """, (start_date, end_date))
        orders = cursor.fetchall()
        
        if orders:
            order_df = pd.DataFrame(orders, 
                                   columns=['Order ID', 'Customer', 'Date', 'Status', 'Total'])
            st.dataframe(order_df, use_container_width=True)
            
            # Summary metrics
            completed = [o for o in orders if o[3] == 'completed']
            cancelled = [o for o in orders if o[3] == 'cancelled']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Orders", len(orders))
            with col2:
                st.metric("Completed", len(completed))
            with col3:
                st.metric("Cancelled", len(cancelled))
        else:
            st.info("No orders found for the selected period")
    
    conn.close()

if __name__ == "__main__":
    main()
