import React from 'react';
import { useApp } from '../../context/AppContext';
import { BookOpen, Award, CheckCircle, Clock } from 'lucide-react';

export const AcademicsView: React.FC = () => {
  const { currentStudent, academics, courses } = useApp();

  const completedCourses = courses.filter((c) => c.status === 'completed');
  const enrolledCourses = courses.filter((c) => c.status === 'enrolled');

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
              Academic Transcript & Enrollment
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
              Curriculum & Academic Progress
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              {currentStudent.programme} &middot; Current Semester {currentStudent.currentSemester}
            </p>
          </div>

          <div className="flex items-center space-x-4 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <div>
              <div className="text-xs text-slate-500">Cumulative GPA</div>
              <div className="text-xl font-extrabold font-mono text-teal-800">
                {academics[academics.length - 1]?.cgpa?.toFixed(2) ?? '8.55'}
              </div>
            </div>
            <div className="border-l border-slate-200 pl-4">
              <div className="text-xs text-slate-500">Total Credits Earned</div>
              <div className="text-xl font-extrabold font-mono text-slate-800">
                {academics.reduce((sum, a) => sum + a.creditsEarned, 0)} credits
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Current Semester Enrolments */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center">
          <Clock className="w-5 h-5 mr-2 text-teal-600" />
          Current Semester Enrolments (Semester {currentStudent.currentSemester})
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-semibold border-y border-slate-200">
              <tr>
                <th className="py-3 px-4">Course Code</th>
                <th className="py-3 px-4">Title</th>
                <th className="py-3 px-4">Credits</th>
                <th className="py-3 px-4">Term</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {enrolledCourses.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3 px-4 font-mono font-medium text-teal-800">{c.courseCode}</td>
                  <td className="py-3 px-4 font-semibold text-slate-900">{c.courseTitle}</td>
                  <td className="py-3 px-4 text-slate-600">{c.credits}</td>
                  <td className="py-3 px-4 text-slate-500">{c.academicYear}</td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                      Enrolled
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Semester History & Performance */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center">
          <Award className="w-5 h-5 mr-2 text-teal-600" />
          Past Semester Results
        </h2>

        <div className="space-y-6">
          {academics.map((record) => (
            <div key={record.semester} className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="bg-slate-50 px-4 py-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-sm text-slate-900">
                    Semester {record.semester} ({record.academicYear})
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase ${
                      record.resultStatus === 'pass'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {record.resultStatus}
                  </span>
                </div>
                <div className="flex items-center space-x-4 text-xs font-mono">
                  <span>
                    SGPA: <strong className="text-slate-800">{record.sgpa?.toFixed(2)}</strong>
                  </span>
                  <span>
                    CGPA: <strong className="text-slate-800">{record.cgpa?.toFixed(2)}</strong>
                  </span>
                  <span>
                    Credits: {record.creditsEarned} / {record.creditsRegistered}
                  </span>
                </div>
              </div>

              {/* Courses in this completed semester */}
              <div className="p-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-slate-400 font-semibold border-b border-slate-100 pb-2">
                      <th className="pb-2">Course Code</th>
                      <th className="pb-2">Course Name</th>
                      <th className="pb-2">Credits</th>
                      <th className="pb-2">Marks</th>
                      <th className="pb-2">Grade</th>
                      <th className="pb-2">Points</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {completedCourses
                      .filter((c) => c.semester === record.semester)
                      .map((course) => (
                        <tr key={course.id} className="py-2">
                          <td className="py-2 font-mono font-medium text-slate-700">
                            {course.courseCode}
                          </td>
                          <td className="py-2 font-medium text-slate-900">{course.courseTitle}</td>
                          <td className="py-2 text-slate-600">{course.credits}</td>
                          <td className="py-2 font-mono">{course.marks}%</td>
                          <td className="py-2">
                            <span
                              className={`px-1.5 py-0.5 rounded font-mono font-bold ${
                                course.grade === 'F'
                                  ? 'bg-rose-100 text-rose-700'
                                  : 'bg-emerald-100 text-emerald-800'
                              }`}
                            >
                              {course.grade}
                            </span>
                          </td>
                          <td className="py-2 font-mono text-slate-600">{course.gradePoints}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
