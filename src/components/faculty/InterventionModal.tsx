import React, { useState } from 'react';
import { api } from '../../services/api.js';
import { InterventionRecommendation, RiskLevel } from '../../types.js';
import {
  Calendar,
  Sparkles,
  CheckSquare,
  Plus,
  Trash2,
  X,
  FileText,
  Clock,
  Send
} from 'lucide-react';

interface InterventionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  studentId: string;
  studentName: string;
  currentRiskLevel: RiskLevel;
  currentRiskProbability: number;
  recommendation?: InterventionRecommendation | null;
  detectedRiskFactors?: string[];
}

const INTERVENTION_TYPES = [
  'Remedial Coaching Clinic & Subject Tutoring',
  'Attendance Recovery Program & Weekly Attendance Tracking',
  'Academic Peer Mentorship & Study Group Pairing',
  'Faculty Mentor 1-on-1 Academic Counselling',
  'Multidisciplinary Academic Support Review',
  'Continuous Assessment & Assignment Catch-Up Plan'
];

export const InterventionModal: React.FC<InterventionModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  studentId,
  studentName,
  currentRiskLevel,
  currentRiskProbability,
  recommendation,
  detectedRiskFactors = []
}) => {
  const [selectedType, setSelectedType] = useState<string>(
    recommendation?.title || INTERVENTION_TYPES[0]
  );
  const [facultyNotes, setFacultyNotes] = useState<string>('');
  const [actionItems, setActionItems] = useState<string[]>(
    recommendation?.suggestedActionItems || [
      'Attend bi-weekly remedial clinic for lower-scoring subjects',
      'Maintain weekly attendance check-in with faculty advisor',
      'Submit pending tutorial assignments before mid-term cutoff'
    ]
  );
  const [newItem, setNewItem] = useState<string>('');
  const [followUpDate, setFollowUpDate] = useState<string>(
    new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0] // 2 weeks out
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddActionItem = () => {
    if (!newItem.trim()) return;
    setActionItems([...actionItems, newItem.trim()]);
    setNewItem('');
  };

  const handleRemoveItem = (index: number) => {
    setActionItems(actionItems.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (actionItems.length === 0) {
      setError('Please provide at least one actionable milestone for the student.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.createIntervention({
        studentId,
        riskLevel: currentRiskLevel,
        riskProbability: currentRiskProbability,
        detectedRiskFactors,
        aiRecommendation: recommendation
          ? `${recommendation.title}: ${recommendation.rationale}`
          : selectedType,
        selectedIntervention: selectedType,
        facultyNotes,
        actionItems,
        assignedDate: new Date().toISOString().split('T')[0],
        followUpDate,
        status: 'IN_PROGRESS'
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create intervention plan');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div id="create-intervention-modal" className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full overflow-hidden transition-all flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-indigo-900 text-white p-5 flex items-center justify-between border-b border-indigo-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-700/50 text-indigo-300 rounded-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Design Supportive Intervention Plan
              </h2>
              <p className="text-xs text-indigo-200">
                Candidate: <strong className="text-white">{studentName}</strong> ({studentId}) • Current Risk: {currentRiskProbability}% ({currentRiskLevel})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-indigo-300 hover:text-white rounded-lg hover:bg-indigo-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800">
              {error}
            </div>
          )}

          {/* AI Recommendation Banner */}
          {recommendation && (
            <div className="bg-indigo-50/70 border border-indigo-200/80 rounded-xl p-4">
              <div className="flex items-center gap-2 text-xs font-bold text-indigo-900 mb-1">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <span>AI Recommendation Engine: {recommendation.title}</span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.2 rounded-md bg-indigo-200 text-indigo-900 ml-auto">
                  {recommendation.urgency} URGENCY
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed">
                {recommendation.rationale}
              </p>
            </div>
          )}

          <form id="intervention-form" onSubmit={handleSubmit} className="space-y-4">
            {/* Intervention Type */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1 uppercase tracking-wider">
                Intervention Strategy
              </label>
              <select
                value={selectedType}
                onChange={e => setSelectedType(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-900 font-medium focus:ring-2 focus:ring-indigo-500"
              >
                {INTERVENTION_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Mentor Counselling Notes */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1 uppercase tracking-wider">
                Mentor Counselling Notes & Agreed Goals
              </label>
              <textarea
                rows={3}
                required
                value={facultyNotes}
                onChange={e => setFacultyNotes(e.target.value)}
                placeholder="Detail the discussion points with the student, underlying difficulties identified, and agreed commitments..."
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-900 focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Action Items */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1 uppercase tracking-wider flex items-center justify-between">
                <span>Actionable Milestones for Student</span>
                <span className="text-[11px] text-slate-400 font-normal">({actionItems.length} Milestones)</span>
              </label>
              
              <div className="space-y-2 mb-2">
                {actionItems.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-2 p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs">
                    <span className="text-slate-800 flex items-center gap-2">
                      <CheckSquare className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                      {item}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(idx)}
                      className="text-slate-400 hover:text-rose-600 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={newItem}
                  onChange={e => setNewItem(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddActionItem();
                    }
                  }}
                  placeholder="Add custom milestone (e.g. Attend Monday lab remedial)..."
                  className="flex-1 text-xs border border-slate-300 rounded-lg p-2 text-slate-900"
                />
                <button
                  type="button"
                  onClick={handleAddActionItem}
                  className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </div>
            </div>

            {/* Follow-up scheduled date */}
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1 uppercase tracking-wider">
                Scheduled Follow-up Review Date
              </label>
              <div className="relative">
                <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="date"
                  required
                  value={followUpDate}
                  onChange={e => setFollowUpDate(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg text-slate-900"
                />
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">
                SEWS will automatically flag follow-up reviews due or overdue on the faculty dashboard.
              </span>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-3.5 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="intervention-form"
            disabled={isSubmitting}
            className="inline-flex items-center gap-1.5 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {isSubmitting ? 'Saving Plan...' : 'Authorize & Launch Intervention'}
          </button>
        </div>
      </div>
    </div>
  );
};
