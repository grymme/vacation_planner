import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login, setPassword: setPasswordApi, requestPasswordReset } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inviteToken = searchParams.get('token');
  const resetToken = searchParams.get('reset_token');

  // If invite/reset token present, show password set/reset form
  if (inviteToken || resetToken) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h2>{inviteToken ? 'Set Your Password' : 'Reset Password'}</h2>
          <p className="login-subtitle">
            {inviteToken ? 'Welcome! Please set your password to activate your account.' : 'Enter your new password.'}
          </p>
          
          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          
          <form onSubmit={async (e) => {
            e.preventDefault();
            setError('');
            setIsLoading(true);
            
            try {
              if (password !== confirmPassword) {
                throw new Error('Passwords do not match');
              }
              if (password.length < 8) {
                throw new Error('Password must be at least 8 characters');
              }
              
              await setPasswordApi(inviteToken || resetToken!, password, confirmPassword);
              setSuccess('Password set successfully! Redirecting to login...');
              setTimeout(() => navigate('/login'), 2000);
            } catch (err: any) {
              setError(err.response?.data?.detail || err.message || 'Failed to set password');
            } finally {
              setIsLoading(false);
            }
          }}>
            <div className="form-group">
              <label htmlFor="password">New Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            
            <button type="submit" disabled={isLoading} className="btn btn-primary">
              {isLoading ? 'Setting password...' : 'Set Password'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>{isLogin ? 'Sign In' : 'Reset Password'}</h2>
        <p className="login-subtitle">
          {isLogin ? 'Enter your credentials to access your account' : 'Enter your email to receive a password reset link'}
        </p>
        
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}
        
        <form onSubmit={async (e) => {
          e.preventDefault();
          setError('');
          setIsLoading(true);
          
          try {
            if (isLogin) {
              await login(email, password);
              navigate('/');
            } else {
              await requestPasswordReset(email);
              setSuccess('If an account exists with that email, a reset link has been sent.');
              setIsLogin(true);
            }
          } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Authentication failed');
          } finally {
            setIsLoading(false);
          }
        }}>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          {isLogin && (
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          )}
          
          <button type="submit" disabled={isLoading} className="btn btn-primary">
            {isLoading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Send Reset Link')}
          </button>
        </form>
        
        <div className="login-links">
          {isLogin ? (
            <>
              <button className="link-btn" onClick={() => setIsLogin(false)}>
                Forgot your password?
              </button>
              <p>
                New user? Contact your administrator for an invite.
              </p>
            </>
          ) : (
            <button className="link-btn" onClick={() => setIsLogin(true)}>
              Back to login
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
