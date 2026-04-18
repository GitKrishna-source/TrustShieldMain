import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getUserProfile, getUserEvents } from '../services/api';
import { ArrowLeft, AlertTriangle } from 'lucide-react';

const UserProfile = () => {
    const { id } = useParams();
    const [profile, setProfile] = useState(null);
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchProfileData = async () => {
            setLoading(true);
            try {
                const profileData = await getUserProfile(id);
                setProfile(profileData);
                
                const eventData = await getUserEvents(id, 20);
                if (eventData && eventData.events) {
                    setEvents(eventData.events);
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        fetchProfileData();
    }, [id]);

    if (loading) return <div className="animate-fade-in" style={{color: 'var(--text-muted)'}}>Loading profile...</div>;
    if (!profile) return <div className="animate-fade-in" style={{color: 'var(--status-critical)'}}>Failed to load profile.</div>;

    const riskScore = profile.risk_score || 0;
    const riskLevel = profile.risk_level || 'LOW';
    
    return (
        <div className="animate-fade-in">
            <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
                <Link to="/users" style={{ color: '#fff', textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
                    <ArrowLeft size={20} />
                </Link>
                <div>
                    <h1 style={{ fontSize: '2rem', marginBottom: '4px' }}>Profile: {profile.user_id}</h1>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Risk Score: <strong style={{color: '#fff'}}>{riskScore}</strong></span>
                        <span className={`badge badge-${riskLevel.toLowerCase()}`}>{riskLevel}</span>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', marginBottom: '24px' }}>
                
                <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ marginBottom: '16px', color: 'var(--primary)' }}>Behavioral Baseline</h3>
                    {profile.baseline && profile.baseline.event_type_distribution ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <p style={{fontSize: '0.85rem', color: 'var(--text-muted)'}}>Events Analyzed: <span style={{color: '#fff'}}>{profile.baseline.total_events_analysed}</span></p>
                            <p style={{fontSize: '0.85rem', color: 'var(--text-muted)'}}>Avg Events/Day: <span style={{color: '#fff'}}>{profile.baseline.avg_events_per_day?.toFixed(2)}</span></p>
                            <div style={{marginTop: '12px'}}>
                                <h4 style={{fontSize: '0.9rem', marginBottom: '12px', color: '#fff'}}>Typical Activities</h4>
                                {Object.entries(profile.baseline.event_type_distribution)
                                    .sort((a,b) => b[1] - a[1])
                                    .slice(0, 5)
                                    .map(([type, freq]) => (
                                    <div key={type} style={{marginBottom: '8px'}}>
                                        <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px', color:'var(--text-muted)'}}>
                                            <span style={{textTransform: 'uppercase'}}>{type}</span>
                                            <span>{(freq * 100).toFixed(1)}%</span>
                                        </div>
                                        <div style={{height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden'}}>
                                            <div style={{width: `${freq * 100}%`, height: '100%', background: 'var(--primary)'}}></div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div style={{color: 'var(--text-muted)'}}>No baseline established.</div>
                    )}
                </div>

                <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-high)' }}>
                        <AlertTriangle size={20} /> 
                        Recent Anomalies
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {profile.recent_anomalies && profile.recent_anomalies.length > 0 ? (
                            profile.recent_anomalies.slice(0, 5).map(anomaly => (
                                <div key={anomaly.anomaly_id} style={{
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    borderLeft: '4px solid #EF4444',
                                    padding: '12px',
                                    borderRadius: '6px'
                                }}>
                                    <div style={{fontWeight: 600, fontSize: '0.9rem'}}>{anomaly.anomaly_type}</div>
                                    <div style={{fontSize: '0.8rem', color: '#fff', marginTop:'4px'}}>{anomaly.description}</div>
                                    <div style={{fontSize: '0.75rem', color: 'var(--text-muted)', marginTop:'8px'}}>
                                        {new Date(anomaly.detected_at).toLocaleString()}
                                    </div>
                                    {anomaly.z_score !== undefined && anomaly.z_score !== null && (
                                        <div style={{fontSize: '0.75rem', color: '#F87171', marginTop: '4px'}}>
                                            Z-Score: {anomaly.z_score.toFixed(2)}
                                        </div>
                                    )}
                                </div>
                            ))
                        ) : (
                            <div style={{color: 'var(--status-low)', padding: '16px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)'}}>
                                User behavior within normal parameters. No recent anomalies.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 style={{ marginBottom: '16px' }}>Recent Activity Feed</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {events.length > 0 ? events.map(event => (
                        <div key={event.event_id} style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '12px',
                            background: 'rgba(255,255,255,0.02)',
                            borderRadius: '6px',
                        }}>
                            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                                <span style={{fontSize: '0.75rem', textTransform: 'uppercase', padding: '4px 8px', background: 'rgba(99, 102, 241, 0.2)', color: '#818CF8', borderRadius: '4px'}}>
                                    {event.event_type}
                                </span>
                                <span style={{fontSize: '0.85rem'}}>{event.resource || event.destination || 'System Action'}</span>
                            </div>
                            <span style={{color: 'var(--text-muted)', fontSize: '0.85rem', minWidth: '150px', textAlign: 'right'}}>
                                {new Date(event.timestamp).toLocaleString()}
                            </span>
                        </div>
                    )) : (
                        <div style={{color: 'var(--text-muted)'}}>No recent events found.</div>
                    )}
                </div>
            </div>
            
        </div>
    );
};

export default UserProfile;
