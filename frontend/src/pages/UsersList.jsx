import React, { useEffect, useState } from 'react';
import { getUsers } from '../services/api';

const UsersList = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true);
      const data = await getUsers(100, 0);
      if (data && data.users) {
        setUsers(data.users);
      }
      setLoading(false);
    };
    fetchUsers();
  }, []);

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>User Directory</h1>
        <p style={{ color: 'var(--text-muted)' }}>Employees and their clearance levels.</p>
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
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {users.length > 0 ? users.map((user) => (
                <tr key={user.user_id}>
                  <td style={{ fontWeight: 600 }}>{user.user_id}</td>
                  <td>{user.username}</td>
                  <td>{user.department}</td>
                  <td>{user.role}</td>
                  <td>Level {user.clearance_level}</td>
                  <td>
                    <span className="badge" style={{ 
                      background: user.is_active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: user.is_active ? '#10B981' : '#EF4444'
                    }}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
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
