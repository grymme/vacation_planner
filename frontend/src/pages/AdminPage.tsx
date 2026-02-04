import React, { useState, useEffect } from 'react';
import { adminApi, usersApi, teamsApi, UserResponse } from '../api/vacation';
import './AdminPage.css';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<'users' | 'teams' | 'invite'>('users');
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [functions, setFunctions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Invite form state
  const [inviteForm, setInviteForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    role: 'user',
    company_id: '',
    function_id: '',
    team_ids: [] as string[]
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [usersRes, teamsRes, companiesRes, functionsRes] = await Promise.all([
        adminApi.listUsers(),
        teamsApi.listTeams(),
        adminApi.listCompanies(),
        adminApi.listFunctions()
      ]);
      
      setUsers(usersRes.data);
      setTeams(teamsRes.data);
      setCompanies(companiesRes.data);
      setFunctions(functionsRes.data);
      
      if (companiesRes.data.length > 0 && !inviteForm.company_id) {
        setInviteForm(prev => ({ ...prev, company_id: companiesRes.data[0].id }));
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.inviteUser({
        ...inviteForm,
        team_ids: inviteForm.team_ids
      });
      alert('User invited successfully! They will receive an email with instructions.');
      setInviteForm({
        email: '',
        first_name: '',
        last_name: '',
        role: 'user',
        company_id: inviteForm.company_id,
        function_id: '',
        team_ids: []
      });
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to invite user');
    }
  };

  const handleDeactivate = async (userId: string) => {
    if (!confirm('Are you sure you want to deactivate this user?')) return;
    try {
      await adminApi.deactivateUser(userId);
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to deactivate user');
    }
  };

  if (isLoading) return <div className="loading">Loading...</div>;

  return (
    <div className="page admin-page">
      <h1>Admin Dashboard</h1>
      
      <div className="admin-tabs">
        <button 
          className={activeTab === 'users' ? 'active' : ''} 
          onClick={() => setActiveTab('users')}
        >
          Users
        </button>
        <button 
          className={activeTab === 'teams' ? 'active' : ''} 
          onClick={() => setActiveTab('teams')}
        >
          Teams
        </button>
        <button 
          className={activeTab === 'invite' ? 'active' : ''} 
          onClick={() => setActiveTab('invite')}
        >
          Invite User
        </button>
      </div>
      
      <div className="admin-content">
        {activeTab === 'users' && (
          <div className="users-list">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.first_name} {user.last_name}</td>
                    <td>{user.email}</td>
                    <td><span className={`role-badge role-${user.role}`}>{user.role}</span></td>
                    <td>{user.is_active ? 'Active' : 'Inactive'}</td>
                    <td>
                      {user.is_active && (
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDeactivate(user.id)}
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        
        {activeTab === 'teams' && (
          <div className="teams-list">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Team Name</th>
                  <th>Company</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {teams.map(team => (
                  <tr key={team.id}>
                    <td>{team.name}</td>
                    <td>{companies.find(c => c.id === team.company_id)?.name || 'Unknown'}</td>
                    <td>
                      <button className="btn btn-sm btn-primary">Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        
        {activeTab === 'invite' && (
          <div className="invite-form">
            <h3>Invite New User</h3>
            <form onSubmit={handleInvite}>
              <div className="form-row">
                <div className="form-group">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={inviteForm.first_name}
                    onChange={(e) => setInviteForm({ ...inviteForm, first_name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={inviteForm.last_name}
                    onChange={(e) => setInviteForm({ ...inviteForm, last_name: e.target.value })}
                    required
                  />
                </div>
              </div>
              
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Role</label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                >
                  <option value="user">User</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Company</label>
                <select
                  value={inviteForm.company_id}
                  onChange={(e) => setInviteForm({ ...inviteForm, company_id: e.target.value })}
                  required
                >
                  <option value="">Select Company</option>
                  {companies.map(company => (
                    <option key={company.id} value={company.id}>{company.name}</option>
                  ))}
                </select>
              </div>
              
              <button type="submit" className="btn btn-primary">Send Invite</button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
