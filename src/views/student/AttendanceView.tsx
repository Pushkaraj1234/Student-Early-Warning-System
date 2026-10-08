import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Calendar, AlertTriangle, CheckCircle, Clock, XCircle, Info } from 'lucide-react';

export const AttendanceView: React.FC = () => {
  const { currentStudent, attendanceStats, courses } = useApp();
  const enrolledCourses = courses.filter((c) => c.status === 'enrolled');

  // Generate realistic recent attendance session records
  const [selectedCourse, setSelectedCourse] = useState<string>('all');

  const attendanceLog = [
    { date: '2026-10-06', course: 'SYN-CS201', session: 1, status: attendanceStats.rate14dPct < 60 ? 'absent' : 'present' },
    { date: '2026-10-05', course: 'SYN-CS202', session: 1, status: attendanceStats.rate14dPct < 60 ? 'absent' : 'present' },
    { date: '2026-10-03', course: 'SYN-MA201', session: 1, status: 'present' },
    { date: '2026-10-02', course: 'SYN-CS201', session: 1, status: attendanceStats.rate14dPct < 60 ? 'absent' : 'present' },
    { date: '2026-09-30', course: 'SYN-CS202', session: 1, status: attendanceStats.rate14dPct < 60 ? 'absent' : 'present' },
    { date: '2026-09-29', course: 'SYN-MA201', session: 1, status: 'present' },
    { date: '2026-09-26', course: 'SYN-CS201', session: 1, status: 'present' },
    { date: '2026-09-25', course: 'SYN-CS202', session: 1, status: 'excused' },
    { date: '2026-09-23', course: 'SYN-MA201', session: 1, status: 'present' },
    { date: '2026-09-22', course: 'SYN-CS201', session: 1, status: 'present' },
  ];

  const filteredLog = selectedCourse === 'all'
    ? attendanceLog
    : attendanceLog.filter((l) => l.course === selectedCourse);

  const isBelowRequirement = attendanceStats.rate14dPct < 75;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
              Attendance Records & Monitoring
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
              Class Attendance
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              {currentStudent.fullName} &middot; Semester {currentStudent.currentSemester} (2026-27)
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <div className="bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-xl text-center">
              <div className="text-xs text-slate-500">Overall Rate</div>
              <div
                className={`text-xl font-extrabold font-mono ${
                  attendanceStats.ratePct < 75 ? 'text-rose-600' : 'text-emerald-700'
                }`}
              >
                {attendanceStats.ratePct}%
              </div>
            </div>
            <div className="bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-xl text-center">
              <div className="text-xs text-slate-500">Last 14 Days</div>
              <div
                className={`text-xl font-extrabold font-mono ${
                  attendanceStats.rate14dPct < 75 ? 'text-rose-600' : 'text-emerald-700'
                }`}
              >
                {attendanceStats.rate14dPct}%
              </div>
            </div>
          </div>
        </div>

        {/* Warning if below threshold */}
        {isBelowRequirement && (
          <div className="mt-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs sm:text-sm text-rose-900 flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-rose-950">Attendance Requirement Alert (Below 75%)</p>
              <p className="text-rose-800 mt-0.5">
                Institutional regulations require at least 75% attendance to sit for end-of-semester examinations.
                Your current rate ({attendanceStats.ratePct}%) is below this threshold. Connect with your academic mentor to discuss remediation options.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Course Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {enrolledCourses.map((c, i) => {
          const courseRate = attendanceStats.ratePct > 80 ? 88 + i * 3 : 50 + i * 5;
          return (
            <div key={c.id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
              <div className="text-xs font-mono font-semibold text-teal-800">{c.courseCode}</div>
              <div className="text-sm font-bold text-slate-900 truncate mt-0.5">{c.courseTitle}</div>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-slate-500">Course Rate:</span>
                <span
                  className={`text-base font-bold font-mono ${
                    courseRate < 75 ? 'text-rose-600' : 'text-emerald-700'
                  }`}
                >
                  {courseRate}%
                </span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-2">
                <div
                  className={`h-full rounded-full ${courseRate < 75 ? 'bg-rose-500' : 'bg-teal-600'}`}
                  style={{ width: `${courseRate}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Session Logs */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center">
            <Calendar className="w-5 h-5 mr-2 text-teal-600" />
            Recent Session Logs
          </h2>

          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-500">Filter Course:</span>
            <select
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs text-slate-700 bg-white"
            >
              <option value="all">All Courses</option>
              {enrolledCourses.map((c) => (
                <option key={c.courseCode} value={c.courseCode}>
                  {c.courseCode}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-semibold border-y border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Date</th>
                <th className="py-2.5 px-4">Course</th>
                <th className="py-2.5 px-4">Session</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLog.map((log, idx) => (
                <tr key={idx} className="hover:bg-slate-50/70 transition">
                  <td className="py-2.5 px-4 font-mono text-slate-700">{log.date}</td>
                  <td className="py-2.5 px-4 font-medium text-slate-900">{log.course}</td>
                  <td className="py-2.5 px-4 text-slate-500">Session #{log.session}</td>
                  <td className="py-2.5 px-4">
                    {log.status === 'present' ? (
                      <span className="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Present
                      </span>
                    ) : log.status === 'excused' ? (
                      <span className="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                        <Clock className="w-3 h-3 mr-1" />
                        Excused
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800">
                        <XCircle className="w-3 h-3 mr-1" />
                        Absent
                      </span>
                    )}
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
