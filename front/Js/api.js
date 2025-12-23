// API Base URL
const API_URL = 'http://127.0.0.1:5000';

// ========== User API ==========
const userAPI = {
    async register(userData) {
        const response = await fetch(`${API_URL}/users/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        return await response.json();
    },

    async login(credentials) {
        const response = await fetch(`${API_URL}/users/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });
        return await response.json();
    }
};

// ========== Restaurant API ==========
const restaurantAPI = {
    async list() {
        const response = await fetch(`${API_URL}/restaurants/list`);
        return await response.json();
    },

    async get(id) {
        const response = await fetch(`${API_URL}/restaurants/${id}`);
        return await response.json();
    },

    async ownerRegister(ownerData) {
        const response = await fetch(`${API_URL}/restaurants/owner/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ownerData)
        });
        return await response.json();
    },

    async ownerLogin(credentials) {
        const response = await fetch(`${API_URL}/restaurants/owner/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });
        return await response.json();
    },

    async add(restaurantData) {
        const response = await fetch(`${API_URL}/restaurants/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(restaurantData)
        });
        return await response.json();
    },

    async getOrders(restaurantId) {
        const response = await fetch(`${API_URL}/restaurants/orders/${restaurantId}`);
        return await response.json();
    },

    async updateOrderStatus(restaurantOrderId, status) {
        const response = await fetch(`${API_URL}/restaurants/orders/update/${restaurantOrderId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        return await response.json();
    }
};

// ========== Menu API ==========
const menuAPI = {
    async list(restaurantId) {
        const response = await fetch(`${API_URL}/menu/list/${restaurantId}`);
        return await response.json();
    },

    async get(menuItemId) {
        const response = await fetch(`${API_URL}/menu/item/${menuItemId}`);
        return await response.json();
    },

    async add(menuItem) {
        const response = await fetch(`${API_URL}/menu/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(menuItem)
        });
        return await response.json();
    },

    async edit(menuItemId, menuItem) {
        const response = await fetch(`${API_URL}/menu/edit/${menuItemId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(menuItem)
        });
        return await response.json();
    },

    async delete(menuItemId) {
        const response = await fetch(`${API_URL}/menu/delete/${menuItemId}`, {
            method: 'DELETE'
        });
        return await response.json();
    }
};

// ========== Order API ==========
const orderAPI = {
    async place(orderData) {
        const response = await fetch(`${API_URL}/orders/place`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderData)
        });
        return await response.json();
    },

    async getSummary(orderId) {
        const response = await fetch(`${API_URL}/orders/summary/${orderId}`);
        return await response.json();
    },

    async confirm(orderId) {
        const response = await fetch(`${API_URL}/orders/confirm/${orderId}`, {
            method: 'POST'
        });
        return await response.json();
    },

    async getUserOrders(userId) {
        const response = await fetch(`${API_URL}/orders/user/${userId}`);
        return await response.json();
    }
};

// ========== Group Order API ==========
const groupOrderAPI = {
    async create(groupOrderData) {
        const response = await fetch(`${API_URL}/group_orders/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(groupOrderData)
        });
        return await response.json();
    },

    async getSummary(orderId) {
        const response = await fetch(`${API_URL}/group_orders/summary/${orderId}`);
        return await response.json();
    },

    async confirm(orderId) {
        const response = await fetch(`${API_URL}/group_orders/confirm/${orderId}`, {
            method: 'POST'
        });
        return await response.json();
    }
};