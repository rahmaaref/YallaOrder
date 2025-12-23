# ================== routes/menu_routes.py ==================
from flask import Blueprint, request, jsonify
from database import get_db_connection

menu_bp = Blueprint('menu', __name__)

# Add menu item
@menu_bp.route('/add', methods=['POST'])
def add_menu_item():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO menu_items (restaurant_id, name, description, price, image)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['restaurant_id'], data['name'], data.get('description'), data['price'], data.get('image')))
    
    menu_item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'message': 'Menu item added successfully', 'menu_item_id': menu_item_id})

# Edit menu item
@menu_bp.route('/edit/<int:menu_item_id>', methods=['PUT'])
def edit_menu_item(menu_item_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if menu item exists
    cursor.execute('SELECT * FROM menu_items WHERE id = ?', (menu_item_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'message': 'Menu item not found'}), 404
    
    # Update menu item
    cursor.execute('''
        UPDATE menu_items 
        SET name = ?, description = ?, price = ?, image = ?
        WHERE id = ?
    ''', (data['name'], data.get('description'), data['price'], data.get('image'), menu_item_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Menu item updated successfully'})

# Delete menu item
@menu_bp.route('/delete/<int:menu_item_id>', methods=['DELETE'])
def delete_menu_item(menu_item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if menu item exists
    cursor.execute('SELECT * FROM menu_items WHERE id = ?', (menu_item_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'message': 'Menu item not found'}), 404
    
    # Delete menu item
    cursor.execute('DELETE FROM menu_items WHERE id = ?', (menu_item_id,))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Menu item deleted successfully'})

# List menu items for a restaurant
@menu_bp.route('/list/<int:restaurant_id>', methods=['GET'])
def list_menu(restaurant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
    items = cursor.fetchall()
    conn.close()
    return jsonify([dict(i) for i in items])

# Get single menu item details
@menu_bp.route('/item/<int:menu_item_id>', methods=['GET'])
def get_menu_item(menu_item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM menu_items WHERE id = ?', (menu_item_id,))
    item = cursor.fetchone()
    conn.close()
    
    if item:
        return jsonify(dict(item))
    else:
        return jsonify({'message': 'Menu item not found'}), 404