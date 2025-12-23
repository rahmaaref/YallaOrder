from flask import Blueprint, request, jsonify, current_app
from database import get_db_connection

restaurant_bp = Blueprint('restaurants', __name__)

# Get all approved restaurants for customers
@restaurant_bp.route('/', methods=['GET'])
def get_restaurants():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get only approved restaurants
        restaurants = cursor.execute('''
            SELECT 
                id,
                restaurant_name,
                restaurant_email,
                restaurant_phone,
                address,
                hotline,
                manager_name
            FROM partner_applications 
            WHERE status = 'approved'
            ORDER BY restaurant_name ASC
        ''').fetchall()
        
        conn.close()
        
        restaurants_list = [dict(restaurant) for restaurant in restaurants]
        
        return jsonify({
            'restaurants': restaurants_list,
            'total': len(restaurants_list)
        }), 200
        
    except Exception as e:
        print(f"Error in get_restaurants: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Get single restaurant details
@restaurant_bp.route('/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        restaurant = cursor.execute('''
            SELECT 
                id,
                restaurant_name,
                restaurant_email,
                restaurant_phone,
                address,
                hotline,
                manager_name
            FROM partner_applications 
            WHERE id = ? AND status = 'approved'
        ''', (restaurant_id,)).fetchone()
        
        conn.close()
        
        if not restaurant:
            return jsonify({'error': 'Restaurant not found'}), 404
        
        return jsonify({
            'restaurant': dict(restaurant)
        }), 200
        
    except Exception as e:
        print(f"Error in get_restaurant: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Search restaurants by name
@restaurant_bp.route('/search', methods=['GET'])
def search_restaurants():
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        restaurants = cursor.execute('''
            SELECT 
                id,
                restaurant_name,
                restaurant_email,
                restaurant_phone,
                address,
                hotline,
                manager_name
            FROM partner_applications 
            WHERE status = 'approved' 
            AND restaurant_name LIKE ?
            ORDER BY restaurant_name ASC
        ''', (f'%{query}%',)).fetchall()
        
        conn.close()
        
        restaurants_list = [dict(restaurant) for restaurant in restaurants]
        
        return jsonify({
            'restaurants': restaurants_list,
            'total': len(restaurants_list),
            'query': query
        }), 200
        
    except Exception as e:
        print(f"Error in search_restaurants: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
# Get all orders for a specific restaurant
@restaurant_bp.route('/orders/<int:restaurant_id>', methods=['GET'])
def get_restaurant_orders(restaurant_id):
    """Get all orders for a specific restaurant"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all restaurant orders
        cursor.execute("""
            SELECT 
                ro.id as restaurant_order_id,
                ro.order_id,
                ro.status,
                o.phone,
                o.delivery_location,
                o.delivery_fee,
                o.tax,
                o.total,
                o.created_at,
                o.customer_name,
                o.temp_phone
            FROM restaurant_orders ro
            JOIN orders o ON ro.order_id = o.id
            WHERE ro.restaurant_id = ?
            ORDER BY o.created_at DESC
        """, (restaurant_id,))
        
        restaurant_orders = cursor.fetchall()
        
        orders_list = []
        for ro in restaurant_orders:
            # Get order items for this specific restaurant
            cursor.execute("""
                SELECT 
                    oi.id,
                    oi.quantity,
                    oi.subtotal,
                    mi.name,
                    mi.price
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = ? AND oi.restaurant_id = ?
            """, (ro['order_id'], restaurant_id))
            
            items = cursor.fetchall()
            
            # Calculate subtotal for this restaurant's items
            subtotal = sum(item['subtotal'] for item in items)
            
            orders_list.append({
                'restaurant_order_id': ro['restaurant_order_id'],
                'id': ro['order_id'],
                'status': ro['status'],
                'phone': ro['phone'],
                'customer_name': ro['customer_name'],
                'temp_phone': ro['temp_phone'],
                'delivery_location': ro['delivery_location'],
                'delivery_fee': ro['delivery_fee'],
                'tax': ro['tax'],
                'total': ro['total'],
                'subtotal': subtotal,
                'created_at': ro['created_at'],
                'items': [dict(item) for item in items]
            })
        
        conn.close()
        
        return jsonify(orders_list), 200
        
    except Exception as e:
        print(f"Error getting restaurant orders: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# UPDATE ORDER STATUS - FIXED FOR "on_the_way"
# ============================================
@restaurant_bp.route('/orders/update/<int:restaurant_order_id>', methods=['POST'])
def update_order_status(restaurant_order_id):
    """Update the status of a restaurant order"""
    try:
        data = request.json
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Get valid statuses from app config
        valid_statuses = current_app.config.get('VALID_ORDER_STATUSES', 
                                                ['pending', 'preparing', 'on_the_way', 'delivered', 'cancelled'])
        
        # Case-insensitive validation
        new_status_lower = new_status.lower()
        if new_status_lower not in valid_statuses:
            return jsonify({
                'error': 'Invalid status',
                'valid_statuses': valid_statuses
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the restaurant order status
        cursor.execute("""
            UPDATE restaurant_orders 
            SET status = ?
            WHERE id = ?
        """, (new_status_lower, restaurant_order_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Restaurant order not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status_lower}',
            'status': new_status_lower
        }), 200
        
    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Get pending orders count (for notifications)
@restaurant_bp.route('/orders/<int:restaurant_id>/pending-count', methods=['GET'])
def get_pending_orders_count(restaurant_id):
    """Get count of pending orders for notification badge"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM restaurant_orders
            WHERE restaurant_id = ? AND status = 'pending'
        """, (restaurant_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'count': result['count']
        }), 200
        
    except Exception as e:
        print(f"Error getting pending count: {str(e)}")
        return jsonify({'error': str(e)}), 500