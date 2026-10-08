import React from 'react';
import { useApp } from '../../context/AppContext';
import { RiskBadge, TrajectoryBadge, ProvenanceBadge } from '../../components/RiskBadge';
import { formatDate } from '../../utils/formatting';
import {
  ArrowRight,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Clock,
  BookOpen,
  MessageSquare,
  FileText,
  UserCheck,
} from 'lucide-react';

interface DashboardViewProps {
  onNavigate: (tab: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate }) => {
  const {
    currentStudent,
    latestPrediction,
    interventions,
    academics,
    assignments,
    attendanceStats,
  } = useApp();

  const studentInterventions = interventions.filter(
    (i) => i.studentId === currentStudent.id && i.status !== 'declined'
  );

  const pendingAssignments = assignments.filter(
    (a) => a.status === 'upcoming' || a.status === 'missing' || a.status === 'late'
  );

  const latestSemester = academics[academics.length - 1];

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Student Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono mb-1">
            Student Profile · {currentStudent.rollNumber}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Hello, {currentStudent.fullName.split(' ').slice(-1)[0]}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {currentStudent.programme} &middot; Semester {currentStudent.currentSemester}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => onNavigate('checkin')}
            className="inline-flex items-center px-4 py-2 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 font-medium text-sm transition shadow-sm"
          >
            <MessageSquare className="w-4 h-4 mr-2 text-teal-600" />
            Check in with Mentor
          </button>
        </div>
      </div>

      {/* Primary Risk Signal Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Academic Early Warning Signal
              </span>
              {latestPrediction && <ProvenanceBadge provenance={latestPrediction.provenance} />}
            </div>
            {latestPrediction && (
              <span className="text-xs text-slate-400">
                Calculated on {formatDate(latestPrediction.predictionDate)} &middot; Model:{' '}
                <span className="font-mono text-slate-600">{latestPrediction.modelVersion}</span>
              </span>
            )}
          </div>

          <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
            <div className="md:col-span-2 space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-medium text-slate-500">Current Estimate:</span>
                {latestPrediction ? (
                  <>
                    <RiskBadge level={latestPrediction.riskLevel} size="lg" />
                    <TrajectoryBadge trajectory={latestPrediction.trajectory} />
                  </>
                ) : (
                  <span className="text-slate-400">No predictions recorded yet</span>
                )}
              </div>

              <p className="text-sm text-slate-600 leading-relaxed">
                {latestPrediction?.riskLevel === 'high'
                  ? 'Your current activity and attendance indicators suggest you may encounter academic difficulty without prompt support. Early check-in with your mentor is recommended.'
                  : latestPrediction?.riskLevel === 'watch' || latestPrediction?.riskLevel === 'elevated'
                  ? 'Some slight shifts in attendance or submission timing have been noted. Review the recommendations below to stay on schedule.'
                  : 'Your learning activity and academic progress are on track. Keep up the consistent pace!'}
              </p>

              <div className="text-xs text-slate-400 italic">
                * Note: Estimates are probabilistic indicators based on historical academic trends, not fixed predictions.
              </div>
            </div>

            <div className="flex md:justify-end">
              <button
                onClick={() => onNavigate('risk')}
                className="w-full sm:w-auto inline-flex items-center justify-center px-5 py-3 rounded-xl bg-[#00696B] hover:bg-[#005759] text-white font-semibold text-sm transition shadow-sm group"
              >
                <span>Explain Why & Factors</span>
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Recommended Interventions & Check In */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recommended Actions */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-slate-900 flex items-center">
                <CheckCircle2 className="w-5 h-5 mr-2 text-teal-600" />
                Recommended Actions
              </h2>
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">
                {studentInterventions.length} items
              </span>
            </div>

            {studentInterventions.length === 0 ? (
              <p className="text-sm text-slate-500 py-4">
                No active intervention recommendations for your profile at this time.
              </p>
            ) : (
              <div className="space-y-3">
                {studentInterventions.map((iv) => (
                  <div
                    key={iv.id}
                    className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-semibold text-sm text-slate-900 capitalize">
                        {iv.interventionType.replace(/_/g, ' ')}
                      </div>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          iv.status === 'recommended'
                            ? 'bg-amber-100 text-amber-800'
                            : iv.status === 'in_progress'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {iv.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1 leading-normal">{iv.reason}</p>
                    <div className="text-xs text-slate-400 mt-2 flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1" />
                      Target timeline: {formatDate(iv.dueOn)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Self-Reporting / Check In Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-slate-900 flex items-center">
                <UserCheck className="w-5 h-5 mr-2 text-teal-600" />
                Student Support & Check In
              </h2>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed mb-4">
              Need assistance or experiencing difficulties with health, coursework, or personal matters?
              Submit a quick confidential check-in so your mentor can review and coordinate assistance.
            </p>

            <div className="p-3.5 rounded-lg bg-teal-50/70 border border-teal-100 text-xs text-teal-900 space-y-1">
              <div className="font-semibold">Mentoring Office Hours:</div>
              <div>Mon &ndash; Thu: 2:00 PM &ndash; 5:00 PM (Room 304, CS Dept)</div>
            </div>
          </div>

          <div className="mt-5">
            <button
              onClick={() => onNavigate('checkin')}
              className="w-full py-2.5 px-4 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-medium text-sm transition shadow-sm flex items-center justify-center space-x-2"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Submit Check-In</span>
            </button>
          </div>
        </div>
      </div>

      {/* Academic, Attendance, & Assignment Snapshots */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Academic Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <BookOpen className="w-4 h-4 mr-2 text-teal-600" />
                Academic Standing
              </h3>
              <button
                onClick={() => onNavigate('academics')}
                className="text-xs text-teal-700 hover:text-teal-900 font-semibold"
              >
                View &rarr;
              </button>
            </div>

            {latestSemester ? (
              <div className="space-y-3 mt-2">
                <div className="flex justify-between items-baseline border-b border-slate-100 pb-2">
                  <span className="text-xs text-slate-500">Cumulative GPA (CGPA)</span>
                  <span className="text-lg font-bold font-mono text-slate-900">
                    {latestSemester.cgpa?.toFixed(2) ?? 'Pending'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline border-b border-slate-100 pb-2">
                  <span className="text-xs text-slate-500">Last Semester (SGPA)</span>
                  <span className="text-sm font-semibold font-mono text-slate-800">
                    {latestSemester.sgpa?.toFixed(2) ?? 'Pending'}
                  </span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-slate-500">Earned Credits</span>
                  <span className="text-sm font-semibold text-slate-800">
                    {latestSemester.creditsEarned} / {latestSemester.creditsRegistered}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No semester results published yet.</p>
            )}
          </div>
        </div>

        {/* Attendance Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <Calendar className="w-4 h-4 mr-2 text-teal-600" />
                Attendance
              </h3>
              <button
                onClick={() => onNavigate('attendance')}
                className="text-xs text-teal-700 hover:text-teal-900 font-semibold"
              >
                View &rarr;
              </button>
            </div>

            <div className="space-y-3 mt-2">
              <div className="flex justify-between items-baseline border-b border-slate-100 pb-2">
                <span className="text-xs text-slate-500">Last 14 Days</span>
                <span
                  className={`text-lg font-bold font-mono ${
                    attendanceStats.rate14dPct < 60
                      ? 'text-rose-600'
                      : attendanceStats.rate14dPct < 75
                      ? 'text-amber-600'
                      : 'text-emerald-700'
                  }`}
                >
                  {attendanceStats.rate14dPct}%
                </span>
              </div>
              <div className="flex justify-between items-baseline border-b border-slate-100 pb-2">
                <span className="text-xs text-slate-500">Overall Semester Rate</span>
                <span className="text-sm font-semibold font-mono text-slate-800">
                  {attendanceStats.ratePct}%
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Institutional Minimum</span>
                <span className="font-semibold text-slate-700">75% required</span>
              </div>
            </div>
          </div>
        </div>

        {/* Assignments Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <FileText className="w-4 h-4 mr-2 text-teal-600" />
                Assignments
              </h3>
              <button
                onClick={() => onNavigate('assignments')}
                className="text-xs text-teal-700 hover:text-teal-900 font-semibold"
              >
                View &rarr;
              </button>
            </div>

            <div className="space-y-2 mt-2">
              {pendingAssignments.slice(0, 2).map((a) => (
                <div
                  key={a.id}
                  className="p-2 rounded bg-slate-50 border border-slate-100 text-xs flex justify-between items-center"
                >
                  <div className="truncate pr-2">
                    <div className="font-medium text-slate-800 truncate">{a.title}</div>
                    <div className="text-slate-400">{a.courseCode}</div>
                  </div>
                  <span
                    className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                      a.status === 'missing'
                        ? 'bg-rose-100 text-rose-700'
                        : a.status === 'late'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {a.status}
                  </span>
                </div>
              ))}
              {pendingAssignments.length === 0 && (
                <p className="text-xs text-slate-500 py-3 text-center">
                  All current assignments are submitted!
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
