import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { UserRole } from '../types';
import {
  GraduationCap,
  Users,
  ShieldCheck,
  Bell,
  ChevronDown,
  Activity,
  Layers,
} from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, setCurrentTab }) => {
  const {
    role,
    setRole,
    activeStudentId,
    setActiveStudentId,
    students,
    currentStudent,
    notifications,
  } = useApp();

  const [roleMenuOpen, setRoleMenuOpen] = useState(false);

  const unreadCount = notifications.filter(
    (n) => !n.read && (n.targetRole === role || n.targetRole === 'all')
  ).length;

  const handleSelectStudent = (studentId: string) => {
    setActiveStudentId(studentId);
    setRole('student');
    setRoleMenuOpen(false);
  };

  const handleSelectRole = (newRole: UserRole) => {
    setRole(newRole);
    setRoleMenuOpen(false);
    if (newRole === 'mentor') {
      setCurrentTab('mentor-caseload');
    } else if (newRole === 'admin') {
      setCurrentTab('admin-monitoring');
    } else {
      setCurrentTab('dashboard');
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-[#00696B] text-white shadow-md">
      {/* Top Banner */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setCurrentTab(role === 'mentor' ? 'mentor-caseload' : role === 'admin' ? 'admin-monitoring' : 'dashboard')}>
            <div className="w-10 h-10 rounded-lg bg-teal-800/60 border border-teal-400/30 flex items-center justify-center shadow-inner">
              <GraduationCap className="w-6 h-6 text-teal-200" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">SEWS</span>
                <span className="text-xs uppercase px-1.5 py-0.5 rounded bg-teal-900/80 text-teal-200 font-mono border border-teal-700/50">
                  v3-Core
                </span>
              </div>
              <p className="text-xs text-teal-200/90 hidden sm:block">
                Student Early Warning & Intervention System
              </p>
            </div>
          </div>

          {/* Center/Right Controls: Role Switcher & Notifications */}
          <div className="flex items-center space-x-3">
            {/* Role & Persona Switcher */}
            <div className="relative">
              <button
                onClick={() => setRoleMenuOpen(!roleMenuOpen)}
                className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-teal-900/70 hover:bg-teal-900 border border-teal-500/30 text-xs sm:text-sm font-medium transition shadow-sm"
                aria-label="Switch Role or Persona"
              >
                <div className="flex items-center space-x-1.5">
                  {role === 'student' && <GraduationCap className="w-4 h-4 text-teal-300" />}
                  {role === 'mentor' && <Users className="w-4 h-4 text-amber-300" />}
                  {role === 'admin' && <ShieldCheck className="w-4 h-4 text-emerald-300" />}
                  <span className="font-semibold">
                    {role === 'student'
                      ? currentStudent.fullName.replace('Synthetic Student ', '')
                      : role === 'mentor'
                      ? 'Academic Mentor'
                      : 'ML Admin'}
                  </span>
                  <span className="text-teal-300 text-xs hidden md:inline">
                    ({role})
                  </span>
                </div>
                <ChevronDown className="w-4 h-4 text-teal-200" />
              </button>

              {roleMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setRoleMenuOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 text-slate-800 animate-in fade-in slide-in-from-top-2 duration-150">
                    <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Student Accounts
                    </div>
                    {students.map((s) => {
                      const isBeta = s.id === 's2';
                      const isAlpha = s.id === 's1';
                      const isGamma = s.id === 's3';
                      return (
                        <button
                          key={s.id}
                          onClick={() => handleSelectStudent(s.id)}
                          className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-50 transition ${
                            role === 'student' && activeStudentId === s.id
                              ? 'bg-teal-50 text-teal-900 font-semibold'
                              : 'text-slate-700'
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <GraduationCap className="w-4 h-4 text-teal-600" />
                            <span>{s.fullName}</span>
                          </div>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              isBeta
                                ? 'bg-rose-100 text-rose-700 border border-rose-200'
                                : isAlpha
                                ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                                : 'bg-amber-100 text-amber-700 border border-amber-200'
                            }`}
                          >
                            {isBeta ? 'High Risk' : isAlpha ? 'Stable' : 'Watch'}
                          </span>
                        </button>
                      );
                    })}

                    <div className="my-1.5 border-t border-slate-100" />
                    <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Staff & Oversight Roles
                    </div>

                    <button
                      onClick={() => handleSelectRole('mentor')}
                      className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-50 transition ${
                        role === 'mentor'
                          ? 'bg-amber-50 text-amber-900 font-semibold'
                          : 'text-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <Users className="w-4 h-4 text-amber-600" />
                        <div>
                          <div>Academic Mentor / Advisor</div>
                          <div className="text-xs text-slate-400 font-normal">
                            Caseload overview & interventions
                          </div>
                        </div>
                      </div>
                    </button>

                    <button
                      onClick={() => handleSelectRole('admin')}
                      className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-50 transition ${
                        role === 'admin'
                          ? 'bg-emerald-50 text-emerald-900 font-semibold'
                          : 'text-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-600" />
                        <div>
                          <div>System Administrator</div>
                          <div className="text-xs text-slate-400 font-normal">
                            Model registry & drift monitoring
                          </div>
                        </div>
                      </div>
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* Notification Bell */}
            <button
              onClick={() => setCurrentTab('notifications')}
              className="relative p-2 rounded-lg bg-teal-900/60 hover:bg-teal-900 border border-teal-500/30 text-teal-100 transition"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-xs font-bold rounded-full h-5 min-w-[20px] px-1 flex items-center justify-center border-2 border-[#00696B]">
                  {unreadCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Sub Navigation Bar according to current role */}
      <div className="bg-[#005759] border-t border-teal-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-1 sm:space-x-3 overflow-x-auto py-2 scrollbar-none text-xs sm:text-sm font-medium">
            {role === 'student' && (
              <>
                <button
                  onClick={() => setCurrentTab('dashboard')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'dashboard'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Home
                </button>
                <button
                  onClick={() => setCurrentTab('risk')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap flex items-center space-x-1 ${
                    currentTab === 'risk'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  <Activity className="w-3.5 h-3.5 mr-1" />
                  Risk Signals & Explainability
                </button>
                <button
                  onClick={() => setCurrentTab('academics')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'academics'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Academics
                </button>
                <button
                  onClick={() => setCurrentTab('attendance')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'attendance'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Attendance
                </button>
                <button
                  onClick={() => setCurrentTab('assignments')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'assignments'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Assignments
                </button>
                <button
                  onClick={() => setCurrentTab('checkin')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'checkin'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Check In
                </button>
                <button
                  onClick={() => setCurrentTab('profile')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'profile'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Profile & Ethics
                </button>
              </>
            )}

            {role === 'mentor' && (
              <>
                <button
                  onClick={() => setCurrentTab('mentor-caseload')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap flex items-center space-x-1 ${
                    currentTab === 'mentor-caseload'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  <Users className="w-3.5 h-3.5 mr-1" />
                  Caseload & Students
                </button>
                <button
                  onClick={() => setCurrentTab('mentor-interventions')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'mentor-interventions'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Intervention Queue
                </button>
                <button
                  onClick={() => setCurrentTab('mentor-checkins')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'mentor-checkins'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Student Check-ins
                </button>
              </>
            )}

            {role === 'admin' && (
              <>
                <button
                  onClick={() => setCurrentTab('admin-monitoring')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap flex items-center space-x-1 ${
                    currentTab === 'admin-monitoring'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 mr-1" />
                  Model Registry
                </button>
                <button
                  onClick={() => setCurrentTab('admin-drift')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'admin-drift'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Drift Alerts
                </button>
                <button
                  onClick={() => setCurrentTab('admin-snapshots')}
                  className={`px-3 py-1.5 rounded-md transition whitespace-nowrap ${
                    currentTab === 'admin-snapshots'
                      ? 'bg-teal-900 text-white shadow-sm'
                      : 'text-teal-100 hover:bg-teal-800/60'
                  }`}
                >
                  Monitoring Windows
                </button>
              </>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
};
