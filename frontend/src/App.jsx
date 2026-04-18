import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { ShieldAlert, Users, LayoutDashboard, Shield } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Alerts from './pages/Alerts';
import UsersList from './pages/UsersList';
import './index.css';

const Sidebar = () => (
  <div className="sidebar">
    <div className="sidebar-logo">
      <Shield size={28} color="#6366F1" />
      <span>TrustShield</span>
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
    </nav>
  </div>
);

const App = () => {
  return (
    <Router>
      <div className="app-container">
        <div className="gradient-blob blob-1"></div>
        <div className="gradient-blob blob-2"></div>
        
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/users" element={<UsersList />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
