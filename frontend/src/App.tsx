import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import './App.css';

// Lazy load components for code splitting
const Login = lazy(() => import('./components/Login'));
const Calendar = lazy(() => import('./components/Calendar'));
const ApprovalsPage = lazy(() => import('./pages/ApprovalsPage'));
const TeamsPage = lazy(() => import('./pages/TeamsPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));

// Loading fallback component
function Loading() {
  return (
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p>Loading...</p>
    </div>
  );
}

// Protected Route wrapper
function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <Loading />;
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
    return <Loading />;
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
        <Suspense fallback={<Loading />}>
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
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
