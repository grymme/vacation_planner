import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { VacationBalance } from './VacationBalance';
import './Header.css';

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  if (!user) return null;

  return (
    <header className="app-header">
      <div className="header-content">
        <div className="logo">
          <Link to="/">🏖️ Vacation Planner</Link>
        </div>
        
        <nav className="main-nav">
          <Link to="/" className={isActive('/') ? 'active' : ''}>
            Calendar
          </Link>
          
          {(user.role === 'manager' || user.role === 'admin') && (
            <Link to="/approvals" className={isActive('/approvals') ? 'active' : ''}>
              Approvals
            </Link>
          )}
          
          {(user.role === 'manager' || user.role === 'admin') && (
            <Link to="/teams" className={isActive('/teams') ? 'active' : ''}>
              Teams
            </Link>
          )}
          
          {user.role === 'admin' && (
            <Link to="/admin" className={isActive('/admin') ? 'active' : ''}>
              Admin
            </Link>
          )}
        </nav>
        
        <div className="user-menu">
          <div className="header-balance">
            <VacationBalance />
          </div>
          <div className="user-info">
            <span className="user-name">{user.first_name} {user.last_name}</span>
            <span className={`role-badge role-${user.role}`}>{user.role}</span>
          </div>
          <button onClick={handleLogout} className="btn btn-outline">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
