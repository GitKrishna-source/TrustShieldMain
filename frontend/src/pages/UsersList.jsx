import React, { useEffect, useState } from 'react';
import { getUsers } from '../services/api';
import { Link } from 'react-router-dom';
import { User, Shield } from 'lucide-react';

const UsersList = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true);
      try {
        const data = await getUsers(100, 0);
        if (data && data.users) {
            // Sort by user_id for deterministic view, or you could do risk score if available here
            setUsers(data.users.sort((a,b) => a.user_id.localeCompare(b.user_id)));
        }
      } catch (err) {
        console.error("Error fetching users:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>User Directory</h1>
        <p style={{ color: 'var(--text-muted)' }}>Employees and access levels.</p>
      </div>

      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '24px', color: 'var(--text-muted)' }}>Loading users...</div>
        ) : (
          <table className="glass-table">
            <thead>
              <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>Department</th>
                <th>Role</th>
                <th>Clearance</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {users.length > 0 ? users.map((user) => (
                <tr key={user.user_id}>
                  <td style={{ fontWeight: 600 }}>{user.user_id}</td>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                        <User size={16} color="var(--text-muted)" />
                        {user.username}
                    </div>
                  </td>
                  <td style={{textTransform: 'capitalize'}}>{user.department}</td>
                  <td style={{textTransform: 'capitalize'}}>{user.role.replace('_', ' ')}</td>
                  <td>
                    <div style={{display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-cyan)'}}>
                        <Shield size={16} />
                        Level {user.clearance_level}
                    </div>
                  </td>
                  <td>
                    <Link to={`/users/${user.user_id}`} style={{
                        background: 'rgba(99, 102, 241, 0.1)', 
                        padding: '6px 16px', 
                        borderRadius: '6px',
                        color: '#818CF8',
                        textDecoration: 'none',
                        fontSize: '0.85rem',
                        fontWeight: 500,
                        border: '1px solid rgba(99, 102, 241, 0.2)'
                    }}>
                        View Profile
                    </Link>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '24px' }}>No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default UsersList;
