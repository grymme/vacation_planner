import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './components/Login';
import Calendar from './components/Calendar';
import Header from './components/Header';
import ApprovalsPage from './pages/ApprovalsPage';
import TeamsPage from './pages/TeamsPage';
import AdminPage from './pages/AdminPage';
import './App.css';

// Protected Route wrapper
function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  
  return <>{children}</>;
}

// Layout with Header
function AppLayout() {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }
  
  if (!user) {
    return <Outlet />;
  }
  
  return (
    <div className="app-layout">
      <Header />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/set-password" element={<Login />} />
          <Route path="/reset-password" element={<Login />} />
          
          <Route element={<AppLayout />}>
            <Route path="/" element={
              <ProtectedRoute>
                <Calendar viewMode="user" />
              </ProtectedRoute>
            } />
            
            <Route path="/approvals" element={
              <ProtectedRoute roles={['manager', 'admin']}>
                <ApprovalsPage />
              </ProtectedRoute>
            } />
            
            <Route path="/teams" element={
              <ProtectedRoute roles={['manager', 'admin']}>
                <TeamsPage />
              </ProtectedRoute>
            } />
            
            <Route path="/admin" element={
              <ProtectedRoute roles={['admin']}>
                <AdminPage />
              </ProtectedRoute>
            } />
          </Route>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
