import React, { useState, useEffect, useCallback } from 'react';
import { AuthContext } from './AuthContext';
import api from '../services/api';
import { AUTH_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../constants/auth';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const checkAuthStatus = useCallback(async () => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      try {
        const response = await api.get('/auth/profile/');
        setUser(response.data);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        setUser(null);
        setIsAuthenticated(false);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  const login = async (email, password) => {
    try {
      const response = await api.post('/auth/token/', { email, password });
      const { access, refresh, user } = response.data;

      localStorage.setItem(AUTH_TOKEN_KEY, access);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh);

      setUser(user);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await api.post('/auth/register/', userData);
      const { access, refresh, user } = response.data;

      localStorage.setItem(AUTH_TOKEN_KEY, access);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh);

      setUser(user);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Registration failed'
      };
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout/', {
        refresh_token: localStorage.getItem(REFRESH_TOKEN_KEY)
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const hasRole = (roleName) => {
    return user?.roles?.some(role => role.name === roleName) || false;
  };

  const hasPermission = (permission) => {
    if (!user) return false;

    // Check role-based permissions
    for (const role of user.roles || []) {
      if (role.permissions?.some(perm => perm.codename === permission)) {
        return true;
      }
    }

    return false;
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    hasRole,
    hasPermission,
    checkAuthStatus,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
