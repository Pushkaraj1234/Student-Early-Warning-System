import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext.js';
import { StudentDirectory } from './StudentDirectory.js';
import {
  Users,
  AlertTriangle,
  AlertOctagon,
  Clock,
  CheckCircle2,
  Sparkles,
  BookOpen,
  Calendar
} from 'lucide-react';

interface FacultyDashboardProps {
  onSelectStudent: (id: string) => void;
  onOpenTestModal: () => void;
}

export const FacultyDashboard: React.FC<FacultyDashboardProps> = ({
  onSelectStudent,
  onOpenTestModal
}) => {
  const { user } = useAuth();
  const [activeQuickFilter, setActiveQuickFilter] = useState<'ALL' | 'CRITICAL' | 'ATTENDANCE_LOW'>('ALL');

  return (
    <div className="space-y-6">
      {/* Mentor Welcome Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
                <BookOpen className="w-5 h-5" />
              </span>
              <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
                Faculty Mentorship & Cohort Advisory Center
              </h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Welcome, <strong className="text-slate-800">{user?.name}</strong> • Department of Computer Science & Engineering
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Assigned Cohort Active
            </span>
          </div>
        </div>
      </div>

      {/* Student Directory Table with Mentor Cohort Filter */}
      <StudentDirectory
        onSelectStudent={onSelectStudent}
        assignedOnly={false}
        title="Department Academic Cohort"
        subtitle="Filter by risk category, search by roll ID, or click a student to view full SHAP decomposition"
      />
    </div>
  );
};
