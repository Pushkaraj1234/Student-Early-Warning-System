import React, { useState } from 'react';
import { api } from '../../services/api.js';
import { FollowUpRecord } from '../../types.js';
import {
  CheckCircle2,
  TrendingDown,
  X,
  Sparkles,
  ClipboardCheck,
  Award,
  ArrowRight
} from 'lucide-react';

interface FollowUpModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  followUp: FollowUpRecord;
  studentName: string;
  initialAttendance?: number;
  initialCGPA?: number;
  initialBacklogs?: number;
}

export const FollowUpModal: React.FC<FollowUpModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  followUp,
  studentName,
  initialAttendance = 65,
  initialCGPA = 6.2,
  initialBacklogs = 1
}) => {
  const [observations, setObservations] = useState<string>('');
  const [studentFeedback, setStudentFeedback] = useState<string>('');
  const [updatedAttendance, setUpdatedAttendance] = useState<number>(initialAttendance + 10);
  const [updatedCGPA, setUpdatedCGPA] = useState<number>(initialCGPA + 0.3);
  const [updatedBacklogs, setUpdatedBacklogs] = useState<number>(Math.max(0, initialBacklogs - 1));
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [completionResult, setCompletionResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await api.completeFollowUp(followUp.id, {
        observations,
        studentFeedback,
        updatedAttendance: Number(updatedAttendance),
        updatedCGPA: Number(updatedCGPA),
        updatedBacklogs: Number(updatedBacklogs)
      });
      setCompletionResult(res);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to complete follow-up review');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div id="followup-review-modal" className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-xl w-full overflow-hidden transition-all flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-slate-900 text-white p-5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg">
              <ClipboardCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Log Follow-up & Dynamic Risk Re-evaluation
              </h2>
              <p className="text-xs text-slate-400">
                Candidate: <strong className="text-white">{studentName}</strong> • Scheduled: {followUp.scheduled_date}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800">
              {error}
            </div>
          )}

          {completionResult ? (
            /* Outcome display with dynamic risk delta */
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                <TrendingDown className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Dynamic Re-evaluation Completed!
              </h3>
              <p className="text-xs text-slate-600 max-w-md mx-auto">
                {completionResult.message}
              </p>

              <div className="grid grid-cols-2 gap-3 max-w-xs mx-auto text-center pt-2">
                <div className="bg-white p-3 rounded-xl border border-slate-200">
                  <div className="text-[10px] uppercase font-bold text-slate-500">Prior Risk</div>
                  <div className="text-xl font-bold font-mono text-slate-700 mt-1">
                    {completionResult.previousRisk}%
                  </div>
                </div>
                <div className="bg-emerald-100/70 p-3 rounded-xl border border-emerald-300">
                  <div className="text-[10px] uppercase font-bold text-emerald-800">New Risk Score</div>
                  <div className="text-xl font-black font-mono text-emerald-700 mt-1">
                    {completionResult.newRisk}%
                  </div>
                  <div className="text-[10px] text-emerald-700 font-bold mt-0.5">
                    ({completionResult.riskLevel})
                  </div>
                </div>
              </div>

              {completionResult.improvedDelta > 0 && (
                <div className="text-xs font-bold text-emerald-800 bg-emerald-100 py-1.5 px-3 rounded-lg inline-block">
                  Risk decreased by {completionResult.improvedDelta}% following intervention
                </div>
              )}

              <div className="pt-2">
                <button
                  onClick={onClose}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-xs"
                >
                  Close & View Updated Student Profile
                </button>
              </div>
            </div>
          ) : (
            <form id="followup-form" onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1 uppercase tracking-wider">
                  Faculty Mentor Observations & Outcome Assessment
                </label>
                <textarea
                  rows={3}
                  required
                  value={observations}
                  onChange={e => setObservations(e.target.value)}
                  placeholder="Note attendance at remedial sessions, changes in engagement, and feedback from course teachers..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1 uppercase tracking-wider">
                  Student's Self-Reported Feedback
                </label>
                <input
                  type="text"
                  value={studentFeedback}
                  onChange={e => setStudentFeedback(e.target.value)}
                  placeholder="Student's perception of remedial clinics and peer tutoring..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-900"
                />
              </div>

              {/* Updated metric inputs for dynamic re-evaluation */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <span>Post-Intervention Metric Refresh (Triggers Dynamic Re-evaluation)</span>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                      Updated Att. (%)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="100"
                      value={updatedAttendance}
                      onChange={e => setUpdatedAttendance(Number(e.target.value))}
                      className="w-full text-xs font-mono border border-slate-300 rounded-md p-1.5 text-slate-900"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                      Updated CGPA
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="10"
                      value={updatedCGPA}
                      onChange={e => setUpdatedCGPA(Number(e.target.value))}
                      className="w-full text-xs font-mono border border-slate-300 rounded-md p-1.5 text-slate-900"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                      Active Backlogs
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      value={updatedBacklogs}
                      onChange={e => setUpdatedBacklogs(Number(e.target.value))}
                      className="w-full text-xs font-mono border border-slate-300 rounded-md p-1.5 text-slate-900"
                    />
                  </div>
                </div>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        {!completionResult && (
          <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex items-center justify-between">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              form="followup-form"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors disabled:opacity-50"
            >
              {isSubmitting ? 'Computing Re-evaluation...' : 'Submit & Recompute Risk'}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
