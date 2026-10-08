import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Checkin } from '../../types';
import { formatDate } from '../../utils/formatting';
import {
  MessageSquare,
  Send,
  CheckCircle2,
  Clock,
  HeartPulse,
  BookOpen,
  Calendar,
  AlertCircle,
} from 'lucide-react';

export const CheckinView: React.FC = () => {
  const { currentStudent, checkins, addCheckin } = useApp();

  const [category, setCategory] = useState<Checkin['category']>('workload');
  const [stressLevel, setStressLevel] = useState<Checkin['stressLevel']>(3);
  const [message, setMessage] = useState('');
  const [submittedSuccess, setSubmittedSuccess] = useState(false);

  const studentCheckins = checkins.filter((c) => c.studentId === currentStudent.id);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    addCheckin(category, stressLevel, message.trim());
    setMessage('');
    setSubmittedSuccess(true);
    setTimeout(() => setSubmittedSuccess(false), 4000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
          Student Self-Reporting & Feedback
        </div>
        <h1 className="text-2xl font-extrabold text-slate-900 mt-1">Student Check-In</h1>
        <p className="text-sm text-slate-500 mt-1">
          Share your academic progress, stress factors, or personal circumstances directly with your assigned mentor.
        </p>
      </div>

      {/* Checkin Form */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
          <MessageSquare className="w-5 h-5 mr-2 text-teal-600" />
          Submit a New Check-In
        </h2>

        {submittedSuccess && (
          <div className="mb-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm flex items-center space-x-2 animate-in fade-in duration-200">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span>
              Your check-in has been submitted and shared with your academic mentor.
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Category selection */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Primary Area of Concern
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { id: 'workload', label: 'Course Workload', icon: BookOpen },
                { id: 'attendance', label: 'Attendance & Health', icon: Calendar },
                { id: 'wellbeing', label: 'Personal / Wellbeing', icon: HeartPulse },
                { id: 'academics', label: 'Subject Difficulty', icon: AlertCircle },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  type="button"
                  key={id}
                  onClick={() => setCategory(id as Checkin['category'])}
                  className={`p-3 rounded-xl border text-left text-xs font-semibold flex flex-col items-start justify-between transition ${
                    category === id
                      ? 'bg-teal-50 border-teal-600 text-teal-900 ring-2 ring-teal-500/20'
                      : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 mb-2 ${
                      category === id ? 'text-teal-600' : 'text-slate-400'
                    }`}
                  />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Stress Level slider / chips */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Current Pressure / Stress Level (1 = Low, 5 = Severe)
            </label>
            <div className="flex items-center space-x-2">
              {([1, 2, 3, 4, 5] as const).map((lvl) => (
                <button
                  type="button"
                  key={lvl}
                  onClick={() => setStressLevel(lvl)}
                  className={`flex-1 py-2.5 rounded-lg border font-mono font-bold text-sm transition ${
                    stressLevel === lvl
                      ? lvl >= 4
                        ? 'bg-rose-500 text-white border-rose-600 shadow-sm'
                        : 'bg-teal-700 text-white border-teal-800 shadow-sm'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>Managing well</span>
              <span>Moderate challenge</span>
              <span>Overwhelmed / Urgent</span>
            </div>
          </div>

          {/* Message textarea */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Note for Mentor
            </label>
            <textarea
              rows={4}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Explain how things are going, any illness, deadline clashes, or concepts you're finding difficult..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 transition"
              required
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end">
            <button
              type="submit"
              className="inline-flex items-center px-5 py-2.5 rounded-xl bg-[#00696B] hover:bg-[#005759] text-white font-semibold text-sm transition shadow-sm"
            >
              <Send className="w-4 h-4 mr-2" />
              <span>Send Check-In</span>
            </button>
          </div>
        </form>
      </div>

      {/* Previous Check-ins History */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
          <Clock className="w-5 h-5 mr-2 text-teal-600" />
          Previous Check-Ins ({studentCheckins.length})
        </h2>

        {studentCheckins.length === 0 ? (
          <p className="text-sm text-slate-500 py-4 text-center">
            You haven't submitted any check-ins yet.
          </p>
        ) : (
          <div className="space-y-3">
            {studentCheckins.map((chk) => (
              <div
                key={chk.id}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                      {chk.category}
                    </span>
                    <span className="text-xs text-slate-500">
                      Stress Level: <strong>{chk.stressLevel}/5</strong>
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-slate-400">{formatDate(chk.createdAt)}</span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        chk.acknowledgedByMentor
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {chk.acknowledgedByMentor ? 'Reviewed by Mentor' : 'Awaiting Review'}
                    </span>
                  </div>
                </div>
                <p className="text-xs sm:text-sm text-slate-700 italic">"{chk.message}"</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
