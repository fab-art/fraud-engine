import streamlit as st
from utils import check_auth, get_db_connection, log_audit, get_current_user
from styles import inject_css

def main():
    st.set_page_config(page_title="Point of Sale", layout="wide")
    inject_css()
    
    if not check_auth():
        st.warning("Please login to access this page")
        st.switch_page("Home.py")
        return
    
    st.title("Point of Sale")
    
    # Product selection
    st.header("Products")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get products
    cursor.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
    products = cursor.fetchall()
    
    # Display products in grid
    cols = st.columns(4)
    cart = st.session_state.get('cart', [])
    
    for idx, product in enumerate(products):
        with cols[idx % 4]:
            st.card(
                f"**{product[1]}**\n\nPrice: ${product[2]:.2f}\n\nStock: {product[3]}"
            )
            if st.button(f"Add to Cart", key=f"add_{product[0]}"):
                cart.append({
                    'id': product[0],
                    'name': product[1],
                    'price': product[2],
                    'quantity': 1
                })
                st.session_state['cart'] = cart
                st.rerun()
    
    # Shopping cart
    st.header("Shopping Cart")
    if cart:
        cart_df = st.dataframe({
            'Product': [item['name'] for item in cart],
            'Price': [item['price'] for item in cart],
            'Qty': [item['quantity'] for item in cart],
            'Total': [item['price'] * item['quantity'] for item in cart]
        })
        
        total = sum(item['price'] * item['quantity'] for item in cart)
        st.metric("Total", f"${total:.2f}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Cart"):
                st.session_state['cart'] = []
                st.rerun()
        
        with col2:
            if st.button("Complete Sale", type="primary"):
                try:
                    cursor = conn.cursor()
                    for item in cart:
                        # Create sale record
                        cursor.execute("""
                            INSERT INTO sales (product_id, quantity, price, total)
                            VALUES (%s, %s, %s, %s)
                        """, (item['id'], item['quantity'], item['price'], 
                              item['price'] * item['quantity']))
                        
                        # Update stock
                        cursor.execute("""
                            UPDATE products SET stock = stock - %s WHERE id = %s
                        """, (item['quantity'], item['id']))
                    
                    conn.commit()
                    log_audit(get_current_user(), "sale", f"Completed sale: {total:.2f}")
                    st.session_state['cart'] = []
                    st.success("Sale completed successfully!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error processing sale: {e}")
    else:
        st.info("Cart is empty")
    
    conn.close()

if __name__ == "__main__":
    main()
