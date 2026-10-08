import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Navbar } from './components/Navbar';
import { DashboardView } from './views/student/DashboardView';
import { RiskExplanationView } from './views/student/RiskExplanationView';
import { AcademicsView } from './views/student/AcademicsView';
import { AttendanceView } from './views/student/AttendanceView';
import { AssignmentsView } from './views/student/AssignmentsView';
import { CheckinView } from './views/student/CheckinView';
import { ProfileView } from './views/student/ProfileView';
import { NotificationsView } from './views/student/NotificationsView';
import { MentorDashboardView } from './views/mentor/MentorDashboardView';
import { MentorStudentDetailView } from './views/mentor/MentorStudentDetailView';
import { AdminDashboardView } from './views/admin/AdminDashboardView';

const MainContent: React.FC = () => {
  const { role, activeStudentId, setActiveStudentId } = useApp();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [drilldownStudentId, setDrilldownStudentId] = useState<string | null>(null);

  const handleSelectStudentForMentor = (studentId: string) => {
    setDrilldownStudentId(studentId);
    setCurrentTab('mentor-student');
  };

  const handleBackToCaseload = () => {
    setDrilldownStudentId(null);
    setCurrentTab('mentor-caseload');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <Navbar currentTab={currentTab} setCurrentTab={setCurrentTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Student Views */}
        {role === 'student' && (
          <>
            {currentTab === 'dashboard' && <DashboardView onNavigate={setCurrentTab} />}
            {currentTab === 'risk' && (
              <RiskExplanationView onBack={() => setCurrentTab('dashboard')} />
            )}
            {currentTab === 'academics' && <AcademicsView />}
            {currentTab === 'attendance' && <AttendanceView />}
            {currentTab === 'assignments' && <AssignmentsView />}
            {currentTab === 'checkin' && <CheckinView />}
            {currentTab === 'profile' && <ProfileView />}
            {currentTab === 'notifications' && <NotificationsView />}
          </>
        )}

        {/* Mentor Views */}
        {role === 'mentor' && (
          <>
            {currentTab === 'mentor-caseload' && (
              <MentorDashboardView
                onSelectStudent={handleSelectStudentForMentor}
                onNavigateTab={setCurrentTab}
              />
            )}
            {currentTab === 'mentor-student' && (
              <MentorStudentDetailView
                studentId={drilldownStudentId || activeStudentId}
                onBack={handleBackToCaseload}
              />
            )}
            {currentTab === 'mentor-interventions' && (
              <MentorStudentDetailView
                studentId="s2"
                onBack={handleBackToCaseload}
              />
            )}
            {currentTab === 'mentor-checkins' && (
              <MentorStudentDetailView
                studentId="s2"
                onBack={handleBackToCaseload}
              />
            )}
            {currentTab === 'notifications' && <NotificationsView />}
          </>
        )}

        {/* Admin Views */}
        {role === 'admin' && (
          <>
            {(currentTab === 'admin-monitoring' ||
              currentTab === 'admin-drift' ||
              currentTab === 'admin-snapshots') && <AdminDashboardView />}
            {currentTab === 'notifications' && <NotificationsView />}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-[#00696B]">SEWS</span>
            <span>&bull; Student Early Warning and Intervention System</span>
          </div>
          <div className="text-center sm:text-right">
            Probabilistic early signal predictions &middot; Audited model provenance &middot; Human-in-the-loop governance
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <MainContent />
    </AppProvider>
  );
}
