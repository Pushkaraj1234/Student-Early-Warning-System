import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext.js';
import { Header } from './components/common/Header.js';
import { LoginPage } from './components/auth/LoginPage.js';
import { AdminDashboard } from './components/admin/AdminDashboard.js';
import { FacultyDashboard } from './components/faculty/FacultyDashboard.js';
import { StudentDirectory } from './components/faculty/StudentDirectory.js';
import { StudentProfileView } from './components/faculty/StudentProfileView.js';
import { InterventionsListView } from './components/admin/InterventionsListView.js';
import { ModelPerformanceView } from './components/admin/ModelPerformanceView.js';
import { AuditLogsView } from './components/admin/AuditLogsView.js';
import { SettingsView } from './components/admin/SettingsView.js';
import { StudentPortalView } from './components/student/StudentPortalView.js';
import { TestRunnerModal } from './components/common/TestRunnerModal.js';
import { DataImportModal } from './components/admin/DataImportModal.js';

const MainApp: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [selectedStudentId, setSelectedStudentId] = useState<string>('STU1001');

  // Modals
  const [isTestModalOpen, setIsTestModalOpen] = useState<boolean>(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);

  // If not logged in, show persona login screen
  if (!isAuthenticated || !user) {
    return (
      <LoginPage
        onLoginSuccess={() => {
          setActiveTab('dashboard');
        }}
      />
    );
  }

  const handleSelectStudent = (id: string) => {
    setSelectedStudentId(id);
    setActiveTab('student-profile');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Universal Institutional Header & Navigation */}
      <Header
        activeTab={activeTab}
        onTabChange={tab => setActiveTab(tab)}
        onOpenTestRunner={() => setIsTestModalOpen(true)}
        onOpenDataImport={() => setIsImportModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Dashboard Router */}
        {activeTab === 'dashboard' && (
          <>
            {user.role === 'STUDENT' ? (
              <StudentPortalView />
            ) : user.role === 'FACULTY' ? (
              <FacultyDashboard
                onSelectStudent={handleSelectStudent}
                onOpenTestModal={() => setIsTestModalOpen(true)}
              />
            ) : (
              <AdminDashboard
                onNavigateTab={tab => setActiveTab(tab)}
                onSelectStudent={handleSelectStudent}
                onOpenImport={() => setIsImportModalOpen(true)}
              />
            )}
          </>
        )}

        {/* Student Directory Tab */}
        {activeTab === 'students' && (
          <StudentDirectory
            onSelectStudent={handleSelectStudent}
            onOpenImport={() => setIsImportModalOpen(true)}
          />
        )}

        {/* Student Deep-Dive Profile & SHAP Explainability View */}
        {activeTab === 'student-profile' && (
          <StudentProfileView
            studentId={selectedStudentId}
            onBack={() => setActiveTab(user.role === 'STUDENT' ? 'student-portal' : 'students')}
          />
        )}

        {/* Mentorship Interventions Registry */}
        {activeTab === 'interventions' && (
          <InterventionsListView onSelectStudent={handleSelectStudent} />
        )}

        {/* ML Performance & Research Evaluation */}
        {activeTab === 'model-performance' && <ModelPerformanceView />}

        {/* Tamper-Evident Institutional Audit Trail */}
        {activeTab === 'audit-logs' && <AuditLogsView />}

        {/* System Threshold Configurations */}
        {activeTab === 'settings' && <SettingsView />}

        {/* Student Self-Service Portal Tab */}
        {activeTab === 'student-portal' && <StudentPortalView />}
      </main>

      {/* Institutional Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-700">SEWS</span> • Student Early Warning System & Retention Analytics
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span>Active Inference Engine: <strong className="text-indigo-600 font-mono">XGB-V2 (SHAP Attributed)</strong></span>
            <span>•</span>
            <button
              onClick={() => setIsTestModalOpen(true)}
              className="text-indigo-600 hover:text-indigo-800 font-semibold"
            >
              Run System Diagnostic
            </button>
          </div>
        </div>
      </footer>

      {/* Global Modals */}
      <TestRunnerModal
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
      />

      <DataImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={() => {
          setActiveTab('students');
        }}
      />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
