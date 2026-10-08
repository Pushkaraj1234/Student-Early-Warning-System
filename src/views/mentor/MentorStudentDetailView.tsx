import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { RiskBadge, TrajectoryBadge, ProvenanceBadge } from '../../components/RiskBadge';
import {
  formatDate,
  formatFeatureValue,
  getFeatureDisplayTitle,
  formatDirectionText,
} from '../../utils/formatting';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  PlusCircle,
  Clock,
  Layers,
  Calendar,
  FileText,
  UserCheck,
  Send,
  MessageSquare,
  AlertTriangle,
} from 'lucide-react';
import { Intervention } from '../../types';

interface MentorStudentDetailViewProps {
  studentId: string;
  onBack: () => void;
}

export const MentorStudentDetailView: React.FC<MentorStudentDetailViewProps> = ({
  studentId,
  onBack,
}) => {
  const {
    students,
    interventions,
    updateInterventionStatus,
    addIntervention,
    checkins,
    acknowledgeCheckin,
    assignments,
    attendanceStats,
  } = useApp();

  const student = students.find((s) => s.id === studentId) || students[0];
  const studentInterventions = interventions.filter((i) => i.studentId === student.id);
  const studentCheckins = checkins.filter((c) => c.studentId === student.id);
  const studentAssignments = assignments;

  // New intervention modal/form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newType, setNewType] = useState<Intervention['interventionType']>('mentor_meeting');
  const [newReason, setNewReason] = useState('');
  const [newPriority, setNewPriority] = useState<Intervention['priority']>('high');

  // Outcome note input state
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [outcomeText, setOutcomeText] = useState('');

  // Decline modal/input state
  const [decliningId, setDecliningId] = useState<string | null>(null);
  const [declineReason, setDeclineReason] = useState('');

  const isBeta = student.id === 's2';
  const isAlpha = student.id === 's1';
  const riskLevel = isBeta ? 'high' : isAlpha ? 'stable' : 'watch';
  const trajectory = isBeta ? 'rapidly_increasing' : 'stable';
  const probability = isBeta ? 0.74 : isAlpha ? 0.06 : 0.32;

  const handleCreateIntervention = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReason.trim()) return;

    addIntervention({
      studentId: student.id,
      studentName: student.fullName,
      interventionType: newType,
      status: 'approved',
      source: 'mentor_manual',
      dueOn: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
      reason: newReason.trim(),
      priority: newPriority,
    });

    setNewReason('');
    setShowAddForm(false);
  };

  const handleCompleteIntervention = (id: string) => {
    updateInterventionStatus(id, 'completed', { outcome: outcomeText.trim() });
    setCompletingId(null);
    setOutcomeText('');
  };

  const handleDeclineIntervention = (id: string) => {
    updateInterventionStatus(id, 'declined', { declineReason: declineReason.trim() });
    setDecliningId(null);
    setDeclineReason('');
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Back to Caseload */}
      <div>
        <button
          onClick={onBack}
          className="inline-flex items-center text-sm font-semibold text-teal-700 hover:text-teal-900 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Caseload Overview
        </button>
      </div>

      {/* Student Profile Card & Risk Overview */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
              Student Advisor Record &middot; {student.rollNumber}
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">{student.fullName}</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {student.programme} &middot; Semester {student.currentSemester} &middot; {student.email}
            </p>
          </div>

          <div className="flex flex-col sm:items-end">
            <div className="flex items-center space-x-2">
              <RiskBadge level={riskLevel} size="lg" />
              <TrajectoryBadge trajectory={trajectory} forStaff={true} />
            </div>
            <div className="text-xs text-slate-400 mt-1 font-mono">
              Calibrated Prob: <strong>{(probability * 100).toFixed(0)}%</strong> &middot; Model:{' '}
              <span className="text-slate-600">seed-demo-0</span>
            </div>
          </div>
        </div>

        {/* Quick metrics grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
            <div className="text-xs text-slate-500">14-Day Attendance</div>
            <div
              className={`text-lg font-bold font-mono ${
                attendanceStats.rate14dPct < 75 ? 'text-rose-600' : 'text-emerald-700'
              }`}
            >
              {attendanceStats.rate14dPct}%
            </div>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
            <div className="text-xs text-slate-500">Overall Semester Rate</div>
            <div className="text-lg font-bold font-mono text-slate-800">
              {attendanceStats.ratePct}%
            </div>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
            <div className="text-xs text-slate-500">Cumulative GPA</div>
            <div className="text-lg font-bold font-mono text-slate-800">
              {isBeta ? '5.80' : isAlpha ? '8.55' : '7.00'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-center">
            <div className="text-xs text-slate-500">Active Interventions</div>
            <div className="text-lg font-bold font-mono text-slate-800">
              {studentInterventions.filter((i) => i.status !== 'completed' && i.status !== 'declined').length}
            </div>
          </div>
        </div>
      </div>

      {/* Interventions Section: Approve, Complete, Add */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center">
              <CheckCircle2 className="w-5 h-5 mr-2 text-teal-600" />
              Intervention Management & Recommendations
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Review rule-engine recommendations or create custom mentor outreach plans.
            </p>
          </div>

          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold text-xs border border-teal-200 transition"
          >
            <PlusCircle className="w-4 h-4 mr-1.5" />
            Add Intervention
          </button>
        </div>

        {/* Add Intervention Form */}
        {showAddForm && (
          <form
            onSubmit={handleCreateIntervention}
            className="p-4 rounded-xl bg-teal-50/50 border border-teal-200 mb-5 space-y-3"
          >
            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-900">
              Create New Mentoring Intervention
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as Intervention['interventionType'])}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 bg-white"
                >
                  <option value="mentor_meeting">Mentor 1-on-1 Meeting</option>
                  <option value="attendance_follow_up">Attendance Follow-up</option>
                  <option value="academic_tutoring">Peer Tutoring / Study Group</option>
                  <option value="wellbeing_checkin">Wellbeing & Counseling Referral</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Priority</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value as Intervention['priority'])}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 bg-white"
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Reason / Action Plan</label>
              <input
                type="text"
                value={newReason}
                onChange={(e) => setNewReason(e.target.value)}
                placeholder="e.g. Schedule review of Data Structures recursion topics and catch-up on week 4 lecture"
                className="w-full text-xs p-2 rounded-lg border border-slate-300 bg-white"
                required
              />
            </div>

            <div className="flex justify-end space-x-2 pt-1">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#00696B] text-white hover:bg-[#005759]"
              >
                Save & Assign
              </button>
            </div>
          </form>
        )}

        {/* Existing Interventions */}
        <div className="space-y-3">
          {studentInterventions.map((iv) => {
            const isRec = iv.status === 'recommended';
            const isInProg = iv.status === 'approved' || iv.status === 'in_progress';
            const isDone = iv.status === 'completed';
            const isDeclined = iv.status === 'declined';

            return (
              <div
                key={iv.id}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm text-slate-900 capitalize">
                      {iv.interventionType.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        isRec
                          ? 'bg-amber-100 text-amber-800'
                          : isInProg
                          ? 'bg-blue-100 text-blue-800'
                          : isDone
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {iv.status}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      Source: {iv.source.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Actions according to status */}
                  <div className="flex items-center space-x-2 self-end sm:self-center">
                    {isRec && (
                      <>
                        <button
                          onClick={() => updateInterventionStatus(iv.id, 'approved')}
                          className="px-2.5 py-1 rounded bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold transition"
                        >
                          Approve Action
                        </button>
                        <button
                          onClick={() => setDecliningId(iv.id)}
                          className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold transition"
                        >
                          Decline
                        </button>
                      </>
                    )}

                    {isInProg && (
                      <button
                        onClick={() => setCompletingId(iv.id)}
                        className="px-2.5 py-1 rounded bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold transition"
                      >
                        Mark Completed
                      </button>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-700 leading-normal">{iv.reason}</p>

                {iv.outcome && (
                  <div className="p-2.5 rounded bg-emerald-50 border border-emerald-200 text-xs text-emerald-900">
                    <strong>Recorded Outcome:</strong> {iv.outcome}
                  </div>
                )}

                {iv.declineReason && (
                  <div className="p-2.5 rounded bg-slate-100 border border-slate-200 text-xs text-slate-700">
                    <strong>Decline Reason:</strong> {iv.declineReason}
                  </div>
                )}

                {/* Outcome notes input if completing */}
                {completingId === iv.id && (
                  <div className="pt-2 border-t border-slate-200 flex flex-col space-y-2">
                    <label className="text-xs font-medium text-slate-700">
                      Intervention Outcome / Mentoring Notes:
                    </label>
                    <textarea
                      rows={2}
                      value={outcomeText}
                      onChange={(e) => setOutcomeText(e.target.value)}
                      placeholder="e.g. Met on Oct 4. Student caught up with missed labs and agreed to weekly office hours check-in."
                      className="w-full text-xs p-2 rounded-lg border border-slate-300 bg-white"
                    />
                    <div className="flex justify-end space-x-2">
                      <button
                        type="button"
                        onClick={() => setCompletingId(null)}
                        className="px-2.5 py-1 text-xs text-slate-500"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCompleteIntervention(iv.id)}
                        className="px-3 py-1 rounded bg-emerald-700 text-white text-xs font-semibold"
                      >
                        Save & Close
                      </button>
                    </div>
                  </div>
                )}

                {/* Decline modal / reason input */}
                {decliningId === iv.id && (
                  <div className="pt-2 border-t border-slate-200 flex flex-col space-y-2">
                    <label className="text-xs font-medium text-slate-700">Reason for Declining:</label>
                    <input
                      type="text"
                      value={declineReason}
                      onChange={(e) => setDeclineReason(e.target.value)}
                      placeholder="e.g. Student already met informally; no further action needed."
                      className="w-full text-xs p-2 rounded-lg border border-slate-300 bg-white"
                    />
                    <div className="flex justify-end space-x-2">
                      <button
                        type="button"
                        onClick={() => setDecliningId(null)}
                        className="px-2.5 py-1 text-xs text-slate-500"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeclineIntervention(iv.id)}
                        className="px-3 py-1 rounded bg-rose-700 text-white text-xs font-semibold"
                      >
                        Confirm Decline
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {studentInterventions.length === 0 && (
            <p className="text-xs text-slate-500 py-3 text-center">
              No interventions recorded for this student.
            </p>
          )}
        </div>
      </div>

      {/* Student Check-ins from this Student */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-base font-bold text-slate-900 mb-3 flex items-center">
          <UserCheck className="w-5 h-5 mr-2 text-teal-600" />
          Student Check-In Feedback ({studentCheckins.length})
        </h2>

        <div className="space-y-3">
          {studentCheckins.map((chk) => (
            <div
              key={chk.id}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                    {chk.category}
                  </span>
                  <span className="text-xs font-mono font-bold text-rose-600">
                    Reported Stress: {chk.stressLevel} / 5
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-400">{formatDate(chk.createdAt)}</span>
                  {!chk.acknowledgedByMentor ? (
                    <button
                      onClick={() => acknowledgeCheckin(chk.id)}
                      className="px-2.5 py-1 rounded bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold transition"
                    >
                      Acknowledge
                    </button>
                  ) : (
                    <span className="text-xs text-emerald-700 font-semibold flex items-center">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                      Reviewed
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs sm:text-sm text-slate-800 italic">"{chk.message}"</p>
            </div>
          ))}
          {studentCheckins.length === 0 && (
            <p className="text-xs text-slate-500 py-3 text-center">
              No check-ins submitted by this student yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
