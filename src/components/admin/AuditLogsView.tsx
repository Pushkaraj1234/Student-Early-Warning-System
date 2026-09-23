import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { ShieldCheck, Search, RefreshCw, FileSpreadsheet, Lock } from 'lucide-react';

export const AuditLogsView: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAuditLogs();
      setLogs(data.logs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    const q = searchTerm.toLowerCase();
    return (
      log.action?.toLowerCase().includes(q) ||
      log.user_email?.toLowerCase().includes(q) ||
      log.entity?.toLowerCase().includes(q) ||
      log.entity_id?.toLowerCase().includes(q) ||
      log.new_value?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
              <Lock className="w-4 h-4" />
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Institutional Audit Trail & Traceability
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Tamper-evident logs of system events, logins, risk recalibrations, and intervention assignments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchLogs}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Search Filter */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative max-w-sm w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Search action, email, or entity ID..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <span className="text-xs text-slate-400 font-mono">
          Showing {filteredLogs.length} audit events
        </span>
      </div>

      {/* Table */}
      <div className="border border-slate-200 rounded-xl overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
          <thead className="bg-slate-50 font-semibold text-slate-700 uppercase text-[10px] tracking-wider">
            <tr>
              <th className="px-3.5 py-3">Timestamp</th>
              <th className="px-3.5 py-3">User / Actor</th>
              <th className="px-3.5 py-3">Role</th>
              <th className="px-3.5 py-3">Action</th>
              <th className="px-3.5 py-3">Target Entity</th>
              <th className="px-3.5 py-3">Details / Value Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-400">
                  No matching audit records found.
                </td>
              </tr>
            ) : (
              filteredLogs.map(log => (
                <tr key={log.id} className="hover:bg-slate-50 font-medium">
                  <td className="px-3.5 py-2.5 text-slate-500 font-mono whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3.5 py-2.5 text-slate-900 font-semibold">
                    {log.user_email || log.user_id}
                  </td>
                  <td className="px-3.5 py-2.5">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">
                      {log.user_role || 'SYSTEM'}
                    </span>
                  </td>
                  <td className="px-3.5 py-2.5 font-bold text-indigo-700 font-mono">
                    {log.action}
                  </td>
                  <td className="px-3.5 py-2.5 text-slate-600 font-mono">
                    {log.entity} {log.entity_id ? `(${log.entity_id})` : ''}
                  </td>
                  <td className="px-3.5 py-2.5 text-slate-600 max-w-xs truncate" title={log.new_value}>
                    {log.new_value || '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
