from flask import Blueprint, request, jsonify
from database import get_db_connection

restaurant_menu_bp = Blueprint(
    'restaurant_menu',
    __name__,
    url_prefix='/restaurant-menu'
)

# Get all menu items for a specific restaurant
@restaurant_menu_bp.route('/<int:restaurant_id>', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if restaurant exists and is approved
        restaurant = cursor.execute('''
            SELECT id, restaurant_name, restaurant_phone, address
            FROM partner_applications
            WHERE id = ? AND status = 'approved'
        ''', (restaurant_id,)).fetchone()

        if not restaurant:
            conn.close()
            return jsonify({'error': 'Restaurant not found or not approved'}), 404

        # Get menu items
        menu_items = cursor.execute('''
            SELECT
                id,
                restaurant_id,
                name,
                description,
                price,
                image
            FROM menu_items
            WHERE restaurant_id = ?
            ORDER BY name ASC
        ''', (restaurant_id,)).fetchall()

        conn.close()

        menu_list = [dict(item) for item in menu_items]

        return jsonify({
            'restaurant': dict(restaurant),
            'menu_items': menu_list,
            'total_items': len(menu_list)
        }), 200

    except Exception as e:
        print(f"Error in get_restaurant_menu: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Get single menu item
@restaurant_menu_bp.route('/item/<int:item_id>', methods=['GET'])
def get_menu_item(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        item = cursor.execute('''
            SELECT
                m.id,
                m.restaurant_id,
                m.name,
                m.description,
                m.price,
                m.image,
                p.restaurant_name
            FROM menu_items m
            JOIN partner_applications p ON m.restaurant_id = p.id
            WHERE m.id = ? AND p.status = 'approved'
        ''', (item_id,)).fetchone()

        conn.close()

        if not item:
            return jsonify({'error': 'Menu item not found'}), 404

        return jsonify({'menu_item': dict(item)}), 200

    except Exception as e:
        print(f"Error in get_menu_item: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Search menu items
@restaurant_menu_bp.route('/search', methods=['GET'])
def search_menu_items():
    try:
        query = request.args.get('q', '').strip()

        if not query:
            return jsonify({'error': 'Search query is required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        items = cursor.execute('''
            SELECT
                m.id,
                m.restaurant_id,
                m.name,
                m.description,
                m.price,
                m.image,
                p.restaurant_name
            FROM menu_items m
            JOIN partner_applications p ON m.restaurant_id = p.id
            WHERE p.status = 'approved'
            AND (m.name LIKE ? OR m.description LIKE ?)
            ORDER BY m.name ASC
        ''', (f'%{query}%', f'%{query}%')).fetchall()

        conn.close()

        items_list = [dict(item) for item in items]

        return jsonify({
            'menu_items': items_list,
            'total': len(items_list),
            'query': query
        }), 200

    except Exception as e:
        print(f"Error in search_menu_items: {str(e)}")
        return jsonify({'error': str(e)}), 500
