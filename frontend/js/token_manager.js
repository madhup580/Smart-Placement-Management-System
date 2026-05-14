/**
 * Token Manager
 * Handles JWT token refresh, storage, and auto-refresh mechanism
 */

class TokenManager {
    constructor() {
        this.accessToken = null;
        this.refreshToken = null;
        this.refreshTimer = null;
        this.refreshCheckInterval = 60000; // Check every minute
        this.init();
    }
    
    init() {
        // Load tokens from storage
        this.loadTokens();
        
        // Start auto-refresh check
        this.startAutoRefresh();
        
        // Listen for storage changes (multi-tab support)
        window.addEventListener('storage', (e) => {
            if (e.key === 'authToken' || e.key === 'refreshToken') {
                this.loadTokens();
            }
        });
    }
    
    loadTokens() {
        this.accessToken = localStorage.getItem('authToken') || localStorage.getItem('token');
        this.refreshToken = localStorage.getItem('refreshToken');
    }
    
    saveTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        
        localStorage.setItem('authToken', accessToken);
        if (refreshToken) {
            localStorage.setItem('refreshToken', refreshToken);
        }
    }
    
    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
    }
    
    /**
     * Get current access token
     */
    getAccessToken() {
        this.loadTokens();
        return this.accessToken;
    }
    
    /**
     * Get current refresh token
     */
    getRefreshToken() {
        this.loadTokens();
        return this.refreshToken;
    }
    
    /**
     * Check if token is expired or near expiry
     */
    isTokenExpiringSoon(token) {
        if (!token) return true;
        
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const exp = payload.exp * 1000; // Convert to milliseconds
            const now = Date.now();
            const timeUntilExpiry = exp - now;
            
            // Refresh if less than 5 minutes remaining
            return timeUntilExpiry < 5 * 60 * 1000;
        } catch (e) {
            return true; // If can't parse, assume expired
        }
    }
    
    /**
     * Refresh access token using refresh token
     */
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        
        if (!refreshToken) {
            console.warn('[TokenManager] No refresh token available');
            return false;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.access_token) {
                    this.saveTokens(data.access_token, refreshToken);
                    console.log('[TokenManager] Token refreshed successfully');
                    return data.access_token;
                }
            } else if (response.status === 401) {
                // Refresh token expired, logout user
                console.warn('[TokenManager] Refresh token expired, logging out');
                this.clearTokens();
                if (window.logout) {
                    window.logout();
                } else {
                    window.location.href = '#auth';
                }
                return false;
            }
        } catch (error) {
            console.error('[TokenManager] Error refreshing token:', error);
            return false;
        }
        
        return false;
    }
    
    /**
     * Start auto-refresh mechanism
     */
    startAutoRefresh() {
        // Clear existing timer
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        // Check token expiry periodically
        this.refreshTimer = setInterval(() => {
            const accessToken = this.getAccessToken();
            
            if (accessToken && this.isTokenExpiringSoon(accessToken)) {
                console.log('[TokenManager] Token expiring soon, refreshing...');
                this.refreshAccessToken();
            }
        }, this.refreshCheckInterval);
    }
    
    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    /**
     * Intercept fetch requests to add token and handle 401
     */
    async fetchWithAuth(url, options = {}) {
        let accessToken = this.getAccessToken();
        
        // Check if token needs refresh before request
        if (accessToken && this.isTokenExpiringSoon(accessToken)) {
            await this.refreshAccessToken();
            accessToken = this.getAccessToken();
        }
        
        // Add authorization header
        if (accessToken) {
            options.headers = options.headers || {};
            options.headers['Authorization'] = `Bearer ${accessToken}`;
        }
        
        // Make request
        const response = await fetch(url, options);
        
        // Handle 401 - token expired
        if (response.status === 401) {
            // Try to refresh token
            const refreshed = await this.refreshAccessToken();
            
            if (refreshed) {
                // Retry request with new token
                accessToken = this.getAccessToken();
                options.headers['Authorization'] = `Bearer ${accessToken}`;
                return fetch(url, options);
            } else {
                // Refresh failed, logout
                this.clearTokens();
                if (window.logout) {
                    window.logout();
                } else {
                    window.location.href = '#auth';
                }
                throw new Error('Authentication failed');
            }
        }
        
        return response;
    }
}

// Initialize token manager
window.tokenManager = new TokenManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TokenManager;
}
