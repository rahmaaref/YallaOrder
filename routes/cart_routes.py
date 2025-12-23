from flask import Blueprint, request, jsonify
import sqlite3
from datetime import datetime

cart_bp = Blueprint('cart', __name__)

DATABASE = 'yallaorder.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ========== CART ENDPOINTS ==========

@cart_bp.route('/add', methods=['POST'])
def add_to_cart():
    """Add item to cart or update quantity if exists"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')
        menu_item_id = data.get('menu_item_id')
        restaurant_id = data.get('restaurant_id')
        item_name = data.get('item_name')
        price = data.get('price')
        quantity = data.get('quantity', 1)

        if not all([cart_uuid, menu_item_id, restaurant_id, item_name, price]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Get or create cart
        cursor.execute('SELECT id FROM carts WHERE session_id = ?', (cart_uuid,))
        cart = cursor.fetchone()
        
        if not cart:
            cursor.execute(
                'INSERT INTO carts (session_id, user_id, created_at, updated_at) VALUES (?, NULL, datetime("now"), datetime("now"))',
                (cart_uuid,)
            )
            cart_id = cursor.lastrowid
        else:
            cart_id = cart['id']
            # Update cart timestamp
            cursor.execute('UPDATE carts SET updated_at = datetime("now") WHERE id = ?', (cart_id,))

        # Check if item already exists in cart
        cursor.execute(
            'SELECT id, quantity FROM cart_items WHERE cart_id = ? AND menu_item_id = ?',
            (cart_id, menu_item_id)
        )
        existing_item = cursor.fetchone()

        if existing_item:
            # Update quantity
            new_quantity = existing_item['quantity'] + quantity
            cursor.execute(
                'UPDATE cart_items SET quantity = ?, updated_at = datetime("now") WHERE id = ?',
                (new_quantity, existing_item['id'])
            )
            item_id = existing_item['id']
        else:
            # Insert new item
            cursor.execute(
                '''INSERT INTO cart_items 
                   (cart_id, menu_item_id, restaurant_id, item_name, price, quantity, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime("now"), datetime("now"))''',
                (cart_id, menu_item_id, restaurant_id, item_name, price, quantity)
            )
            item_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Item added to cart',
            'cart_item_id': item_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cart_bp.route('/view', methods=['POST'])
def view_cart():
    """Get all items in cart"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')
        user_id = data.get('user_id')  # Optional for logged-in users

        if not cart_uuid:
            return jsonify({'success': False, 'error': 'cart_uuid required'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Get cart
        if user_id:
            cursor.execute('SELECT id FROM carts WHERE user_id = ? OR session_id = ?', (user_id, cart_uuid))
        else:
            cursor.execute('SELECT id FROM carts WHERE session_id = ?', (cart_uuid,))
        
        cart = cursor.fetchone()

        if not cart:
            return jsonify({'success': True, 'items': [], 'total_items': 0})

        cart_id = cart['id']

        # Get all cart items
        cursor.execute(
            '''SELECT 
                ci.id,
                ci.menu_item_id,
                ci.restaurant_id,
                ci.item_name,
                ci.price,
                ci.quantity,
                ci.created_at,
                r.name as restaurant_name
               FROM cart_items ci
               LEFT JOIN restaurants r ON ci.restaurant_id = r.id
               WHERE ci.cart_id = ?
               ORDER BY ci.created_at DESC''',
            (cart_id,)
        )
        
        items = cursor.fetchall()
        conn.close()

        cart_items = []
        for item in items:
            cart_items.append({
                'id': item['id'],
                'menu_item_id': item['menu_item_id'],
                'restaurant_id': item['restaurant_id'],
                'restaurant_name': item['restaurant_name'],
                'item_name': item['item_name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'subtotal': item['price'] * item['quantity'],
                'created_at': item['created_at']
            })

        return jsonify({
            'success': True,
            'items': cart_items,
            'total_items': len(cart_items)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cart_bp.route('/update', methods=['PUT'])
def update_cart_item():
    """Update quantity of cart item"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')
        cart_item_id = data.get('cart_item_id')
        quantity = data.get('quantity')

        if not all([cart_uuid, cart_item_id, quantity]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        if quantity < 1:
            return jsonify({'success': False, 'error': 'Quantity must be at least 1'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Verify cart ownership and update
        cursor.execute(
            '''UPDATE cart_items 
               SET quantity = ?, updated_at = datetime("now")
               WHERE id = ? 
               AND cart_id IN (SELECT id FROM carts WHERE session_id = ?)''',
            (quantity, cart_item_id, cart_uuid)
        )

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Cart item not found'}), 404

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Cart item updated'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cart_bp.route('/remove', methods=['DELETE'])
def remove_cart_item():
    """Remove item from cart"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')
        cart_item_id = data.get('cart_item_id')

        if not all([cart_uuid, cart_item_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Verify cart ownership and delete
        cursor.execute(
            '''DELETE FROM cart_items 
               WHERE id = ? 
               AND cart_id IN (SELECT id FROM carts WHERE session_id = ?)''',
            (cart_item_id, cart_uuid)
        )

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Cart item not found'}), 404

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Item removed from cart'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cart_bp.route('/clear', methods=['DELETE'])
def clear_cart():
    """Clear all items from cart"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')

        if not cart_uuid:
            return jsonify({'success': False, 'error': 'cart_uuid required'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Get cart ID
        cursor.execute('SELECT id FROM carts WHERE session_id = ?', (cart_uuid,))
        cart = cursor.fetchone()

        if not cart:
            conn.close()
            return jsonify({'success': True, 'message': 'Cart already empty'})

        cart_id = cart['id']

        # Delete all items
        cursor.execute('DELETE FROM cart_items WHERE cart_id = ?', (cart_id,))
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Removed {deleted_count} items from cart'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cart_bp.route('/count', methods=['POST'])
def get_cart_count():
    """Get total number of items in cart"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')

        if not cart_uuid:
            return jsonify({'success': False, 'error': 'cart_uuid required'}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            '''SELECT COUNT(*) as count
               FROM cart_items ci
               JOIN carts c ON ci.cart_id = c.id
               WHERE c.session_id = ?''',
            (cart_uuid,)
        )
        
        result = cursor.fetchone()
        conn.close()

        return jsonify({
            'success': True,
            'count': result['count']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@cart_bp.route('/summary', methods=['POST'])
def get_cart_summary():
    """Get cart summary with totals"""
    try:
        data = request.json
        cart_uuid = data.get('cart_uuid')

        if not cart_uuid:
            return jsonify({'success': False, 'error': 'cart_uuid required'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Get cart
        cursor.execute('SELECT id FROM carts WHERE session_id = ?', (cart_uuid,))
        cart = cursor.fetchone()

        if not cart:
            return jsonify({
                'success': True,
                'items': [],
                'subtotal': 0,
                'tax': 0,
                'delivery_fee': 0,
                'total': 0
            })

        cart_id = cart['id']

        # Get all items with subtotals
        cursor.execute(
            '''SELECT 
                ci.item_name,
                ci.price,
                ci.quantity,
                (ci.price * ci.quantity) as subtotal,
                r.name as restaurant_name
               FROM cart_items ci
               LEFT JOIN restaurants r ON ci.restaurant_id = r.id
               WHERE ci.cart_id = ?''',
            (cart_id,)
        )
        
        items = cursor.fetchall()
        conn.close()

        # Calculate totals
        subtotal = sum(item['subtotal'] for item in items)
        tax = subtotal * 0.14  # 14% tax
        delivery_fee = 25.0 if len(items) > 0 else 0.0
        total = subtotal + tax + delivery_fee

        cart_items = []
        for item in items:
            cart_items.append({
                'item_name': item['item_name'],
                'restaurant_name': item['restaurant_name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'subtotal': item['subtotal']
            })

        return jsonify({
            'success': True,
            'items': cart_items,
            'subtotal': round(subtotal, 2),
            'tax': round(tax, 2),
            'delivery_fee': round(delivery_fee, 2),
            'total': round(total, 2)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500