import streamlit as st
from utils import check_auth, get_db_connection, log_audit, get_current_user
from styles import inject_css
import pandas as pd

def main():
    st.set_page_config(page_title="Inventory Management", layout="wide")
    inject_css()
    
    if not check_auth():
        st.warning("Please login to access this page")
        st.switch_page("Home.py")
        return
    
    st.title("Inventory Management")
    
    # Tabs for different inventory functions
    tab1, tab2, tab3 = st.tabs(["Stock Overview", "Add Product", "Stock Adjustments"])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    with tab1:
        st.header("Stock Overview")
        
        # Get all products
        cursor.execute("""
            SELECT id, name, category, price, stock, min_stock 
            FROM products 
            ORDER BY category, name
        """)
        products = cursor.fetchall()
        
        df = pd.DataFrame(products, columns=['ID', 'Name', 'Category', 'Price', 'Stock', 'Min Stock'])
        
        # Highlight low stock items
        def highlight_low_stock(row):
            if row['Stock'] <= row['Min Stock']:
                return ['background-color: #FFEBEE'] * len(row)
            return [''] * len(row)
        
        styled_df = df.style.apply(highlight_low_stock, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        # Low stock alerts
        low_stock = df[df['Stock'] <= df['Min Stock']]
        if not low_stock.empty:
            st.warning(f"⚠️ {len(low_stock)} products are below minimum stock level!")
    
    with tab2:
        st.header("Add New Product")
        
        with st.form("add_product"):
            name = st.text_input("Product Name")
            category = st.text_input("Category")
            price = st.number_input("Price", min_value=0.0, step=0.01)
            stock = st.number_input("Initial Stock", min_value=0, step=1)
            min_stock = st.number_input("Minimum Stock Level", min_value=0, step=1)
            
            submitted = st.form_submit_button("Add Product")
            if submitted:
                try:
                    cursor.execute("""
                        INSERT INTO products (name, category, price, stock, min_stock)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (name, category, price, stock, min_stock))
                    conn.commit()
                    log_audit(get_current_user(), "product_create", f"Added product: {name}")
                    st.success("Product added successfully!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error adding product: {e}")
    
    with tab3:
        st.header("Stock Adjustments")
        
        # Get products for adjustment
        cursor.execute("SELECT id, name, stock FROM products ORDER BY name")
        products = cursor.fetchall()
        product_dict = {p[0]: f"{p[1]} (Stock: {p[2]})" for p in products}
        
        selected_product = st.selectbox("Select Product", list(product_dict.keys()), 
                                        format_func=lambda x: product_dict[x])
        
        adjustment_type = st.radio("Adjustment Type", ["Add Stock", "Remove Stock", "Set Stock"])
        quantity = st.number_input("Quantity", min_value=1, step=1)
        reason = st.text_area("Reason for Adjustment")
        
        if st.button("Apply Adjustment"):
            try:
                if adjustment_type == "Add Stock":
                    cursor.execute("UPDATE products SET stock = stock + %s WHERE id = %s", 
                                 (quantity, selected_product))
                elif adjustment_type == "Remove Stock":
                    cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", 
                                 (quantity, selected_product))
                else:  # Set Stock
                    cursor.execute("UPDATE products SET stock = %s WHERE id = %s", 
                                 (quantity, selected_product))
                
                conn.commit()
                log_audit(get_current_user(), "stock_adjustment", 
                         f"Adjusted product {selected_product}: {adjustment_type} {quantity}. Reason: {reason}")
                st.success("Stock adjusted successfully!")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Error adjusting stock: {e}")
    
    conn.close()

if __name__ == "__main__":
    main()
