import React, { useState, useEffect } from 'react';
import { 
  adminApi, 
  usersApi, 
  teamsApi, 
  UserResponse,
  vacationPeriodsApi,
  allocationsApi,
  VacationPeriod,
  VacationAllocation
} from '../api/vacation';
import { VacationPeriodSelector } from '../components/VacationPeriodSelector';
import './AdminPage.css';

type AdminTab = 'users' | 'teams' | 'invite' | 'periods' | 'allocations';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [functions, setFunctions] = useState<any[]>([]);
  const [periods, setPeriods] = useState<VacationPeriod[]>([]);
  const [allocations, setAllocations] = useState<VacationAllocation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Period selector state
  const [selectedPeriodId, setSelectedPeriodId] = useState<string | null>(null);
  
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

  // Period form state
  const [periodForm, setPeriodForm] = useState({
    name: '',
    start_date: '',
    end_date: '',
    company_id: '',
    is_default: false
  });

  // Allocation form state
  const [allocationForm, setAllocationForm] = useState({
    user_id: '',
    vacation_period_id: '',
    total_days: 0,
    carried_over_days: 0
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [usersRes, teamsRes, companiesRes, functionsRes, periodsRes] = await Promise.all([
        adminApi.listUsers(),
        teamsApi.listTeams(),
        adminApi.listCompanies(),
        adminApi.listFunctions(),
        vacationPeriodsApi.getVacationPeriods()
      ]);
      
      setUsers(usersRes.data);
      setTeams(teamsRes.data);
      setCompanies(companiesRes.data);
      setFunctions(functionsRes.data);
      setPeriods(periodsRes);
      
      if (companiesRes.data.length > 0 && !inviteForm.company_id) {
        setInviteForm(prev => ({ ...prev, company_id: companiesRes.data[0].id }));
        setPeriodForm(prev => ({ ...prev, company_id: companiesRes.data[0].id }));
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAllocations = async () => {
    if (!selectedPeriodId) return;
    try {
      const data = await allocationsApi.getAllocations({ vacation_period_id: selectedPeriodId });
      setAllocations(data);
    } catch (error) {
      console.error('Failed to fetch allocations:', error);
    }
  };

  useEffect(() => {
    if (selectedPeriodId) {
      fetchAllocations();
    }
  }, [selectedPeriodId]);

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

  const handleCreatePeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await vacationPeriodsApi.createVacationPeriod(periodForm);
      alert('Vacation period created successfully!');
      setPeriodForm({
        name: '',
        start_date: '',
        end_date: '',
        company_id: periodForm.company_id,
        is_default: false
      });
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create period');
    }
  };

  const handleDeletePeriod = async (periodId: string) => {
    if (!confirm('Are you sure you want to delete this period?')) return;
    try {
      await vacationPeriodsApi.deleteVacationPeriod(periodId);
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete period');
    }
  };

  const handleCreateAllocation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await allocationsApi.createAllocation(allocationForm);
      alert('Allocation created successfully!');
      setAllocationForm({
        user_id: '',
        vacation_period_id: selectedPeriodId || '',
        total_days: 0,
        carried_over_days: 0
      });
      fetchAllocations();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create allocation');
    }
  };

  const handleDeleteAllocation = async (allocationId: string) => {
    if (!confirm('Are you sure you want to delete this allocation?')) return;
    try {
      await allocationsApi.deleteAllocation(allocationId);
      fetchAllocations();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete allocation');
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
        <button 
          className={activeTab === 'periods' ? 'active' : ''} 
          onClick={() => setActiveTab('periods')}
        >
          Vacation Periods
        </button>
        <button 
          className={activeTab === 'allocations' ? 'active' : ''} 
          onClick={() => setActiveTab('allocations')}
        >
          Allocations
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
        
        {activeTab === 'periods' && (
          <div className="periods-section">
            <div className="periods-list">
              <h3>Vacation Periods</h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Default</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {periods.map(period => (
                    <tr key={period.id}>
                      <td>{period.name}</td>
                      <td>{period.start_date}</td>
                      <td>{period.end_date}</td>
                      <td>{period.is_default ? 'Yes' : 'No'}</td>
                      <td>
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDeletePeriod(period.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div className="period-form">
              <h3>Create Vacation Period</h3>
              <form onSubmit={handleCreatePeriod}>
                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    value={periodForm.name}
                    onChange={(e) => setPeriodForm({ ...periodForm, name: e.target.value })}
                    placeholder="e.g., 2024 Vacation Year"
                    required
                  />
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Start Date</label>
                    <input
                      type="date"
                      value={periodForm.start_date}
                      onChange={(e) => setPeriodForm({ ...periodForm, start_date: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>End Date</label>
                    <input
                      type="date"
                      value={periodForm.end_date}
                      onChange={(e) => setPeriodForm({ ...periodForm, end_date: e.target.value })}
                      required
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>Company</label>
                  <select
                    value={periodForm.company_id}
                    onChange={(e) => setPeriodForm({ ...periodForm, company_id: e.target.value })}
                    required
                  >
                    <option value="">Select Company</option>
                    {companies.map(company => (
                      <option key={company.id} value={company.id}>{company.name}</option>
                    ))}
                  </select>
                </div>
                
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={periodForm.is_default}
                      onChange={(e) => setPeriodForm({ ...periodForm, is_default: e.target.checked })}
                    />
                    Set as default period
                  </label>
                </div>
                
                <button type="submit" className="btn btn-primary">Create Period</button>
              </form>
            </div>
          </div>
        )}
        
        {activeTab === 'allocations' && (
          <div className="allocations-section">
            <VacationPeriodSelector
              selectedPeriodId={selectedPeriodId}
              onChange={setSelectedPeriodId}
            />
            
            {selectedPeriodId && (
              <>
                <div className="allocations-list">
                  <h3>Allocations for Selected Period</h3>
                  {allocations.length === 0 ? (
                    <p className="empty-message">No allocations found for this period.</p>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>User</th>
                          <th>Total Days</th>
                          <th>Carried Over</th>
                          <th>Days Used</th>
                          <th>Remaining</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allocations.map(allocation => {
                          const user = users.find(u => u.id === allocation.user_id);
                          return (
                            <tr key={allocation.id}>
                              <td>{user ? `${user.first_name} ${user.last_name}` : allocation.user_id}</td>
                              <td>{allocation.total_days}</td>
                              <td>{allocation.carried_over_days}</td>
                              <td>{allocation.days_used}</td>
                              <td>{allocation.total_days + allocation.carried_over_days - allocation.days_used}</td>
                              <td>
                                <button 
                                  className="btn btn-sm btn-danger"
                                  onClick={() => handleDeleteAllocation(allocation.id)}
                                >
                                  Delete
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
                
                <div className="allocation-form">
                  <h3>Create Allocation</h3>
                  <form onSubmit={handleCreateAllocation}>
                    <div className="form-group">
                      <label>User</label>
                      <select
                        value={allocationForm.user_id}
                        onChange={(e) => setAllocationForm({ ...allocationForm, user_id: e.target.value })}
                        required
                      >
                        <option value="">Select User</option>
                        {users.map(user => (
                          <option key={user.id} value={user.id}>
                            {user.first_name} {user.last_name}
                          </option>
                        ))}
                      </select>
                    </div>
                    
                    <div className="form-group">
                      <label>Vacation Period</label>
                      <select
                        value={allocationForm.vacation_period_id}
                        onChange={(e) => setAllocationForm({ ...allocationForm, vacation_period_id: e.target.value })}
                        required
                      >
                        <option value="">Select Period</option>
                        {periods.map(period => (
                          <option key={period.id} value={period.id}>{period.name}</option>
                        ))}
                      </select>
                    </div>
                    
                    <div className="form-row">
                      <div className="form-group">
                        <label>Total Days</label>
                        <input
                          type="number"
                          min="0"
                          value={allocationForm.total_days}
                          onChange={(e) => setAllocationForm({ ...allocationForm, total_days: parseInt(e.target.value) || 0 })}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Carried Over Days</label>
                        <input
                          type="number"
                          min="0"
                          value={allocationForm.carried_over_days}
                          onChange={(e) => setAllocationForm({ ...allocationForm, carried_over_days: parseInt(e.target.value) || 0 })}
                        />
                      </div>
                    </div>
                    
                    <button type="submit" className="btn btn-primary">Create Allocation</button>
                  </form>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
