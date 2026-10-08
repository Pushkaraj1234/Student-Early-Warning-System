import React from 'react';
import { useApp } from '../../context/AppContext';
import { User, ShieldCheck, FileCheck, School, Lock } from 'lucide-react';

export const ProfileView: React.FC = () => {
  const { currentStudent } = useApp();

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
          Student Information & Governance
        </div>
        <h1 className="text-2xl font-extrabold text-slate-900 mt-1">Profile & Privacy Settings</h1>
      </div>

      {/* Profile Details */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
          <User className="w-5 h-5 mr-2 text-teal-600" />
          Student Record Information
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs text-slate-400 block">Full Name</span>
            <span className="font-semibold text-slate-800">{currentStudent.fullName}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs text-slate-400 block">Roll Number</span>
            <span className="font-mono font-semibold text-slate-800">{currentStudent.rollNumber}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs text-slate-400 block">Institutional Email</span>
            <span className="font-mono text-slate-700">{currentStudent.email}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs text-slate-400 block">Degree Programme</span>
            <span className="font-medium text-slate-800">{currentStudent.programme}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs text-slate-400 block">Department</span>
            <span className="text-slate-800">{currentStudent.department}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs text-slate-400 block">Admission Year & Semester</span>
            <span className="text-slate-800">
              {currentStudent.admissionYear} &middot; Semester {currentStudent.currentSemester}
            </span>
          </div>
        </div>
      </div>

      {/* AI Ethics, Fairness & Privacy Notice */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center">
          <ShieldCheck className="w-5 h-5 mr-2 text-teal-600" />
          SEWS AI Ethics & Data Privacy Guarantees
        </h2>

        <div className="text-xs sm:text-sm text-slate-600 space-y-3 leading-relaxed">
          <p>
            The Student Early Warning System adheres to strict academic ethics and transparency guidelines
            (outlined in <code className="text-teal-700 font-mono">docs/security/security-model.md</code> and{' '}
            <code className="text-teal-700 font-mono">docs/ml/fairness.md</code>):
          </p>

          <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-700">
            <li>
              <strong>No Automated Penalties:</strong> Early warning scores are strictly advisory for proactive support. No grades, academic disciplinary actions, or degree progression decisions can be made automatically by the system.
            </li>
            <li>
              <strong>Human-in-the-Loop Intervention:</strong> Model recommendations must always be reviewed, evaluated, and approved by a qualified human faculty mentor before any outreach.
            </li>
            <li>
              <strong>Audit Trail:</strong> Every prediction and intervention status change is permanently audited for fairness and calibration monitoring.
            </li>
            <li>
              <strong>Model Provenance & Privacy:</strong> Student metrics are analyzed using institutional cohort models calibrated against past academic sessions, without passing identifiable data to third-party public models.
            </li>
          </ul>

          <div className="mt-4 p-3.5 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-between text-xs text-teal-900">
            <div className="flex items-center space-x-2">
              <FileCheck className="w-4 h-4 text-teal-700" />
              <span>Privacy Notice Version: <strong>v1.0 (Consent Recorded)</strong></span>
            </div>
            <span className="font-semibold text-teal-800">Active</span>
          </div>
        </div>
      </div>
    </div>
  );
};
