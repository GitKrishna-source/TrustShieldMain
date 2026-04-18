import React, { useEffect, useState } from 'react';
import { getAlerts, updateAlertStatus } from '../services/api';

const Alerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    setLoading(true);
    const data = await getAlerts(50, 0);
    if (data && data.alerts) {
      setAlerts(data.alerts);
    }
    setLoading(false);
  };

  const handleStatusChange = async (alertId, newStatus) => {
    await updateAlertStatus(alertId, newStatus, "admin_user");
    // Refresh to show updated status
    fetchAlerts();
  };

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Security Alerts</h1>
        <p style={{ color: 'var(--text-muted)' }}>Manage and triage detected behavioral anomalies.</p>
      </div>

      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '24px', color: 'var(--text-muted)' }}>Loading alerts...</div>
        ) : (
          <table className="glass-table">
            <thead>
              <tr>
                <th>Alert ID</th>
                <th>User ID</th>
                <th>Risk Level</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length > 0 ? alerts.map((alert) => (
                <tr key={alert.alert_id}>
                  <td>{alert.alert_id}</td>
                  <td>{alert.user_id}</td>
                  <td>
                    <span className={`badge badge-${alert.risk_level.toLowerCase()}`}>
                      {alert.risk_level}
                    </span>
                  </td>
                  <td>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.1)', color: '#fff' }}>
                      {alert.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(alert.created_at).toLocaleString()}</td>
                  <td>
                    <select 
                      onChange={(e) => handleStatusChange(alert.alert_id, e.target.value)}
                      value={alert.status}
                      style={{ background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', padding: '6px', borderRadius: '6px' }}
                    >
                      <option value="NEW">New</option>
                      <option value="OPEN">Open</option>
                      <option value="INVESTIGATING">Investigating</option>
                      <option value="RESOLVED">Resolved</option>
                      <option value="FALSE_POSITIVE">False Positive</option>
                    </select>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '24px' }}>No alerts found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default Alerts;
