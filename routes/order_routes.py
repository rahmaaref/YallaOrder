# ================== routes/order_routes.py ==================
from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime

order_bp = Blueprint('orders', __name__)

# CREATE ORDER FROM CART (for checkout page)
@order_bp.route('/create', methods=['POST'])
def create_order():
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('cart_uuid'):
            return jsonify({'success': False, 'error': 'Cart UUID is required'}), 400
        if not data.get('phone'):
            return jsonify({'success': False, 'error': 'Phone number is required'}), 400
        if not data.get('delivery_location'):
            return jsonify({'success': False, 'error': 'Delivery location is required'}), 400
        
        cart_uuid = data['cart_uuid']
        customer_name = data.get('customer_name', 'Customer')
        phone = data['phone']
        temp_phone = data.get('temp_phone')
        delivery_location = data['delivery_location']
        order_type = data.get('order_type', 'individual')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cart
        cursor.execute("SELECT id FROM carts WHERE session_id = ?", (cart_uuid,))
        cart = cursor.fetchone()
        
        if not cart:
            conn.close()
            return jsonify({'success': False, 'error': 'Cart not found'}), 404
        
        cart_id = cart['id']
        
        # Get cart items
        cursor.execute("""
            SELECT ci.*, mi.price as current_price
            FROM cart_items ci
            JOIN menu_items mi ON ci.menu_item_id = mi.id
            WHERE ci.cart_id = ?
        """, (cart_id,))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            conn.close()
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        tax = subtotal * 0.14  # 14% tax
        delivery_fee = 20.0
        total = subtotal + tax + delivery_fee
        
        # Create order
        cursor.execute("""
       INSERT INTO orders (
           user_id, order_type, phone, delivery_location, 
           delivery_fee, tax, total, created_at, customer_name, temp_phone
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
   """, (None, order_type, phone, delivery_location, delivery_fee, tax, total, 
         datetime.now().isoformat(), customer_name, temp_phone))
        
        order_id = cursor.lastrowid
        
        # Add order items
        for item in cart_items:
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, menu_item_id, restaurant_id, 
                    quantity, subtotal
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                item['menu_item_id'],
                item['restaurant_id'],
                item['quantity'],
                item['price'] * item['quantity']
            ))
        
        # Create restaurant orders 
        cursor.execute("""
            SELECT DISTINCT restaurant_id FROM cart_items WHERE cart_id = ?
        """, (cart_id,))
        restaurants = cursor.fetchall()
        
        for restaurant in restaurants:
            cursor.execute("""
                INSERT INTO restaurant_orders (order_id, restaurant_id, status)
                VALUES (?, ?, 'pending')
            """, (order_id, restaurant['restaurant_id']))
        
        # Clear the cart
        cursor.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM carts WHERE id = ?", (cart_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Order created successfully',
            'order_id': order_id,
            'total': total,
            'customer_name': customer_name,
            'temp_phone': temp_phone
        }), 201
        
    except Exception as e:
        print(f"Error creating order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# GET ORDER BY ID (for order confirmation page)
@order_bp.route('/<int:order_id>', methods=['GET'])
def get_order(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            conn.close()
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        # Get order items with menu item details
        cursor.execute("""
            SELECT 
                oi.*,
                mi.name as item_name,
                mi.price
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        """, (order_id,))
        items = cursor.fetchall()
        
        conn.close()
        
        # Convert to dict
        order_dict = dict(order)
        items_list = [dict(item) for item in items]
        
        return jsonify({
            'success': True,
            'order': {
                'id': order_dict['id'],
                'customer_name': order_dict['customer_name'],
                'phone': order_dict['phone'],
                'temp_phone': None,  
                'delivery_location': order_dict['delivery_location'],
                'order_type': order_dict['order_type'],
                'delivery_fee': order_dict['delivery_fee'],
                'tax': order_dict['tax'],
                'total': order_dict['total'],
                'created_at': order_dict['created_at'],
                'items': items_list
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Place individual order 
@order_bp.route('/place', methods=['POST'])
def place_order():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO orders (user_id, order_type, phone, delivery_location, delivery_fee, tax, total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('user_id'), 'individual', data['phone'], data['delivery_location'],
        data.get('delivery_fee', 0), data.get('tax', 0), data.get('total', 0)
    ))
    order_id = cursor.lastrowid

    for item in data['items']:
        cursor.execute('''
            INSERT INTO order_items (order_id, menu_item_id, restaurant_id, quantity, subtotal)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, item['menu_item_id'], item['restaurant_id'], item['quantity'], item['subtotal']))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Order placed', 'order_id': order_id})


# Individual order summary
@order_bp.route('/summary/<int:order_id>', methods=['GET'])
def order_summary(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        return jsonify({'message': 'Order not found'}), 404
    cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
    items = cursor.fetchall()
    conn.close()
    return jsonify({'order': dict(order), 'items': [dict(i) for i in items]})


# Confirm order and create restaurant orders 
@order_bp.route('/confirm/<int:order_id>', methods=['POST'])
def confirm_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get distinct restaurants from order items
    cursor.execute('SELECT DISTINCT restaurant_id FROM order_items WHERE order_id = ?', (order_id,))
    restaurants = cursor.fetchall()
    
    # Create restaurant orders for each restaurant
    for r in restaurants:
        cursor.execute('''
            INSERT INTO restaurant_orders (order_id, restaurant_id, status)
            VALUES (?, ?, ?)
        ''', (order_id, r['restaurant_id'], 'pending'))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Order confirmed and sent to restaurants'})


# List all orders for a user by user_id
@order_bp.route('/user/id/<int:user_id>', methods=['GET'])
def user_orders(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])


# Get user orders by phone number
@order_bp.route('/user/phone/<string:phone>', methods=['GET'])
def get_user_orders_by_phone(phone):
    """Get all orders for a user by phone number"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"DEBUG: Searching for orders with phone: {phone}")  
        
        # Get all orders for this phone number
        cursor.execute("""
            SELECT * FROM orders WHERE phone = ? ORDER BY created_at DESC
        """, (phone,))
        
        orders = cursor.fetchall()
        
        print(f"DEBUG: Found {len(orders)} orders")  
        
        if not orders:
            conn.close()
            return jsonify([]), 200
        
        orders_list = []
        for order in orders:
            order_dict = dict(order)
            
            # Get order items
            cursor.execute("""
                SELECT 
                    oi.id,
                    oi.quantity,
                    oi.subtotal,
                    mi.name as item_name,
                    mi.price
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = ?
            """, (order_dict['id'],))
            
            items = cursor.fetchall()
            
            # Get status from restaurant_orders
            cursor.execute("""
                SELECT status FROM restaurant_orders WHERE order_id = ? LIMIT 1
            """, (order_dict['id'],))
            
            status_row = cursor.fetchone()
            status = status_row['status'] if status_row else 'pending'
            
            orders_list.append({
                'id': order_dict['id'],
                'phone': order_dict['phone'],
                'customer_name': order_dict.get('customer_name', 'Customer'),
                'temp_phone': order_dict.get('temp_phone'),
                'delivery_location': order_dict['delivery_location'],
                'order_type': order_dict['order_type'],
                'delivery_fee': order_dict['delivery_fee'],
                'tax': order_dict['tax'],
                'total': order_dict['total'],
                'created_at': order_dict['created_at'],
                'status': status,
                'items': [dict(item) for item in items]
            })
        
        conn.close()
        
        print(f"DEBUG: Returning {len(orders_list)} orders")  # Debug log
        
        return jsonify(orders_list), 200
        
    except Exception as e:
        print(f"Error getting user orders: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500