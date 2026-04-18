import React, { useEffect, useState } from 'react';
import { getEvents } from '../services/api';

const Timeline = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      setLoading(true);
      const data = await getEvents(100, 0);
      if (data && data.events) {
        setEvents(data.events);
      }
      setLoading(false);
    };
    fetchEvents();
  }, []);

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Security Timeline</h1>
        <p style={{ color: 'var(--text-muted)' }}>Chronological feed of user activities.</p>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        {loading ? (
            <div style={{ color: 'var(--text-muted)' }}>Loading timeline...</div>
        ) : (
            <div className="timeline-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {events.map((event, i) => (
                    <div key={event.event_id || i} style={{ 
                        background: 'rgba(255,255,255,0.03)', 
                        padding: '16px', 
                        borderRadius: '8px',
                        borderLeft: '4px solid var(--primary)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontWeight: 600 }}>{event.user_id}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                {new Date(event.timestamp).toLocaleString()}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ 
                                color: '#06B6D4', 
                                background: 'rgba(6, 182, 212, 0.1)', 
                                padding: '4px 8px', 
                                borderRadius: '4px',
                                fontSize: '0.85rem',
                                textTransform: 'uppercase'
                            }}>
                                {event.event_type}
                            </span>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                IP: {event.source_ip || 'N/A'}
                            </span>
                        </div>
                        {event.resource && (
                            <div style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--text-main)' }}>
                                <span style={{color: 'var(--text-muted)'}}>Resource:</span> {event.resource}
                            </div>
                        )}
                        {event.destination && (
                            <div style={{ marginTop: '4px', fontSize: '0.85rem', color: 'var(--text-main)' }}>
                                <span style={{color: 'var(--text-muted)'}}>Destination:</span> {event.destination}
                            </div>
                        )}
                    </div>
                ))}
                {events.length === 0 && <div style={{ color: 'var(--text-muted)' }}>No recent events found.</div>}
            </div>
        )}
      </div>
    </div>
  );
};

export default Timeline;
