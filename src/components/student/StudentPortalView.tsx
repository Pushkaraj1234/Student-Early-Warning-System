import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { useAuth } from '../../context/AuthContext.js';
import {
  GraduationCap,
  Calendar,
  CheckSquare,
  Clock,
  BookOpen,
  Send,
  MessageSquare,
  Sparkles,
  ShieldCheck,
  TrendingUp,
  Award,
  Activity
} from 'lucide-react';
import { RiskSparkline } from '../common/RiskSparkline.js';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts';

export const StudentPortalView: React.FC = () => {
  const { user } = useAuth();
  // Default to STU1001 (Aarav Verma) if student ID not in user object
  const studentId = user?.studentId || 'STU1001';
  const [profileData, setProfileData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [meetingRequested, setMeetingRequested] = useState<boolean>(false);
  const [studentNote, setStudentNote] = useState<string>('');
  const [feedbackSent, setFeedbackSent] = useState<boolean>(false);

  useEffect(() => {
    fetchStudentData();
  }, [studentId]);

  const fetchStudentData = async () => {
    setIsLoading(true);
    try {
      const data = await api.getStudentById(studentId);
      setProfileData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestMeeting = () => {
    setMeetingRequested(true);
    setTimeout(() => setMeetingRequested(false), 5000);
  };

  const handleSubmitFeedback = (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentNote.trim()) return;
    setFeedbackSent(true);
    setStudentNote('');
    setTimeout(() => setFeedbackSent(false), 5000);
  };

  if (isLoading || !profileData) {
    return <div className="p-16 text-center text-xs text-slate-500">Loading student academic portal...</div>;
  }

  const { student, latestPrediction, academicRecords, attendanceRecords, assessments, activeInterventions } = profileData;

  const academicChartData = (academicRecords || []).map((rec: any) => ({
    semester: `Sem ${rec.semester}`,
    gpa: rec.gpa
  }));

  // Constructive, supportive framing of academic standing
  const getConstructiveStatus = (level: string) => {
    if (level === 'CRITICAL' || level === 'HIGH') {
      return {
        badge: 'Priority Support Required',
        description: 'Your current attendance and continuous evaluation marks need targeted support. Work closely with your mentor to clear backlogs.',
        color: 'text-amber-800 bg-amber-50 border-amber-200'
      };
    }
    if (level === 'MODERATE') {
      return {
        badge: 'Focus Recommended',
        description: 'You are near the borderline attendance or grade cutoff. Maintaining consistent lecture attendance will keep you safe.',
        color: 'text-yellow-800 bg-yellow-50 border-yellow-200'
      };
    }
    return {
      badge: 'Good Standing',
      description: 'You are on track with required attendance and academic progression. Keep up the excellent work!',
      color: 'text-emerald-800 bg-emerald-50 border-emerald-200'
    };
  };

  const status = getConstructiveStatus(latestPrediction?.risk_level || 'LOW');

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Student Welcome Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-700 border border-indigo-100 flex items-center justify-center font-bold text-lg shrink-0">
              {student.name.split(' ').map((n: string) => n[0]).join('')}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
                  Welcome, {student.name}
                </h1>
                <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                  {student.id}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {student.program} • Semester {student.semester} • Assigned Faculty Mentor: <strong className="text-indigo-700">{student.assignedFacultyName}</strong>
              </p>
            </div>
          </div>

          <div>
            <span className={`text-xs font-bold px-3 py-1.5 rounded-xl border flex items-center gap-1.5 shadow-2xs ${status.color}`}>
              <ShieldCheck className="w-4 h-4" />
              {status.badge}
            </span>
          </div>
        </div>

        {/* Constructive Guidance Banner */}
        <div className="mt-5 p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 flex items-start gap-2.5">
          <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-slate-900">Academic Progress Guidance: </span>
            {status.description}
          </div>
        </div>
      </div>

      {/* Primary Academic Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Attendance */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Attendance Rate</span>
            <Clock className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-3xl font-black font-mono text-slate-900 mt-2">
            {attendanceRecords?.[0]?.percentage || 0}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Mandatory examination eligibility floor is 75%
          </div>
        </div>

        {/* CGPA */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Cumulative GPA</span>
            <Award className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-3xl font-black font-mono text-slate-900 mt-2">
            {student.current_cgpa}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Calculated across completed semesters
          </div>
        </div>

        {/* Active Backlogs */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Active Backlogs</span>
            <BookOpen className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-3xl font-black font-mono text-slate-900 mt-2">
            {student.backlog_count || 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Remedial clinics available this week
          </div>
        </div>
      </div>

      {/* Historical Risk Score & Academic Improvement Sparkline */}
      {profileData.historicalRiskTrajectory && profileData.historicalRiskTrajectory.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
                <Activity className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Semester Risk Standing & Progress Sparkline
                </h3>
                <p className="text-xs text-slate-500">
                  Continuous historical trajectory across term checkpoints (Week 1 - 16)
                </p>
              </div>
            </div>

            {profileData.historicalRiskSummary && (
              <span className={`text-xs font-bold font-mono px-2.5 py-1 rounded-lg border ${
                profileData.historicalRiskSummary.trendPattern === 'IMPROVING'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : profileData.historicalRiskSummary.trendPattern === 'DECLINING'
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}>
                {profileData.historicalRiskSummary.trendPattern === 'IMPROVING' ? 'Improving Trajectory' : profileData.historicalRiskSummary.trendPattern === 'DECLINING' ? 'Needs Attention' : 'Consistent Track'}
              </span>
            )}
          </div>

          <RiskSparkline
            points={profileData.historicalRiskTrajectory}
            summary={profileData.historicalRiskSummary}
            height={52}
          />
        </div>
      )}

      {/* Active Interventions & Mentorship Action Items */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
              <CheckSquare className="w-4 h-4" />
            </span>
            <h2 className="text-base font-bold text-slate-900">
              My Academic Support Plan & Milestones
            </h2>
          </div>
          <span className="text-xs font-semibold text-slate-500 font-mono">
            {activeInterventions?.length || 0} active plans
          </span>
        </div>

        {(!activeInterventions || activeInterventions.length === 0) ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No active remedial action items assigned right now.
          </div>
        ) : (
          <div className="space-y-4">
            {activeInterventions.map((intv: any) => {
              let actions: string[] = [];
              try {
                actions = typeof intv.action_items === 'string' ? JSON.parse(intv.action_items) : intv.action_items;
              } catch (e) {
                actions = [];
              }

              return (
                <div key={intv.id} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{intv.selected_intervention}</span>
                    <span className="text-[10px] font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">
                      {intv.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 bg-white p-3 rounded-lg border border-slate-200/60">
                    <strong>Advisor's Recommendation:</strong> {intv.faculty_notes}
                  </p>

                  <div className="space-y-1.5">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Agreed Action Milestones:
                    </div>
                    {actions.map((act, idx) => (
                      <label key={idx} className="flex items-center gap-2.5 text-xs text-slate-700 bg-white p-2.5 rounded-lg border border-slate-200 cursor-pointer">
                        <input type="checkbox" defaultChecked={idx === 0} className="rounded accent-indigo-600 w-4 h-4" />
                        <span>{act}</span>
                      </label>
                    ))}
                  </div>

                  {intv.follow_up_date && (
                    <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
                      <Calendar className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Next scheduled progress review: <strong>{intv.follow_up_date}</strong></span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Internal Continuous Assessment Grades */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-indigo-600" />
          Continuous Internal Evaluation Marks (Current Semester)
        </h3>

        <div className="border border-slate-200 rounded-xl overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
            <thead className="bg-slate-50 font-semibold text-slate-700 uppercase text-[10px]">
              <tr>
                <th className="px-4 py-2.5">Subject Code</th>
                <th className="px-4 py-2.5">Unit Test 1 (30)</th>
                <th className="px-4 py-2.5">Unit Test 2 (30)</th>
                <th className="px-4 py-2.5">Attendance</th>
                <th className="px-4 py-2.5">Assignments</th>
                <th className="px-4 py-2.5 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white font-medium">
              {(assessments || []).map((a: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-bold font-mono text-slate-900">{a.subject_id}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.internal_ut1} / 30</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.internal_ut2} / 30</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.attendance_pct}%</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.assignments_submitted} / {a.assignments_total}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      a.status === 'AT_RISK' ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Interactive Communication Panel: Request Meeting / Send Mentor Note */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* Request Meeting */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-600" />
            Schedule 1-on-1 Mentorship Session
          </h3>
          <p className="text-xs text-slate-500">
            Request an in-person or online consultation with your faculty advisor, <strong>{student.assignedFacultyName}</strong>.
          </p>

          {meetingRequested ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-semibold">
              Meeting request dispatched to your advisor! They will confirm your timeslot via institutional email.
            </div>
          ) : (
            <button
              onClick={handleRequestMeeting}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center gap-1.5"
            >
              <Calendar className="w-4 h-4" />
              Request Mentorship Appointment
            </button>
          )}
        </div>

        {/* Send Direct Note to Advisor */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-indigo-600" />
            Send Private Note or Question
          </h3>

          {feedbackSent ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-semibold">
              Message delivered to your advisor's notification portal.
            </div>
          ) : (
            <form onSubmit={handleSubmitFeedback} className="space-y-2">
              <input
                type="text"
                value={studentNote}
                onChange={e => setStudentNote(e.target.value)}
                placeholder="Ask about remedial timings, lab assignments, or request study material..."
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 text-slate-900"
              />
              <button
                type="submit"
                className="w-full py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-xl transition-colors flex items-center justify-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                Send Message
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
