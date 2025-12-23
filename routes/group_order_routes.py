# ================== routes/group_order_routes.py ==================
from flask import Blueprint, request, jsonify
from database import get_db_connection
from datetime import datetime

group_order_bp = Blueprint('group_orders', __name__)

# Create group order
@group_order_bp.route('/create', methods=['POST'])
def create_group_order():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calculate totals
        subtotal = sum(item['subtotal'] for item in data['items'])
        tax = data.get('tax', subtotal * 0.14)
        delivery_fee = data.get('delivery_fee', 20)
        total = subtotal + tax + delivery_fee

        # Create main order
        cursor.execute('''
            INSERT INTO orders (
                user_id, order_type, phone, delivery_location, 
                delivery_fee, tax, total, created_at, customer_name, temp_phone
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            None,  # user_id (null for group orders)
            'group',
            data['phone'],
            data['delivery_location'],
            delivery_fee,
            tax,
            total,
            datetime.now().isoformat(),
            data.get('customer_name', 'Group Order'),
            data.get('temp_phone')
        ))
        order_id = cursor.lastrowid

        # Create group order entry
        cursor.execute('''
            INSERT INTO group_orders (order_id, num_people) 
            VALUES (?, ?)
        ''', (order_id, data['num_people']))
        group_order_id = cursor.lastrowid

        # Create group members
        member_ids = {}
        for i, member_name in enumerate(data['members'], start=1):
            cursor.execute('''
                INSERT INTO group_members (group_order_id, member_name, person_index) 
                VALUES (?, ?, ?)
            ''', (group_order_id, member_name, i))
            member_ids[member_name] = cursor.lastrowid

        # Add order items
        for item in data['items']:
            cursor.execute('''
                INSERT INTO order_items (
                    order_id, menu_item_id, restaurant_id, quantity, subtotal
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                order_id,
                item['menu_item_id'],
                item['restaurant_id'],
                item['quantity'],
                item['subtotal']
            ))
            order_item_id = cursor.lastrowid

            # Link to group member if available
            if 'orderedBy' in item:
                member_id = member_ids.get(item['orderedBy'])
                if member_id:
                    cursor.execute('''
                        INSERT INTO group_order_items (group_member_id, order_item_id) 
                        VALUES (?, ?)
                    ''', (member_id, order_item_id))

        # Create restaurant orders for each unique restaurant
        cursor.execute('''
            SELECT DISTINCT restaurant_id 
            FROM order_items 
            WHERE order_id = ?
        ''', (order_id,))
        restaurants = cursor.fetchall()
        
        for restaurant in restaurants:
            cursor.execute('''
                INSERT INTO restaurant_orders (order_id, restaurant_id, status) 
                VALUES (?, ?, ?)
            ''', (order_id, restaurant['restaurant_id'], 'pending'))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Group order created successfully',
            'order_id': order_id
        }), 201

    except Exception as e:
        print(f"Error creating group order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Group order summary
@group_order_bp.route('/summary/<int:order_id>', methods=['GET'])
def group_order_summary(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get order
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            conn.close()
            return jsonify({'message': 'Group order not found'}), 404
        
        # Get group order
        cursor.execute('SELECT * FROM group_orders WHERE order_id = ?', (order_id,))
        group = cursor.fetchone()
        
        # Get members
        cursor.execute('SELECT * FROM group_members WHERE group_order_id = ?', (group['id'],))
        members = cursor.fetchall()

        # Get items for each member
        member_items = {}
        for member in members:
            cursor.execute('''
                SELECT oi.*, mi.name as item_name, mi.price
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                JOIN group_order_items goi ON oi.id = goi.order_item_id
                WHERE goi.group_member_id = ?
            ''', (member['id'],))
            items = cursor.fetchall()
            member_items[member['member_name']] = [dict(item) for item in items]

        conn.close()
        
        return jsonify({
            'order': dict(order),
            'group': dict(group),
            'members': [dict(m) for m in members],
            'member_items': member_items
        }), 200

    except Exception as e:
        print(f"Error getting group order summary: {e}")
        return jsonify({'error': str(e)}), 500


# Confirm group order
@group_order_bp.route('/confirm/<int:order_id>', methods=['POST'])
def confirm_group_order(order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get distinct restaurants from order items
        cursor.execute('''
            SELECT DISTINCT restaurant_id 
            FROM order_items 
            WHERE order_id = ?
        ''', (order_id,))
        restaurants = cursor.fetchall()
        
        # Create restaurant orders for each restaurant
        for restaurant in restaurants:
            cursor.execute('''
                INSERT INTO restaurant_orders (order_id, restaurant_id, status) 
                VALUES (?, ?, ?)
            ''', (order_id, restaurant['restaurant_id'], 'pending'))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Group order confirmed and sent to restaurants'
        }), 200

    except Exception as e:
        print(f"Error confirming group order: {e}")
        return jsonify({'error': str(e)}), 500