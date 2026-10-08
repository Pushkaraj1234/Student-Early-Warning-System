import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { formatDate } from '../../utils/formatting';
import { FileText, CheckCircle2, Clock, AlertCircle, Upload, Check } from 'lucide-react';

export const AssignmentsView: React.FC = () => {
  const { currentStudent, assignments, submitAssignment } = useApp();
  const [filter, setFilter] = useState<'all' | 'pending' | 'submitted' | 'missing'>('all');
  const [submittingId, setSubmittingId] = useState<string | null>(null);

  const filteredAssignments = assignments.filter((a) => {
    if (filter === 'pending') return a.status === 'upcoming';
    if (filter === 'submitted') return a.status === 'submitted' || a.status === 'late';
    if (filter === 'missing') return a.status === 'missing';
    return true;
  });

  const handleSubmit = (id: string) => {
    setSubmittingId(id);
    setTimeout(() => {
      submitAssignment(id);
      setSubmittingId(null);
    }, 600);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
              Coursework & Deliverables
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">Assignments & Quizzes</h1>
            <p className="text-sm text-slate-500 mt-1">
              {currentStudent.fullName} &middot; Semester {currentStudent.currentSemester}
            </p>
          </div>

          {/* Quick status tabs */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            {(['all', 'pending', 'submitted', 'missing'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-3 py-1.5 rounded-lg capitalize transition ${
                  filter === tab
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Assignment List */}
      <div className="space-y-4">
        {filteredAssignments.map((a) => {
          const isLate = a.status === 'late';
          const isMissing = a.status === 'missing';
          const isSubmitted = a.status === 'submitted';
          const isUpcoming = a.status === 'upcoming';

          return (
            <div
              key={a.id}
              className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-teal-300 transition"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                    {a.courseCode}
                  </span>
                  <span className="text-xs text-slate-400">&bull; {a.courseTitle}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase ${
                      isSubmitted
                        ? 'bg-emerald-100 text-emerald-800'
                        : isLate
                        ? 'bg-amber-100 text-amber-800'
                        : isMissing
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {a.status}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900">{a.title}</h3>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                  <span className="flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    Due: {formatDate(a.dueAt)}
                  </span>
                  {a.submittedAt && (
                    <span className="text-emerald-700">
                      Submitted on {formatDate(a.submittedAt)}
                    </span>
                  )}
                  <span>Max Score: {a.maxScore} pts</span>
                </div>
              </div>

              {/* Score / Action */}
              <div className="flex items-center space-x-3 self-end sm:self-center">
                {a.score !== null && a.score !== undefined ? (
                  <div className="text-right">
                    <div className="text-xs text-slate-400">Score Awarded</div>
                    <div className="text-lg font-bold font-mono text-slate-900">
                      {a.score} / {a.maxScore}
                    </div>
                  </div>
                ) : (
                  <div className="text-right">
                    <div className="text-xs text-slate-400">Status</div>
                    <div className="text-xs font-semibold text-slate-600">Pending Grading</div>
                  </div>
                )}

                {(isUpcoming || isMissing) && (
                  <button
                    disabled={submittingId === a.id}
                    onClick={() => handleSubmit(a.id)}
                    className="inline-flex items-center px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-medium text-xs transition shadow-sm disabled:opacity-50"
                  >
                    <Upload className="w-3.5 h-3.5 mr-1.5" />
                    {submittingId === a.id ? 'Submitting...' : 'Upload Submission'}
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {filteredAssignments.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            No assignments match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
};
