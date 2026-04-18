import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { ShieldAlert, Users, LayoutDashboard, Shield, Activity, LogOut } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import UsersList from './pages/UsersList';
import Login from './pages/Login';
import UserProfile from './pages/UserProfile';
import Timeline from './pages/Timeline';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import './index.css';

const Sidebar = () => {
  const { user, logout } = useAuth();
  
  if (!user) return null;

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <Shield size={28} color="#6366F1" />
        <span>TrustShield</span>
      </div>
      
      <div style={{marginBottom: '32px', padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)'}}>
        <div style={{fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px'}}>Current Session</div>
        <div style={{fontWeight: 600, color: '#fff', fontSize: '0.95rem'}}>{user.username}</div>
        <div style={{fontSize: '0.8rem', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px'}}>
            <span style={{width: '6px', height: '6px', background: '#06B6D4', borderRadius: '50%', display: 'inline-block'}}></span>
            {user.role}
        </div>
      </div>

      <nav className="nav-links">
        <li className="nav-item">
          <NavLink to="/" end className={({isActive}) => isActive ? "active" : ""}>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/alerts" className={({isActive}) => isActive ? "active" : ""}>
            <ShieldAlert size={20} />
            <span>Alerts</span>
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/users" className={({isActive}) => isActive ? "active" : ""}>
            <Users size={20} />
            <span>Users</span>
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink to="/timeline" className={({isActive}) => isActive ? "active" : ""}>
            <Activity size={20} />
            <span>Timeline</span>
          </NavLink>
        </li>
      </nav>

      <div style={{marginTop: 'auto'}}>
        <button onClick={logout} className="logout-button" style={{
            display: 'flex', alignItems: 'center', gap: '12px', width: '100%', 
            padding: '12px 16px', background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444', 
            border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: 500,
            transition: 'background 0.2s'
        }}>
            <LogOut size={18} />
            <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
};

const AppContent = () => {
    const { user } = useAuth();
    
    return (
        <div className="app-container">
          <div className="gradient-blob blob-1"></div>
          <div className="gradient-blob blob-2"></div>
          
          {user && <Sidebar />}
          
          <main className={user ? "main-content" : "full-content"}>
            <Routes>
              <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
              
              <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
              <Route path="/users" element={<ProtectedRoute><UsersList /></ProtectedRoute>} />
              <Route path="/users/:id" element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />
              <Route path="/timeline" element={<ProtectedRoute><Timeline /></ProtectedRoute>} />
              
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
    );
};

const App = () => {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
};

export default App;
