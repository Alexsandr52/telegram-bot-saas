/**
 * API Configuration and Helper Functions
 */

const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';

// Storage keys
const STORAGE_KEYS = {
    TOKEN: 'auth_token',
    MASTER_ID: 'master_id'
};

/**
 * Make API request
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const mergedOptions = { ...defaultOptions, ...options };

    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || 'API Error');
        }

        return data;
    } catch (error) {
        console.error('API Request failed:', error);
        throw error;
    }
}

/**
 * Authentication API
 */
const AuthAPI = {
    async login(token) {
        return apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ token })
        });
    },

    logout(token) {
        return apiRequest(`/auth/logout?token=${token}`, {
            method: 'POST'
        });
    }
};

/**
 * Bots API
 */
const BotsAPI = {
    async getAll(token) {
        return apiRequest(`/bots?token=${token}`);
    },

    async getById(botId, token) {
        return apiRequest(`/bots/${botId}?token=${token}`);
    }
};

/**
 * Services API
 */
const ServicesAPI = {
    async getByBot(botId, token) {
        return apiRequest(`/services/${botId}?token=${token}`);
    },

    async create(botId, data, token) {
        return apiRequest(`/services/${botId}?token=${token}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async update(serviceId, data, token) {
        return apiRequest(`/services/${serviceId}?token=${token}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async delete(serviceId, token) {
        return apiRequest(`/services/${serviceId}?token=${token}`, {
            method: 'DELETE'
        });
    }
};

/**
 * Schedules API
 */
const SchedulesAPI = {
    async getByBot(botId, token) {
        return apiRequest(`/schedules/${botId}?token=${token}`);
    },

    async update(botId, schedules, token) {
        return apiRequest(`/schedules/${botId}?token=${token}`, {
            method: 'PUT',
            body: JSON.stringify({ schedules })
        });
    }
};

/**
 * Appointments API
 */
const AppointmentsAPI = {
    async getByBot(botId, token, status = null, limit = 50, offset = 0) {
        let url = `/appointments/${botId}?token=${token}&limit=${limit}&offset=${offset}`;
        if (status) {
            url += `&status_filter=${status}`;
        }
        return apiRequest(url);
    },

    async updateStatus(appointmentId, status, token) {
        return apiRequest(`/appointments/${appointmentId}/status?token=${token}`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    }
};

/**
 * Storage helpers
 */
const Storage = {
    setToken(token) {
        localStorage.setItem(STORAGE_KEYS.TOKEN, token);
    },

    getToken() {
        return localStorage.getItem(STORAGE_KEYS.TOKEN);
    },

    setMasterId(masterId) {
        localStorage.setItem(STORAGE_KEYS.MASTER_ID, masterId);
    },

    getMasterId() {
        return localStorage.getItem(STORAGE_KEYS.MASTER_ID);
    },

    clear() {
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
        localStorage.removeItem(STORAGE_KEYS.MASTER_ID);
    },

    isAuthenticated() {
        return !!this.getToken();
    }
};

/**
 * Check authentication and redirect if needed
 */
function checkAuth() {
    if (!Storage.isAuthenticated()) {
        window.location.href = '/';
        return false;
    }
    return true;
}

/**
 * Logout and redirect to login
 */
function logout() {
    Storage.clear();
    window.location.href = '/';
}
