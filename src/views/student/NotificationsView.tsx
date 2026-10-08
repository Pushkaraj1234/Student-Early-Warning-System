import React from 'react';
import { useApp } from '../../context/AppContext';
import { formatDate, formatTimeAgo } from '../../utils/formatting';
import { Bell, CheckCheck, AlertTriangle, BookOpen, UserCheck, CheckCircle } from 'lucide-react';

export const NotificationsView: React.FC = () => {
  const {
    role,
    notifications,
    markNotificationRead,
    markAllNotificationsRead,
  } = useApp();

  const roleNotifications = notifications.filter(
    (n) => n.targetRole === role || n.targetRole === 'all'
  );

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
            System Communication
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">Notifications & Alerts</h1>
          <p className="text-sm text-slate-500 mt-1">
            Notifications for your active role ({role})
          </p>
        </div>

        {roleNotifications.length > 0 && (
          <button
            onClick={markAllNotificationsRead}
            className="inline-flex items-center px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition"
          >
            <CheckCheck className="w-4 h-4 mr-1.5 text-slate-600" />
            Mark all as read
          </button>
        )}
      </div>

      {/* List */}
      <div className="space-y-3">
        {roleNotifications.map((n) => {
          return (
            <div
              key={n.id}
              onClick={() => markNotificationRead(n.id)}
              className={`p-4 rounded-xl border transition cursor-pointer flex items-start space-x-3.5 ${
                n.read
                  ? 'bg-white border-slate-200 hover:border-slate-300'
                  : 'bg-teal-50/50 border-teal-200/90 shadow-xs'
              }`}
            >
              <div
                className={`p-2 rounded-lg flex-shrink-0 ${
                  n.type === 'alert'
                    ? 'bg-rose-100 text-rose-600'
                    : n.type === 'intervention'
                    ? 'bg-amber-100 text-amber-600'
                    : n.type === 'checkin'
                    ? 'bg-blue-100 text-blue-600'
                    : 'bg-teal-100 text-teal-600'
                }`}
              >
                {n.type === 'alert' ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : n.type === 'intervention' ? (
                  <CheckCircle className="w-4 h-4" />
                ) : n.type === 'checkin' ? (
                  <UserCheck className="w-4 h-4" />
                ) : (
                  <BookOpen className="w-4 h-4" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h3
                    className={`text-sm font-bold truncate ${
                      n.read ? 'text-slate-800' : 'text-teal-950 font-extrabold'
                    }`}
                  >
                    {n.title}
                  </h3>
                  <span className="text-[11px] text-slate-400 whitespace-nowrap">
                    {formatTimeAgo(n.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">{n.message}</p>
              </div>

              {!n.read && (
                <span className="w-2.5 h-2.5 rounded-full bg-teal-600 self-center flex-shrink-0" />
              )}
            </div>
          );
        })}

        {roleNotifications.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            No notifications at this time.
          </div>
        )}
      </div>
    </div>
  );
};
