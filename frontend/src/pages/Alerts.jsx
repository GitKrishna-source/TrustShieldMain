import React, { useEffect, useState } from 'react';
import { getAlerts, updateAlertStatus } from '../services/api';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

const Alerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
        const data = await getAlerts(50, 0);
        if (data && data.alerts) {
            setAlerts(data.alerts);
        }
    } catch(err) {
        console.error("Failed fetching alerts", err);
    } finally {
        setLoading(false);
    }
  };

  const handleStatusChange = async (alertId, newStatus) => {
    try {
        await updateAlertStatus(alertId, newStatus);
        fetchAlerts();
    } catch(err) {
        console.error("Failed to update status", err);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
        case 'open': return <AlertCircle size={14} color="var(--status-critical)" />;
        case 'resolved': return <CheckCircle size={14} color="var(--status-low)" />;
        default: return <Clock size={14} color="var(--status-medium)" />;
    }
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
                <th>Alert Info</th>
                <th>User ID</th>
                <th>Risk Score</th>
                <th>Status</th>
                <th>Detected At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.length > 0 ? alerts.map((alert) => (
                <tr key={alert.alert_id}>
                  <td>
                    <div style={{fontWeight: 600, fontSize: '0.9rem', marginBottom:'4px'}}>{alert.title}</div>
                    <div style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>{alert.description}</div>
                  </td>
                  <td>{alert.user_id}</td>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>    
                        <span style={{fontWeight: 600}}>{alert.risk_score}</span>
                        <span className={`badge badge-${alert.risk_level.toLowerCase()}`}>
                        {alert.risk_level}
                        </span>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}>
                      {getStatusIcon(alert.status)}
                      {alert.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{new Date(alert.created_at).toLocaleString()}</td>
                  <td>
                    <select 
                      onChange={(e) => handleStatusChange(alert.alert_id, e.target.value)}
                      value={alert.status}
                      style={{ 
                        background: 'rgba(0,0,0,0.5)', 
                        color: '#fff', 
                        border: '1px solid rgba(255,255,255,0.2)', 
                        padding: '6px 12px', 
                        borderRadius: '6px',
                        outline: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      <option value="open">Open</option>
                      <option value="investigating">Investigating</option>
                      <option value="resolved">Resolved</option>
                      <option value="false_positive">False Positive</option>
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
