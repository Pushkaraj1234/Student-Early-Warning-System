import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { Student, RiskLevel } from '../../types.js';
import { RiskBadge } from '../common/RiskBadge.js';
import {
  Search,
  Filter,
  Users,
  ChevronLeft,
  ChevronRight,
  Eye,
  PlusCircle,
  FileSpreadsheet,
  AlertOctagon,
  Sparkles,
  ArrowUpDown
} from 'lucide-react';

interface StudentDirectoryProps {
  onSelectStudent: (studentId: string) => void;
  assignedOnly?: boolean;
  onOpenImport?: () => void;
  title?: string;
  subtitle?: string;
}

export const StudentDirectory: React.FC<StudentDirectoryProps> = ({
  onSelectStudent,
  assignedOnly = false,
  onOpenImport,
  title = 'Student Cohort Directory',
  subtitle = 'Continuous multi-source risk assessment & mentor assignments'
}) => {
  const [students, setStudents] = useState<Student[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Filters
  const [departmentId, setDepartmentId] = useState<string>('ALL');
  const [riskLevel, setRiskLevel] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  useEffect(() => {
    fetchData();
  }, [page, departmentId, riskLevel, assignedOnly]);

  // Debounced search
  useEffect(() => {
    const handler = setTimeout(() => {
      fetchData();
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const res = await api.getStudents({
        departmentId: departmentId !== 'ALL' ? departmentId : undefined,
        riskLevel: riskLevel !== 'ALL' ? riskLevel : undefined,
        search: searchTerm.trim() || undefined,
        page,
        limit: 10,
        assignedOnly
      });
      setStudents(res.students || []);
      setTotal(res.total || 0);
      setTotalPages(res.totalPages || 1);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
              <Users className="w-4 h-4" />
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              {title}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {subtitle} • Showing {total} student records
          </p>
        </div>

        {onOpenImport && (
          <button
            onClick={onOpenImport}
            className="inline-flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-xs transition-colors self-start sm:self-auto"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Ingest Student CSV
          </button>
        )}
      </div>

      {/* Filter Controls Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
        {/* Search */}
        <div className="sm:col-span-5 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            placeholder="Search by student name or roll ID (e.g. STU1024)..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-900"
          />
        </div>

        {/* Department Filter */}
        <div className="sm:col-span-4">
          <select
            value={departmentId}
            onChange={e => {
              setDepartmentId(e.target.value);
              setPage(1);
            }}
            className="w-full py-2 px-3 text-xs border border-slate-300 rounded-xl bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-medium"
          >
            <option value="ALL">All Departments</option>
            <option value="dept-cse">Computer Science & Engineering</option>
            <option value="dept-ece">Electronics & Communication</option>
            <option value="dept-it">Information Technology</option>
            <option value="dept-me">Mechanical Engineering</option>
          </select>
        </div>

        {/* Risk Level Filter */}
        <div className="sm:col-span-3">
          <select
            value={riskLevel}
            onChange={e => {
              setRiskLevel(e.target.value);
              setPage(1);
            }}
            className="w-full py-2 px-3 text-xs border border-slate-300 rounded-xl bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 font-medium"
          >
            <option value="ALL">All Risk Categories</option>
            <option value="CRITICAL">Critical Risk (≥76%)</option>
            <option value="HIGH">High Risk (56-75%)</option>
            <option value="MODERATE">Moderate Risk (31-55%)</option>
            <option value="LOW">Low Risk (≤30%)</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="border border-slate-200 rounded-xl overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
          <thead className="bg-slate-50 font-semibold text-slate-700 uppercase text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Student Name & ID</th>
              <th className="px-3.5 py-3">Department</th>
              <th className="px-3 py-3 text-center">CGPA</th>
              <th className="px-3 py-3 text-center">Attendance</th>
              <th className="px-3 py-3 text-center">Backlogs</th>
              <th className="px-3.5 py-3 text-center">Model Risk Score</th>
              <th className="px-3.5 py-3 text-center">Active Interventions</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white font-medium">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="text-center py-10 text-slate-400">
                  Loading student roster and dynamic risk classifications...
                </td>
              </tr>
            ) : students.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-10 text-slate-400">
                  No students matched your search criteria.
                </td>
              </tr>
            ) : (
              students.map(s => (
                <tr
                  key={s.id}
                  onClick={() => onSelectStudent(s.id)}
                  className="hover:bg-indigo-50/30 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-bold text-slate-900">{s.name}</div>
                    <div className="text-[10px] font-mono text-slate-500">{s.id} • {s.email}</div>
                  </td>
                  <td className="px-3.5 py-3">
                    <span className="font-mono text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                      {s.departmentCode || s.departmentName || s.department_id || s.departmentId}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center font-mono font-bold text-slate-800">
                    {(s.currentCGPA ?? s.current_cgpa ?? 0).toFixed(2)}
                  </td>
                  <td className="px-3 py-3 text-center font-mono">
                    {(() => {
                      const att = s.attendance_rate;
                      return (
                        <span className={att !== undefined && att < 75 ? 'text-rose-600 font-bold' : 'text-slate-700'}>
                          {att !== undefined ? `${att}%` : '-'}
                        </span>
                      );
                    })()}
                  </td>
                  <td className="px-3 py-3 text-center font-mono">
                    {(() => {
                      const bl = s.backlogCount ?? s.backlog_count ?? 0;
                      return (
                        <span className={bl > 0 ? 'text-amber-700 font-bold bg-amber-50 px-1.5 py-0.5 rounded' : 'text-slate-500'}>
                          {bl}
                        </span>
                      );
                    })()}
                  </td>
                  <td className="px-3.5 py-3 text-center">
                    <RiskBadge
                      level={(s.currentRiskLevel || s.risk_level || 'LOW') as RiskLevel}
                      probability={s.currentRiskProbability ?? s.risk_probability}
                      size="sm"
                    />
                  </td>
                  <td className="px-3.5 py-3 text-center font-mono">
                    {s.activeInterventionCount && s.activeInterventionCount > 0 ? (
                      <span className="text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded text-[10px] font-bold">
                        {s.activeInterventionCount} Active
                      </span>
                    ) : (
                      <span className="text-slate-400 text-[10px]">None</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectStudent(s.id);
                      }}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      View Profile
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between pt-2 text-xs text-slate-500">
        <div>
          Showing page <span className="font-bold text-slate-800">{page}</span> of <span className="font-bold text-slate-800">{totalPages}</span> ({total} total students)
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setPage(prev => Math.max(1, prev - 1))}
            disabled={page === 1}
            className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-mono font-bold text-slate-700">{page}</span>
          <button
            onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
