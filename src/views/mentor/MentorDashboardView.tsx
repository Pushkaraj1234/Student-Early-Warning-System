import React from 'react';
import { useApp } from '../../context/AppContext';
import { RiskBadge, TrajectoryBadge } from '../../components/RiskBadge';
import { RiskLevel, Trajectory } from '../../types';
import {
  Users,
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  Clock,
  ArrowRight,
  UserCheck,
  ChevronRight,
  Filter,
} from 'lucide-react';

interface CaseloadItem {
  studentId: string;
  name: string;
  rollNumber: string;
  semester: number;
  programme: string;
  riskLevel: RiskLevel;
  trajectory: Trajectory;
  riskDelta: number;
  openInterventions: number;
}

interface MentorDashboardViewProps {
  onSelectStudent: (studentId: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const MentorDashboardView: React.FC<MentorDashboardViewProps> = ({
  onSelectStudent,
  onNavigateTab,
}) => {
  const { students, interventions, checkins } = useApp();

  // Caseload metadata
  const caseload: CaseloadItem[] = [
    {
      studentId: 's2',
      name: 'Synthetic Student Beta',
      rollNumber: 'SYN2025002',
      semester: 3,
      programme: 'B.Tech Computing',
      riskLevel: 'high',
      trajectory: 'rapidly_increasing',
      riskDelta: +0.19,
      openInterventions: 2,
    },
    {
      studentId: 's3',
      name: 'Synthetic Student Gamma',
      rollNumber: 'SYN2025003',
      semester: 3,
      programme: 'B.Tech Computing',
      riskLevel: 'watch',
      trajectory: 'stable',
      riskDelta: +0.02,
      openInterventions: 0,
    },
    {
      studentId: 's1',
      name: 'Synthetic Student Alpha',
      rollNumber: 'SYN2025001',
      semester: 3,
      programme: 'B.Tech Computing',
      riskLevel: 'stable',
      trajectory: 'stable',
      riskDelta: -0.01,
      openInterventions: 0,
    },
  ];

  // Counts
  const highCount = caseload.filter((c) => c.riskLevel === 'high').length;
  const elevatedCount = caseload.filter((c) => c.riskLevel === 'elevated').length;
  const watchCount = caseload.filter((c) => c.riskLevel === 'watch').length;
  const stableCount = caseload.filter((c) => c.riskLevel === 'stable').length;

  const risingStudents = caseload.filter(
    (c) => c.trajectory === 'rapidly_increasing' || c.trajectory === 'increasing'
  );

  const pendingInterventions = interventions.filter((i) => i.status === 'recommended');
  const unreviewedCheckins = checkins.filter((c) => !c.acknowledgedByMentor);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-amber-700 font-mono">
              Academic Advisory & Mentorship Portal
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">My Students (Caseload)</h1>
            <p className="text-sm text-slate-500 mt-1">
              Active assigned undergraduate cohort &middot; Department of Computing
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-amber-50 text-amber-900 border border-amber-200">
              Total Caseload: <strong>{caseload.length} Students</strong>
            </span>
          </div>
        </div>

        {/* Risk Distribution Summary Chips */}
        <div className="mt-6 pt-5 border-t border-slate-100 flex flex-wrap items-center gap-2.5">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mr-1">
            Cohort Risk:
          </span>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
            High: {highCount}
          </span>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-800 border border-orange-300">
            Elevated: {elevatedCount}
          </span>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
            Watch: {watchCount}
          </span>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
            Stable: {stableCount}
          </span>
        </div>
      </div>

      {/* Action Required Banner: Rising Risk */}
      {risingStudents.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <h2 className="text-sm font-bold text-rose-950">
                  Priority Alert: Rising Academic Risk Detected
                </h2>
                <p className="text-xs text-rose-800 mt-1 leading-relaxed">
                  The statistical trajectory model identified significant negative movement (&Delta; &ge; +0.15)
                  over the last bi-weekly scoring window. Prompt intervention review is advised.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {risingStudents.map((s) => (
                    <button
                      key={s.studentId}
                      onClick={() => onSelectStudent(s.studentId)}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg bg-white border border-rose-300 text-xs font-bold text-rose-900 hover:bg-rose-100/60 transition shadow-xs"
                    >
                      <span>{s.name} ({s.rollNumber})</span>
                      <span className="ml-1.5 font-mono text-rose-600 font-extrabold">
                        +{Math.round(s.riskDelta * 100)}%
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 ml-1 text-rose-400" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grid: Pending Interventions & Unreviewed Check-ins */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recommended Interventions Queue */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-900 text-sm flex items-center">
              <CheckCircle2 className="w-4 h-4 mr-2 text-teal-600" />
              Intervention Queue ({pendingInterventions.length} Pending)
            </h3>
            <button
              onClick={() => onNavigateTab('mentor-interventions')}
              className="text-xs text-teal-700 hover:text-teal-900 font-semibold"
            >
              Manage &rarr;
            </button>
          </div>

          <div className="space-y-2.5">
            {pendingInterventions.map((iv) => (
              <div
                key={iv.id}
                onClick={() => onSelectStudent(iv.studentId)}
                className="p-3 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 cursor-pointer transition text-xs"
              >
                <div className="flex items-center justify-between font-medium">
                  <span className="font-bold text-slate-900">{iv.studentName}</span>
                  <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold uppercase text-[10px]">
                    {iv.interventionType.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-slate-600 mt-1 line-clamp-1">{iv.reason}</p>
              </div>
            ))}
            {pendingInterventions.length === 0 && (
              <p className="text-xs text-slate-500 py-3 text-center">
                All model recommendations have been reviewed.
              </p>
            )}
          </div>
        </div>

        {/* Unreviewed Check-ins */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-900 text-sm flex items-center">
              <UserCheck className="w-4 h-4 mr-2 text-teal-600" />
              Student Check-Ins ({unreviewedCheckins.length} Unreviewed)
            </h3>
            <button
              onClick={() => onNavigateTab('mentor-checkins')}
              className="text-xs text-teal-700 hover:text-teal-900 font-semibold"
            >
              View all &rarr;
            </button>
          </div>

          <div className="space-y-2.5">
            {unreviewedCheckins.map((chk) => (
              <div
                key={chk.id}
                onClick={() => onSelectStudent(chk.studentId)}
                className="p-3 rounded-lg border border-blue-200 bg-blue-50/50 hover:bg-blue-50 cursor-pointer transition text-xs"
              >
                <div className="flex items-center justify-between font-medium">
                  <span className="font-bold text-slate-900">{chk.studentName}</span>
                  <span className="font-mono text-rose-600 font-bold">
                    Stress: {chk.stressLevel}/5
                  </span>
                </div>
                <p className="text-slate-700 mt-1 italic line-clamp-1">"{chk.message}"</p>
              </div>
            ))}
            {unreviewedCheckins.length === 0 && (
              <p className="text-xs text-slate-500 py-3 text-center">
                No pending check-ins from students.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Complete Caseload Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
          <Users className="w-5 h-5 mr-2 text-teal-600" />
          Cohort Student List
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-semibold border-y border-slate-200">
              <tr>
                <th className="py-3 px-4">Student</th>
                <th className="py-3 px-4">Programme & Sem</th>
                <th className="py-3 px-4">Risk Level</th>
                <th className="py-3 px-4">Trajectory</th>
                <th className="py-3 px-4">Change (&Delta;)</th>
                <th className="py-3 px-4">Active Interventions</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {caseload.map((entry) => (
                <tr
                  key={entry.studentId}
                  className="hover:bg-slate-50/80 transition cursor-pointer"
                  onClick={() => onSelectStudent(entry.studentId)}
                >
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-900">{entry.name}</div>
                    <div className="font-mono text-xs text-slate-500">{entry.rollNumber}</div>
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-600">
                    <div>{entry.programme}</div>
                    <div className="text-slate-400">Semester {entry.semester}</div>
                  </td>
                  <td className="py-3 px-4">
                    <RiskBadge level={entry.riskLevel} size="sm" />
                  </td>
                  <td className="py-3 px-4">
                    <TrajectoryBadge trajectory={entry.trajectory} forStaff={true} />
                  </td>
                  <td className="py-3 px-4 font-mono text-xs font-semibold">
                    {entry.riskDelta > 0 ? (
                      <span className="text-rose-600">+{Math.round(entry.riskDelta * 100)}%</span>
                    ) : (
                      <span className="text-emerald-600">{Math.round(entry.riskDelta * 100)}%</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {entry.openInterventions > 0 ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                        {entry.openInterventions} pending
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">None</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectStudent(entry.studentId);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold text-xs transition border border-teal-200"
                    >
                      Review &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
