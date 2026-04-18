import React, { useEffect, useState } from 'react';
import { Shield, Activity, Users, AlertTriangle } from 'lucide-react';
import { getDashboardOverview, getAnomalyTrends, getTopRisks } from '../services/api';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const StatCard = ({ title, value, icon: Icon, colorClass }) => (
  <div className="glass-panel stat-card animate-fade-in text-white">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span className="stat-card-title">{title}</span>
      <Icon size={20} className={colorClass} />
    </div>
    <span className="stat-card-value">{value}</span>
  </div>
);

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);
  const [topRisks, setTopRisks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [overview, trendsData, risksData] = await Promise.all([
          getDashboardOverview(),
          getAnomalyTrends(7),
          getTopRisks(5)
        ]);
        if (overview) setStats(overview);
        if (trendsData && trendsData.trends) setTrends(trendsData.trends);
        if (risksData && risksData.users) setTopRisks(risksData.users);
      } catch (err) {
        console.error("Failed to fetch dashboard data.");
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  if (loading || !stats) {
    return <div className="animate-fade-in" style={{color: '#94A3B8'}}>Loading dashboard...</div>;
  }

  const chartData = {
    labels: trends.map(t => t.date),
    datasets: [
      {
        fill: true,
        label: 'Anomalies',
        data: trends.map(t => t.anomaly_count),
        borderColor: '#6366F1',
        backgroundColor: 'rgba(99, 102, 241, 0.2)',
        tension: 0.4,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false }
    },
    scales: {
      y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
      x: { grid: { color: 'rgba(255,255,255,0.05)' } }
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Dashboard Overview</h1>
        <p style={{ color: 'var(--text-muted)' }}>Real-time behavioral security metrics across the organization.</p>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '24px' }}>
        <StatCard title="Active Users" value={stats.active_users} icon={Users} colorClass="text-[#06B6D4]" />
        <StatCard title="Total Events (24h)" value={stats.events_last_24h} icon={Activity} colorClass="text-[#6366F1]" />
        <StatCard title="Anomalies (24h)" value={stats.anomalies_last_24h} icon={AlertTriangle} colorClass="text-[#F97316]" />
        <StatCard title="Open Alerts" value={stats.open_alerts} icon={Shield} colorClass="text-[#EF4444]" />
      </div>

      {/* Main Charts & Lists */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}>Anomaly Trends (7 Days)</h3>
          <div style={{ height: '300px' }}>
            <Line options={chartOptions} data={chartData} />
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}>Top Risks</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {topRisks.map(user => (
              <div key={user.user_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{user.user_id}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{user.anomaly_count} Anomalies</div>
                </div>
                <span className={`badge badge-${user.risk_level.toLowerCase()}`}>
                  {user.risk_level}
                </span>
              </div>
            ))}
            {topRisks.length === 0 && <span style={{color: 'var(--text-muted)'}}>No high-risk users found.</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
