import React, { useState } from 'react';
import { useAuth, PRESET_ACCOUNTS } from '../../context/AuthContext.js';
import { GraduationCap, Lock, Mail, ArrowRight, ShieldCheck, Sparkles, User, AlertCircle } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const { login, quickLogin, isLoading } = useAuth();
  const [email, setEmail] = useState<string>('admin@sews.edu');
  const [password, setPassword] = useState<string>('Admin@123');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      onLoginSuccess?.();
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify your credentials.');
    }
  };

  const handleQuickPick = async (presetKey: keyof typeof PRESET_ACCOUNTS) => {
    setError(null);
    try {
      await quickLogin(presetKey);
      onLoginSuccess?.();
    } catch (err: any) {
      setError(err.message || 'Quick login failed');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 text-white shadow-md mb-3">
          <GraduationCap className="w-8 h-8" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          SEWS Academic Portal
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Student Early Warning, Explainable Risk Prediction & Mentorship System
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 sm:rounded-2xl sm:px-10 border border-slate-200/80">
          {error && (
            <div className="mb-5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Institutional Email
              </label>
              <div className="relative rounded-lg shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="login-email-input"
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-900"
                  placeholder="name@sews.edu"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative rounded-lg shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="login-password-input"
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-900"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              id="submit-login-btn"
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-xs text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Signing in...' : 'Sign in to Dashboard'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Persona Picker for Effortless Evaluation */}
          <div className="mt-8 pt-6 border-t border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                1-Click Evaluator Personas
              </span>
              <span className="text-[11px] text-slate-500">Instant Demo Login</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                type="button"
                id="quick-login-admin"
                onClick={() => handleQuickPick('ADMIN')}
                className="p-2.5 text-left rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all flex flex-col group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-900">
                    Dean / Admin
                  </span>
                  <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                    ADMIN
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 mt-0.5">
                  Institutional stats, ML model evaluation, CSV upload
                </span>
              </button>

              <button
                type="button"
                id="quick-login-faculty"
                onClick={() => handleQuickPick('FACULTY')}
                className="p-2.5 text-left rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all flex flex-col group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-900">
                    Dr. Rajesh Sharma
                  </span>
                  <span className="text-[10px] font-mono bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded">
                    FACULTY
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 mt-0.5">
                  Assigned cohort, SHAP analysis & intervention plans
                </span>
              </button>

              <button
                type="button"
                id="quick-login-student-risk"
                onClick={() => handleQuickPick('STUDENT_RISK')}
                className="p-2.5 text-left rounded-xl border border-rose-200/80 bg-rose-50/20 hover:bg-rose-50/50 transition-all flex flex-col group sm:col-span-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-rose-900 group-hover:text-rose-950">
                    Aarav Verma (Student STU1024)
                  </span>
                  <span className="text-[10px] font-mono bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded">
                    CRITICAL RISK DEMO
                  </span>
                </div>
                <span className="text-[11px] text-slate-600 mt-0.5">
                  Experience supportive, non-stigmatizing student growth view with assigned remedial plan
                </span>
              </button>

              <button
                type="button"
                id="quick-login-student-improved"
                onClick={() => handleQuickPick('STUDENT_IMPROVED')}
                className="p-2.5 text-left rounded-xl border border-emerald-200/80 bg-emerald-50/20 hover:bg-emerald-50/50 transition-all flex flex-col group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-900">
                    Rohan Deshmukh (STU1012)
                  </span>
                  <span className="text-[10px] font-mono bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">
                    IMPROVED
                  </span>
                </div>
                <span className="text-[11px] text-slate-600 mt-0.5">
                  Dynamic re-evaluation & post-intervention recovery
                </span>
              </button>

              <button
                type="button"
                id="quick-login-student-top"
                onClick={() => handleQuickPick('STUDENT_TOP')}
                className="p-2.5 text-left rounded-xl border border-slate-200 hover:bg-slate-50 transition-all flex flex-col group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">
                    Anika Gupta (STU1001)
                  </span>
                  <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                    HIGH PERFORMER
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 mt-0.5">
                  Stable 9.25 CGPA & protective attendance profile
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
