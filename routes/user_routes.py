# ================== routes/user_routes.py ==================
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

user_bp = Blueprint('users', __name__)

# Register
@user_bp.route('/register', methods=['POST'])
def register_user():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if phone already exists
    cursor.execute('SELECT * FROM users WHERE phone = ?', (data['phone'],))
    if cursor.fetchone():
        conn.close()
        return jsonify({'message': 'Phone already exists'}), 400
    
    # Hash the password
    hashed_password = generate_password_hash(data['password'])
    
    cursor.execute('''
        INSERT INTO users (first_name, last_name, phone, password)
        VALUES (?, ?, ?, ?)
    ''', (data['first_name'], data['last_name'], data['phone'], hashed_password))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'User registered successfully'})

# Login
@user_bp.route('/login', methods=['POST'])
def login_user():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE phone = ?', (data['phone'],))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], data['password']):
        return jsonify({
            'message': 'Login successful', 
            'user_id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name']
        })
    else:
        return jsonify({'message': 'Invalid credentials'}), 401