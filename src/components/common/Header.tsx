import React, { useState, useEffect } from 'react';
import { useAuth, PRESET_ACCOUNTS } from '../../context/AuthContext.js';
import { api } from '../../services/api.js';
import { NotificationItem } from '../../types.js';
import {
  GraduationCap,
  Bell,
  CheckCircle,
  LogOut,
  ChevronDown,
  Terminal,
  Shield,
  UserCheck,
  Sparkles,
  ExternalLink
} from 'lucide-react';

interface HeaderProps {
  onOpenTestModal?: () => void;
  onOpenTestRunner?: () => void;
  onOpenDataImport?: () => void;
  onNavigateStudent?: (studentId: string) => void;
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  onTabChange?: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenTestModal,
  onOpenTestRunner,
  onOpenDataImport,
  onNavigateStudent,
  activeTab = 'dashboard',
  onSelectTab,
  onTabChange
}) => {
  const triggerTestModal = onOpenTestRunner || onOpenTestModal || (() => {});
  const handleTabSelect = (tab: string) => {
    onSelectTab?.(tab);
    onTabChange?.(tab);
  };
  const { user, role, logout, quickLogin } = useAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [showNotifs, setShowNotifs] = useState<boolean>(false);
  const [showRoleMenu, setShowRoleMenu] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    async function fetchNotifs() {
      if (!user) return;
      try {
        const data = await api.getNotifications();
        if (isMounted) {
          setNotifications(data.notifications || []);
          setUnreadCount(data.unreadCount || 0);
        }
      } catch (err) {
        // Silent catch for background poll
      }
    }

    fetchNotifs();
    const interval = setInterval(fetchNotifs, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [user]);

  const handleMarkRead = async (id: string, linkUrl?: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: 1 } : n))
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
      if (linkUrl && onNavigateStudent) {
        const match = linkUrl.match(/STU\d+/);
        if (match) {
          onNavigateStudent(match[0]);
          setShowNotifs(false);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & System Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-xs">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-slate-900 tracking-tight text-base sm:text-lg">
                  SEWS
                </span>
                <span className="hidden sm:inline-block text-[11px] font-semibold uppercase tracking-wider bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-md border border-indigo-100">
                  AI Early Warning System
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden md:block">
                Academic Risk Prediction & Explainable Mentorship Platform
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          {(onSelectTab || onTabChange) && (
            <nav className="hidden lg:flex items-center gap-1 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60 text-xs font-semibold">
              <button
                onClick={() => handleTabSelect('dashboard')}
                className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'dashboard' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                {role === 'STUDENT' ? 'My Progress' : 'Executive Overview'}
              </button>
              {role !== 'STUDENT' && (
                <>
                  <button
                    onClick={() => handleTabSelect('students')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'students' || activeTab === 'student-profile' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    Cohort Directory
                  </button>
                  <button
                    onClick={() => handleTabSelect('interventions')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'interventions' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    Interventions
                  </button>
                  <button
                    onClick={() => handleTabSelect('model-performance')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'model-performance' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    ML Evaluation
                  </button>
                  <button
                    onClick={() => handleTabSelect('audit-logs')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'audit-logs' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
                  >
                    Audit Trail
                  </button>
                  {role === 'ADMIN' && (
                    <button
                      onClick={() => handleTabSelect('settings')}
                      className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'settings' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
                    >
                      Settings
                    </button>
                  )}
                </>
              )}
            </nav>
          )}

          {/* Right Action Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* System Test Runner Button */}
            <button
              id="header-test-runner-btn"
              onClick={triggerTestModal}
              title="Run end-to-end automated verification tests"
              className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300/80 text-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-colors"
            >
              <Terminal className="w-3.5 h-3.5 text-indigo-600" />
              <span className="hidden sm:inline">Verify System</span>
            </button>

            {/* Quick Role Switcher Dropdown (for effortless tester evaluation) */}
            <div className="relative">
              <button
                id="role-switcher-toggle"
                onClick={() => setShowRoleMenu(prev => !prev)}
                className="inline-flex items-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-800 text-xs font-bold px-2.5 py-1.5 rounded-lg transition-colors"
              >
                <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
                <span className="hidden md:inline">Switch Persona</span>
                <span className="md:hidden">Persona</span>
                <ChevronDown className="w-3.5 h-3.5 opacity-60" />
              </button>

              {showRoleMenu && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in zoom-in-95">
                  <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400 border-b border-slate-100">
                    Switch Test Persona (1-Click)
                  </div>
                  {Object.entries(PRESET_ACCOUNTS).map(([key, item]) => (
                    <button
                      key={key}
                      onClick={() => {
                        quickLogin(key as any);
                        setShowRoleMenu(false);
                      }}
                      className="w-full text-left px-3 py-2 text-xs hover:bg-indigo-50/70 flex flex-col transition-colors"
                    >
                      <span className="font-bold text-slate-800">{item.label}</span>
                      <span className="text-[10px] text-slate-500">{item.desc}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Notification Bell */}
            <div className="relative">
              <button
                id="notifications-toggle-btn"
                onClick={() => setShowNotifs(prev => !prev)}
                className="relative p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-rose-500 text-white rounded-full text-[10px] font-bold flex items-center justify-center animate-pulse">
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifs && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50">
                  <div className="px-4 py-2 text-xs font-bold text-slate-900 border-b border-slate-100 flex items-center justify-between">
                    <span>Notifications & Alerts</span>
                    <span className="text-[10px] text-slate-400 font-normal">{unreadCount} unread</span>
                  </div>
                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                    {notifications.length === 0 ? (
                      <div className="text-center py-6 text-xs text-slate-400">
                        No notifications at this time.
                      </div>
                    ) : (
                      notifications.map(n => {
                        const linkUrl = n.linkUrl || (n as any).link_url;
                        const isRead = n.isRead ?? (n as any).is_read;
                        const createdAt = n.createdAt || (n as any).created_at;

                        return (
                          <div
                            key={n.id}
                            onClick={() => handleMarkRead(n.id, linkUrl)}
                            className={`p-3 text-xs cursor-pointer transition-colors ${!isRead ? 'bg-indigo-50/40 hover:bg-indigo-50' : 'hover:bg-slate-50'}`}
                          >
                            <div className="flex items-start justify-between gap-1">
                              <span className="font-bold text-slate-900">{n.title}</span>
                              {!isRead && (
                                <span className="w-2 h-2 rounded-full bg-indigo-600 shrink-0 mt-1"></span>
                              )}
                            </div>
                            <p className="text-slate-600 text-[11px] mt-1 line-clamp-2">
                              {n.message}
                            </p>
                            <div className="flex items-center justify-between mt-2 text-[10px] text-slate-400">
                              <span>{createdAt ? new Date(createdAt).toLocaleDateString() : 'Recent'}</span>
                              {linkUrl && (
                                <span className="text-indigo-600 font-semibold flex items-center gap-0.5">
                                  View <ExternalLink className="w-2.5 h-2.5" />
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Current User Info & Logout */}
            <div className="flex items-center gap-2 border-l border-slate-200 pl-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-bold text-slate-900 leading-tight">
                  {user?.name || 'User'}
                </div>
                <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  {role}
                </div>
              </div>

              <button
                id="logout-btn"
                onClick={logout}
                title="Log out"
                className="p-2 text-slate-500 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
