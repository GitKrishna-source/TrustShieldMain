import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import '../index.css';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError('Invalid email or password');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-container">
      <div className="gradient-blob blob-1"></div>
      <div className="gradient-blob blob-2"></div>
      
      <div className="glass-panel login-panel animate-fade-in">
        <div className="login-header">
          <Shield size={56} color="#6366F1" />
          <h1>TrustShield</h1>
          <p>Behavioral Baseline System</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Email Address</label>
            <input 
              type="text" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@corp.com"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          <button type="submit" className="login-button" disabled={isSubmitting}>
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div className="demo-credentials">
          <p style={{marginBottom: '8px', color: 'var(--text-muted)'}}>Demo Credentials for Hackathon:</p>
          <div style={{background: 'rgba(0,0,0,0.2)', padding:'12px', borderRadius: '8px'}}>
            <p><strong>Admin:</strong> admin@corp.com / admin123</p>
            <p><strong>User:</strong> alice.chen@corp.com / password123</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
