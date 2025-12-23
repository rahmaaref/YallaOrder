// ========== Local Storage Helpers ==========
const storage = {
    setUser(user) {
        localStorage.setItem('user', JSON.stringify(user));
    },

    getUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    },

    removeUser() {
        localStorage.removeItem('user');
    },

    isLoggedIn() {
        return this.getUser() !== null;
    },

    setCart(cart) {
        localStorage.setItem('cart', JSON.stringify(cart));
    },

    getCart() {
        const cart = localStorage.getItem('cart');
        return cart ? JSON.parse(cart) : [];
    },

    clearCart() {
        localStorage.removeItem('cart');
    },

    addToCart(item) {
        const cart = this.getCart();
        const existingItem = cart.find(i => i.menu_item_id === item.menu_item_id);
        
        if (existingItem) {
            existingItem.quantity += item.quantity;
        } else {
            cart.push(item);
        }
        
        this.setCart(cart);
    },

    removeFromCart(menuItemId) {
        let cart = this.getCart();
        cart = cart.filter(item => item.menu_item_id !== menuItemId);
        this.setCart(cart);
    },

    updateCartQuantity(menuItemId, quantity) {
        const cart = this.getCart();
        const item = cart.find(i => i.menu_item_id === menuItemId);
        
        if (item) {
            item.quantity = quantity;
            this.setCart(cart);
        }
    },

    getCartTotal() {
        const cart = this.getCart();
        return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
    },

    getCartCount() {
        const cart = this.getCart();
        return cart.reduce((count, item) => count + item.quantity, 0);
    }
};

// ========== UI Helpers ==========
const ui = {
    showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => alertDiv.remove(), 5000);
    },

    showLoading(element) {
        element.innerHTML = '<div class="spinner"></div>';
    },

    hideLoading(element) {
        const spinner = element.querySelector('.spinner');
        if (spinner) spinner.remove();
    },

    updateNavbar() {
        const user = storage.getUser();
        const userInfo = document.querySelector('.user-info');
        
        if (user && userInfo) {
            userInfo.innerHTML = `
                <span class="user-name">Hello, ${user.first_name}!</span>
                <button class="btn btn-small btn-secondary" onclick="logout()">Logout</button>
            `;
        }
    },

    updateCartBadge() {
        const badge = document.querySelector('.cart-badge');
        if (badge) {
            const count = storage.getCartCount();
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }
};

// ========== Format Helpers ==========
const format = {
    currency(amount) {
        return `${amount.toFixed(2)} EGP`;
    },

    date(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};

// ========== Validation Helpers ==========
const validate = {
    phone(phone) {
        const phoneRegex = /^01[0-2,5]{1}[0-9]{8}$/;
        return phoneRegex.test(phone);
    },

    email(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    required(value) {
        return value && value.trim().length > 0;
    },

    minLength(value, length) {
        return value && value.length >= length;
    }
};

// ========== Global Functions ==========
function logout() {
    storage.removeUser();
    storage.clearCart();
    window.location.href = 'index.html';
}

function checkAuth() {
    if (!storage.isLoggedIn()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

// Update UI on page load
document.addEventListener('DOMContentLoaded', () => {
    ui.updateNavbar();
    ui.updateCartBadge();
});