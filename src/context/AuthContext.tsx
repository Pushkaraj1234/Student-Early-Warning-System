/**
 * Student Early Warning System (SEWS)
 * Authentication & Role-Based Access Control Context
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types.js';
import { api } from '../services/api.js';

interface AuthContextType {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => Promise<void>;
  quickLogin: (preset: 'ADMIN' | 'FACULTY' | 'STUDENT_RISK' | 'STUDENT_IMPROVED' | 'STUDENT_TOP') => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const PRESET_ACCOUNTS = {
  ADMIN: { email: 'admin@sews.edu', pass: 'Admin@123', label: 'Admin (Dean)', desc: 'Full Institutional Access' },
  FACULTY: { email: 'faculty.sharma@sews.edu', pass: 'Faculty@123', label: 'Faculty Mentor (CSE)', desc: 'Class Dashboard & Interventions' },
  STUDENT_RISK: { email: 'stu1024@sews.edu', pass: 'Student@123', label: 'Student (Aarav Verma - Critical)', desc: 'Active Intervention Plan View' },
  STUDENT_IMPROVED: { email: 'stu1012@sews.edu', pass: 'Student@123', label: 'Student (Rohan Deshmukh - Improved)', desc: 'Post-Intervention Progress View' },
  STUDENT_TOP: { email: 'stu1001@sews.edu', pass: 'Student@123', label: 'Student (Anika Gupta - High Performer)', desc: 'Stable Academic View' }
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('sews_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function verifyUser() {
      const storedToken = localStorage.getItem('sews_token');
      if (!storedToken) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      try {
        const { user: currentUser } = await api.getMe();
        setUser(currentUser);
      } catch (err) {
        console.warn('Session verification failed, logging out:', err);
        localStorage.removeItem('sews_token');
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    verifyUser();

    const handleAuthChange = () => {
      setToken(localStorage.getItem('sews_token'));
      if (!localStorage.getItem('sews_token')) {
        setUser(null);
      }
    };
    window.addEventListener('sews_auth_change', handleAuthChange);
    return () => window.removeEventListener('sews_auth_change', handleAuthChange);
  }, []);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const data = await api.login(email, pass);
      localStorage.setItem('sews_token', data.token);
      setToken(data.token);
      setUser(data.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.logout();
    } finally {
      setUser(null);
      setToken(null);
      setIsLoading(false);
    }
  };

  const quickLogin = async (presetKey: keyof typeof PRESET_ACCOUNTS) => {
    const preset = PRESET_ACCOUNTS[presetKey];
    if (preset) {
      await login(preset.email, preset.pass);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role || null,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        quickLogin
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
