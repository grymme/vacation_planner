import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
});

// Add auth header to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface VacationRequest {
  id: string;
  user_id: string;
  user: UserResponse;
  team_id: string | null;
  start_date: string;
  end_date: string;
  vacation_type: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  reason: string | null;
  approver_id: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'manager' | 'user';
  company_id: string;
  function_id: string | null;
  is_active: boolean;
  created_at: string;
  teams?: TeamResponse[];
  function?: FunctionResponse;
}

export interface TeamResponse {
  id: string;
  company_id: string;
  name: string;
  created_at: string;
}

export interface FunctionResponse {
  id: string;
  company_id: string;
  name: string;
  created_at: string;
}

export interface VacationCreate {
  start_date: string;
  end_date: string;
  vacation_type?: string;
  reason?: string;
  team_id?: string;
}

export interface VacationAction {
  action: 'approve' | 'reject';
  comment?: string;
}

// Vacation Requests API
export const vacationApi = {
  getMyRequests: (startDate?: string, endDate?: string, status?: string) =>
    api.get<VacationRequest[]>('/vacation-requests/', {
      params: { start_date: startDate, end_date: endDate, status }
    }),
  
  createRequest: (data: VacationCreate) =>
    api.post<VacationRequest>('/vacation-requests/', data),
  
  getRequest: (id: string) =>
    api.get<VacationRequest>(`/vacation-requests/${id}`),
  
  cancelRequest: (id: string) =>
    api.delete(`/vacation-requests/${id}`),
  
  getPendingRequests: (teamId?: string) =>
    api.get<VacationRequest[]>('/vacation-requests/pending', {
      params: { team_id: teamId }
    }),
  
  approveRequest: (id: string, action: VacationAction) =>
    api.post<VacationRequest>(`/vacation-requests/${id}/approve`, action),
  
  modifyRequest: (id: string, data: Partial<VacationCreate>) =>
    api.put<VacationRequest>(`/vacation-requests/${id}/modify`, data),
};

// Users API
export const usersApi = {
  getCurrentUser: () => api.get<UserResponse>('/users/me'),
  updateProfile: (data: Partial<UserResponse>) => api.put<UserResponse>('/users/me', data),
  listUsers: (companyId?: string, functionId?: string, role?: string) =>
    api.get<UserResponse[]>('/users/', {
      params: { company_id: companyId, function_id: functionId, role }
    }),
  getUser: (id: string) => api.get<UserResponse>(`/users/${id}`),
};

// Teams API
export const teamsApi = {
  listTeams: (companyId?: string) =>
    api.get<TeamResponse[]>('/admin/teams', { params: { company_id: companyId } }),
  createTeam: (data: { company_id: string; name: string }) =>
    api.post<TeamResponse>('/admin/teams', data),
  getManagedTeams: () => api.get<TeamResponse[]>('/manager/teams'),
  getTeamMembers: (teamId: string) =>
    api.get<UserResponse[]>(`/manager/team-members/${teamId}`),
  addTeamMember: (teamId: string, userId: string) =>
    api.post(`/admin/teams/${teamId}/members/${userId}`),
  removeTeamMember: (teamId: string, userId: string) =>
    api.delete(`/admin/teams/${teamId}/members/${userId}`),
};

// Admin API
export const adminApi = {
  listCompanies: () => api.get<any[]>('/admin/companies'),
  createCompany: (name: string) => api.post<any>('/admin/companies', { name }),
  listFunctions: (companyId?: string) =>
    api.get<FunctionResponse[]>('/admin/functions', { params: { company_id: companyId } }),
  createFunction: (data: { company_id: string; name: string }) =>
    api.post<FunctionResponse>('/admin/functions', data),
  listUsers: (companyId?: string, functionId?: string, role?: string) =>
    api.get<UserResponse[]>('/admin/users', {
      params: { company_id: companyId, function_id: functionId, role }
    }),
  inviteUser: (data: {
    email: string;
    first_name: string;
    last_name: string;
    role: string;
    company_id: string;
    function_id?: string;
    team_ids?: string[];
  }) => api.post<{ invite_token: string; invite_link: string }>('/admin/invite', data),
  deactivateUser: (userId: string) =>
    api.post(`/admin/users/${userId}/deactivate`),
  resetUserPassword: (userId: string) =>
    api.post(`/admin/users/${userId}/reset-password`),
  assignManager: (teamId: string, userId: string) =>
    api.post(`/admin/teams/${teamId}/managers/${userId}`),
  removeManager: (teamId: string, userId: string) =>
    api.delete(`/admin/teams/${teamId}/managers/${userId}`),
  getAuditLogs: (limit?: number, offset?: number) =>
    api.get<any[]>('/admin/audit-logs', { params: { limit, offset } }),
};

export default api;

// Export API
export const exportApi = {
  exportCSV: (params: {
    start_date?: string;
    end_date?: string;
    status?: string;
    team_id?: string;
    user_id?: string;
  }) => {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.status) queryParams.append('status', params.status);
    if (params.team_id) queryParams.append('team_id', params.team_id);
    if (params.user_id) queryParams.append('user_id', params.user_id);
    
    const token = localStorage.getItem('accessToken');
    const url = `${API_URL}/export/csv?${queryParams.toString()}`;
    
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('Authorization', `Bearer ${token}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
  
  exportXLSX: (params: {
    start_date?: string;
    end_date?: string;
    status?: string;
    team_id?: string;
    user_id?: string;
  }) => {
    const queryParams = new URLSearchParams();
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.status) queryParams.append('status', params.status);
    if (params.team_id) queryParams.append('team_id', params.team_id);
    if (params.user_id) queryParams.append('user_id', params.user_id);
    
    const token = localStorage.getItem('accessToken');
    const url = `${API_URL}/export/xlsx?${queryParams.toString()}`;
    
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('Authorization', `Bearer ${token}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
  
  exportPNG: (elementId: string, filename: string) => {
    return import('html-to-image').then(htmlToImage => {
      const element = document.getElementById(elementId);
      if (!element) throw new Error('Element not found');
      
      return htmlToImage.toPng(element, {
        backgroundColor: '#ffffff',
        pixelRatio: 2
      }).then((dataUrl: string) => {
        const link = document.createElement('a');
        link.download = `${filename}_${new Date().toISOString().split('T')[0]}.png`;
        link.href = dataUrl;
        link.click();
      });
    });
  }
};
