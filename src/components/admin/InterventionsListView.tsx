import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { Intervention } from '../../types.js';
import { RiskBadge } from '../common/RiskBadge.js';
import {
  Calendar,
  CheckCircle2,
  Clock,
  Search,
  Filter,
  Eye,
  Sparkles,
  TrendingDown
} from 'lucide-react';

interface InterventionsListViewProps {
  onSelectStudent: (studentId: string) => void;
}

export const InterventionsListView: React.FC<InterventionsListViewProps> = ({ onSelectStudent }) => {
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchInterventions();
  }, [statusFilter]);

  const fetchInterventions = async () => {
    setIsLoading(true);
    try {
      const data = await api.getInterventions({
        status: statusFilter !== 'ALL' ? statusFilter : undefined
      });
      setInterventions(data.interventions || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = interventions.filter(i => {
    const q = searchTerm.toLowerCase();
    const studentName = i.studentName || i.student_name || '';
    const studentId = i.studentId || i.student_id || '';
    const strategy = i.selectedIntervention || i.selected_intervention || '';
    const facultyName = i.facultyName || i.faculty_name || '';
    return (
      studentName.toLowerCase().includes(q) ||
      studentId.toLowerCase().includes(q) ||
      strategy.toLowerCase().includes(q) ||
      facultyName.toLowerCase().includes(q)
    );
  });

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
              <Calendar className="w-4 h-4" />
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Institutional Mentorship & Interventions Management
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Tracking remedial coaching clinics, attendance recovery plans, and dynamic post-intervention re-evaluations.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:max-w-xs">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Search student or intervention title..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs text-slate-500 font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs font-semibold py-2 px-3 border border-slate-300 rounded-xl bg-white text-slate-800"
          >
            <option value="ALL">All Statuses</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="border border-slate-200 rounded-xl overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
          <thead className="bg-slate-50 font-semibold text-slate-700 uppercase text-[10px] tracking-wider">
            <tr>
              <th className="px-4 py-3">Student & ID</th>
              <th className="px-3.5 py-3">Intervention Strategy</th>
              <th className="px-3.5 py-3">Assigned Mentor</th>
              <th className="px-3 py-3 text-center">Initial Risk</th>
              <th className="px-3 py-3 text-center">Follow-up Review</th>
              <th className="px-3.5 py-3 text-center">Status & Outcome</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white font-medium">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400">
                  Loading interventions and follow-up metrics...
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400">
                  No interventions found matching filter.
                </td>
              </tr>
            ) : (
              filtered.map(intv => {
                const sId = intv.studentId || intv.student_id || '';
                const sName = intv.studentName || intv.student_name || 'Student';
                const strategy = intv.selectedIntervention || intv.selected_intervention || 'Mentorship Plan';
                const fNotes = intv.facultyNotes || intv.faculty_notes || 'Action plan initiated';
                const fName = intv.facultyName || intv.faculty_name || 'Assigned Advisor';
                const rLevel = intv.riskLevel || intv.risk_level || intv.riskLevelAtCreation || 'MODERATE';
                const rProb = intv.riskProbability ?? intv.risk_probability ?? intv.riskProbabilityAtCreation ?? 0.5;
                const fuDate = intv.followUpDate || intv.follow_up_date || 'Scheduled';
                const postProb = intv.postInterventionRiskProb ?? intv.post_risk_probability;

                return (
                  <tr
                    key={intv.id}
                    onClick={() => sId && onSelectStudent(sId)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900">{sName}</div>
                      <div className="text-[10px] font-mono text-slate-500">{sId}</div>
                    </td>
                    <td className="px-3.5 py-3">
                      <div className="font-bold text-slate-800">{strategy}</div>
                      <div className="text-[10px] text-slate-500 italic max-w-xs truncate">{fNotes}</div>
                    </td>
                    <td className="px-3.5 py-3 text-slate-700">
                      {fName}
                    </td>
                    <td className="px-3 py-3 text-center font-mono">
                      <RiskBadge level={rLevel} probability={rProb} size="sm" />
                    </td>
                    <td className="px-3 py-3 text-center font-mono text-slate-600">
                      {fuDate}
                    </td>
                    <td className="px-3.5 py-3 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          intv.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800'
                        }`}>
                          {intv.status}
                        </span>
                        {postProb !== null && postProb !== undefined && (
                          <span className="text-[10px] text-emerald-700 font-bold flex items-center gap-0.5">
                            <TrendingDown className="w-3 h-3" />
                            New: {Math.round(postProb * 100)}%
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (sId) onSelectStudent(sId);
                        }}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1 rounded-lg"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Review Profile
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
