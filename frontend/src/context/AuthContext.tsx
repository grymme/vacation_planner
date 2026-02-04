import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { UserResponse } from '../api/vacation';

interface AuthContextType {
  user: UserResponse | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  setPassword: (token: string, password: string, confirmPassword: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      setAccessToken(token);
      fetchUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  // Set up axios interceptor for token refresh
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401 && error.config.url !== '/auth/login') {
          try {
            await refreshToken();
            return axios(error.config);
          } catch {
            logout();
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`);
      setUser(response.data);
    } catch {
      localStorage.removeItem('accessToken');
      setAccessToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });
    const { access_token } = response.data;
    localStorage.setItem('accessToken', access_token);
    setAccessToken(access_token);
    await fetchUser();
  };

  const logout = async () => {
    try {
      await axios.post(`${API_URL}/auth/logout`);
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem('accessToken');
    setAccessToken(null);
    setUser(null);
  };

  const refreshToken = async () => {
    const response = await axios.post(`${API_URL}/auth/refresh`);
    const { access_token } = response.data;
    localStorage.setItem('accessToken', access_token);
    setAccessToken(access_token);
  };

  const setPassword = async (token: string, password: string, confirmPassword: string) => {
    await axios.post(`${API_URL}/auth/set-password`, { token, password, confirm_password: confirmPassword });
  };

  const requestPasswordReset = async (email: string) => {
    await axios.post(`${API_URL}/auth/password-reset-request`, { email });
  };

  return (
    <AuthContext.Provider value={{ user, accessToken, isLoading, login, logout, refreshToken, setPassword, requestPasswordReset }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
