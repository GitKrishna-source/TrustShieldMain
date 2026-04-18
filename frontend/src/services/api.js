const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
};

const handleError = (error) => {
  console.error("API Error:", error);
  throw error;
};

const fetchWithAuth = async (url, options = {}) => {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getAuthHeaders(),
        ...(options.headers || {}),
      },
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
      }
      const errText = await response.text();
      throw new Error(errText || `HTTP error! status: ${response.status}`);
    }
    
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  } catch (error) {
    handleError(error);
  }
};

// --- Auth API ---
export const login = async (email, password) => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
        throw new Error('Login failed');
    }
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getCurrentUser = async () => {
  return await fetchWithAuth(`${API_BASE_URL}/auth/me`);
};

// --- Dashboard API ---
export const getDashboardOverview = async () => {
  return await fetchWithAuth(`${API_BASE_URL}/dashboard/overview`);
};

export const getRiskSummary = async () => {
  return await fetchWithAuth(`${API_BASE_URL}/dashboard/risk-summary`);
};

export const getRecentActivity = async (hours = 24, limit = 100) => {
  return await fetchWithAuth(`${API_BASE_URL}/dashboard/activity?hours=${hours}&limit=${limit}`);
};

export const getTopRisks = async (limit = 10) => {
  return await fetchWithAuth(`${API_BASE_URL}/dashboard/top-risks?limit=${limit}`);
};

export const getAnomalyTrends = async (days = 7) => {
  return await fetchWithAuth(`${API_BASE_URL}/dashboard/anomaly-trends?days=${days}`);
};

// --- Alerts API ---
export const getAlerts = async (limit = 50, offset = 0) => {
  return await fetchWithAuth(`${API_BASE_URL}/alerts/?limit=${limit}&offset=${offset}`);
};

export const getAlertStats = async () => {
  return await fetchWithAuth(`${API_BASE_URL}/alerts/stats`);
};

export const getAlertById = async (alertId) => {
  return await fetchWithAuth(`${API_BASE_URL}/alerts/${alertId}`);
};

export const updateAlertStatus = async (alertId, status, resolvedBy = null) => {
  return await fetchWithAuth(`${API_BASE_URL}/alerts/${alertId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status, resolved_by: resolvedBy })
  });
};

// --- Users API ---
export const getUsers = async (limit = 50, offset = 0) => {
  return await fetchWithAuth(`${API_BASE_URL}/users/?limit=${limit}&offset=${offset}`);
};

export const getUserProfile = async (userId) => {
  return await fetchWithAuth(`${API_BASE_URL}/users/${userId}/profile`);
};

// --- Events API ---
export const getEvents = async (limit = 50, offset = 0) => {
    return await fetchWithAuth(`${API_BASE_URL}/events/?limit=${limit}&offset=${offset}`);
};

export const getUserEvents = async (userId, limit = 50) => {
    return await fetchWithAuth(`${API_BASE_URL}/events/user/${userId}?limit=${limit}`);
};
