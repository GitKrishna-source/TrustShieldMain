// Using Vite env variables or fallback to relative path.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const handleError = (error) => {
  console.error("API Error:", error);
  throw error;
};

// --- Dashboard API ---
export const getDashboardOverview = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/overview`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getRiskSummary = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/risk-summary`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getRecentActivity = async (hours = 24, limit = 100) => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/activity?hours=${hours}&limit=${limit}`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getTopRisks = async (limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/top-risks?limit=${limit}`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getAnomalyTrends = async (days = 7) => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/anomaly-trends?days=${days}`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

// --- Alerts API ---
export const getAlerts = async (limit = 50, offset = 0) => {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/?limit=${limit}&offset=${offset}`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getAlertStats = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/stats`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getAlertById = async (alertId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/${alertId}`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const updateAlertStatus = async (alertId, status, resolvedBy = null) => {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/${alertId}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, resolved_by: resolvedBy })
    });
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

// --- Users API ---
export const getUsers = async (limit = 50, offset = 0) => {
  try {
    const response = await fetch(`${API_BASE_URL}/users/?limit=${limit}&offset=${offset}`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};

export const getUserProfile = async (userId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/profile`);
    return await response.json();
  } catch (error) {
    handleError(error);
  }
};
