from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='front', static_url_path='')

# Enable CORS with specific configuration
CORS(app, resources={
    r"/*": {
        "origins": ["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:5000", "http://localhost:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})


# Enable CORS
CORS(app)

# Serve frontend files

#Entry point
@app.route('/')
def index():
    return send_from_directory('front', 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    # Serve files from the front folder
    if os.path.exists(os.path.join('front', path)):
        return send_from_directory('front', path)
    # If file doesn't exist, return index.html (for single page app routing)
    return send_from_directory('front', 'index.html')

# API Welcome route
@app.route('/api')
def api_home():
    return jsonify({
        'message': 'Welcome to YallaOrder API',
        'version': '1.0',
        'status': 'Running',
        'endpoints': {
            'users': '/users',
            'restaurants': '/restaurants',
            'menu': '/menu',
            'orders': '/orders',
            'group_orders': '/group_orders',
            'partner_applications': '/partners',
            'restaurant_menu': '/restaurant-menu',
            'cart': '/cart'
        }
    })

# Import routes
from routes.user_routes import user_bp
from routes.restaurant_routes import restaurant_bp
from routes.menu_routes import menu_bp
from routes.order_routes import order_bp
from routes.group_order_routes import group_order_bp
from routes.partner_routes import partner_app_bp
from routes.restaurant_menu_routes import restaurant_menu_bp
from routes.cart_routes import cart_bp

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/users')
app.register_blueprint(restaurant_bp, url_prefix='/restaurants')
app.register_blueprint(menu_bp, url_prefix='/menu')
app.register_blueprint(order_bp, url_prefix='/orders')
app.register_blueprint(group_order_bp, url_prefix='/group_orders')
app.register_blueprint(partner_app_bp, url_prefix='/partners')
app.register_blueprint(restaurant_menu_bp, url_prefix='/restaurant-menu')
app.register_blueprint(cart_bp, url_prefix='/cart')

if __name__ == '__main__':
    app.run(debug=True)