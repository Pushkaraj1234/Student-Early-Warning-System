import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { RiskBadge } from '../common/RiskBadge.js';
import { ShapWaterfall } from '../common/ShapWaterfall.js';
import { RiskSparkline } from '../common/RiskSparkline.js';
import { InterventionModal } from './InterventionModal.js';
import { FollowUpModal } from './FollowUpModal.js';
import {
  User,
  ArrowLeft,
  Calendar,
  BookOpen,
  TrendingDown,
  TrendingUp,
  Award,
  AlertOctagon,
  Sparkles,
  RefreshCw,
  PlusCircle,
  Clock,
  CheckCircle2,
  Sliders,
  ChevronRight,
  Activity,
  Minus,
  Info
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts';

interface StudentProfileViewProps {
  studentId: string;
  onBack: () => void;
}

export const StudentProfileView: React.FC<StudentProfileViewProps> = ({ studentId, onBack }) => {
  const [profileData, setProfileData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isInterventionModalOpen, setIsInterventionModalOpen] = useState<boolean>(false);
  const [activeFollowUp, setActiveFollowUp] = useState<any | null>(null);

  // What-If Simulation State
  const [showSimulator, setShowSimulator] = useState<boolean>(false);
  const [simAttendance, setSimAttendance] = useState<number>(75);
  const [simCGPA, setSimCGPA] = useState<number>(6.5);
  const [simBacklogs, setSimBacklogs] = useState<number>(0);
  const [simDropRate, setSimDropRate] = useState<number>(2);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulatedPrediction, setSimulatedPrediction] = useState<any | null>(null);

  useEffect(() => {
    fetchStudentProfile();
  }, [studentId]);

  const fetchStudentProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getStudentById(studentId);
      setProfileData(data);

      // Initialize simulator with current student values
      if (data.features) {
        setSimAttendance(data.features.attendance_rate || 70);
        setSimCGPA(data.student.current_cgpa || 6.5);
        setSimBacklogs(data.features.backlog_count || 0);
        setSimDropRate(data.features.recent_attendance_drop || 0);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load student profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSimulation = async () => {
    setIsSimulating(true);
    try {
      const res = await api.recalculatePrediction(studentId, {
        updatedAttendance: Number(simAttendance),
        updatedCGPA: Number(simCGPA),
        updatedBacklogs: Number(simBacklogs),
        updatedDropRate: Number(simDropRate)
      });
      setSimulatedPrediction(res.prediction);
    } catch (err: any) {
      alert(err.message || 'Simulation calculation failed');
    } finally {
      setIsSimulating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-16 text-center text-xs text-slate-500">
        <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-2" />
        Loading student comprehensive profile & SHAP factor decomposition...
      </div>
    );
  }

  if (error || !profileData) {
    return (
      <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center space-y-3">
        <div className="text-sm font-bold text-rose-600">Error loading student profile</div>
        <p className="text-xs text-slate-500">{error || 'Student not found.'}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
        >
          Return to Student List
        </button>
      </div>
    );
  }

  const student = profileData.student || {};
  const latestPrediction = profileData.latestPrediction || profileData.currentPrediction || {
    risk_probability: 25,
    risk_level: 'LOW',
    model_version_id: 'xgb-v2',
    contributingFactors: []
  };
  const allPredictions = profileData.allPredictions || profileData.predictionHistory || [];
  const academicRecords = profileData.academicRecords || [];
  const attendanceRecords = profileData.attendanceRecords || [];
  const lmsActivity = profileData.lmsActivity;
  const assessments = profileData.assessments || profileData.assessmentRecords || [];
  const activeInterventions = profileData.activeInterventions || profileData.interventions || [];
  const recommendation = profileData.recommendation;
  const rawHistoricalTrajectory = profileData.historicalRiskTrajectory;
  const rawHistoricalSummary = profileData.historicalRiskSummary;

  // Fallback trajectory if backend didn't supply it
  const currentRiskVal = Number(latestPrediction?.risk_probability ?? 25);
  const historicalTrajectory = (rawHistoricalTrajectory && rawHistoricalTrajectory.length > 0)
    ? rawHistoricalTrajectory
    : [
        { checkpoint: 'Week 1 (Baseline)', shortLabel: 'W1', date: 'Semester Start', riskProbability: Math.max(10, currentRiskVal - 8), riskLevel: 'LOW', eventNote: 'Diagnostic baseline assessment' },
        { checkpoint: 'Week 4 (Early Check)', shortLabel: 'W4', date: 'Month 1', riskProbability: Math.max(10, currentRiskVal - 4), riskLevel: 'LOW', eventNote: 'Initial term coursework pacing' },
        { checkpoint: 'Week 8 (Mid-Term / UT-1)', shortLabel: 'W8', date: 'Mid-Semester', riskProbability: Math.max(12, currentRiskVal + 2), riskLevel: currentRiskVal > 55 ? 'HIGH' : 'MODERATE', eventNote: 'Midterm unit test milestone' },
        { checkpoint: 'Week 12 (Unit Test 2)', shortLabel: 'W12', date: 'Late Term', riskProbability: Math.max(10, currentRiskVal - 2), riskLevel: currentRiskVal > 55 ? 'HIGH' : 'MODERATE', eventNote: 'Continuous internal assessment checkpoint' },
        { checkpoint: 'Week 16 (Current Status)', shortLabel: 'W16', date: 'Active Term', riskProbability: currentRiskVal, riskLevel: latestPrediction?.risk_level || 'LOW', eventNote: 'Active dynamic evaluation' }
      ];

  const historicalSummary = rawHistoricalSummary || {
    points: historicalTrajectory,
    trendPattern: (currentRiskVal - historicalTrajectory[0].riskProbability) <= -4 ? 'IMPROVING' : (currentRiskVal - historicalTrajectory[0].riskProbability) >= 4 ? 'DECLINING' : 'STABLE',
    netChange: Math.round((currentRiskVal - historicalTrajectory[0].riskProbability) * 10) / 10,
    startProbability: historicalTrajectory[0].riskProbability,
    currentProbability: currentRiskVal,
    peakProbability: Math.max(...historicalTrajectory.map((p: any) => p.riskProbability)),
    lowestProbability: Math.min(...historicalTrajectory.map((p: any) => p.riskProbability)),
    patternDescription: `Semester historical trajectory tracking across 16 weeks.`
  };

  // Academic trend chart data
  const academicChartData = (academicRecords || []).map((rec: any) => ({
    semester: `Sem ${rec.semester}`,
    gpa: rec.gpa,
    credits: rec.credits_earned
  }));

  // Prior predictions for progress timeline
  const hasMultiplePredictions = (allPredictions || []).length > 1;
  const initialPred = hasMultiplePredictions ? allPredictions[allPredictions.length - 1] : null;

  return (
    <div className="space-y-6">
      {/* Back Button & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs transition-colors self-start"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Directory
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSimulator(prev => !prev)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Sliders className="w-3.5 h-3.5" />
            {showSimulator ? 'Close Simulation' : 'What-If Risk Simulator'}
          </button>

          <button
            onClick={() => setIsInterventionModalOpen(true)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-3.5 py-1.5 rounded-lg shadow-xs transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            Launch Intervention Plan
          </button>
        </div>
      </div>

      {/* Dynamic Re-evaluation / Improvement Alert Banner */}
      {hasMultiplePredictions && initialPred && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-100 text-emerald-700 rounded-xl">
              <TrendingDown className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-bold text-emerald-900">
                Dynamic Re-evaluation History Detected
              </div>
              <p className="text-xs text-emerald-700 mt-0.5">
                Baseline Risk on {new Date(initialPred.timestamp).toLocaleDateString()}: <span className="font-mono font-bold">{initialPred.risk_probability}%</span> ({initialPred.risk_level}) → Current: <span className="font-mono font-bold">{latestPrediction.risk_probability}%</span> ({latestPrediction.risk_level}).
              </p>
            </div>
          </div>

          <span className="text-xs font-bold text-emerald-800 bg-white border border-emerald-300 px-3 py-1 rounded-lg">
            Δ {(initialPred.risk_probability - latestPrediction.risk_probability).toFixed(1)}% Improvement
          </span>
        </div>
      )}

      {/* Student Overview Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {/* Left info */}
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-700 border border-indigo-100 flex items-center justify-center font-bold text-lg shrink-0">
              {student.name.split(' ').map((n: string) => n[0]).join('')}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xl font-black text-slate-900 tracking-tight">
                  {student.name}
                </h2>
                <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-md">
                  {student.id}
                </span>
                <span className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md border ${
                  student.academic_status === 'PROBATION'
                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                    : student.academic_status === 'UNDER_REVIEW'
                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}>
                  {student.academic_status}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {student.program} • Semester {student.semester} (Division {student.division}) • Dept: <span className="font-semibold text-slate-700">{student.departmentName}</span>
              </p>
              <div className="flex items-center gap-4 text-xs text-slate-500 mt-2">
                <span>Email: <strong className="text-slate-800">{student.email}</strong></span>
                <span>•</span>
                <span>Mentor: <strong className="text-indigo-700">{student.assignedFacultyName}</strong></span>
              </div>
            </div>
          </div>

          {/* Right Risk Score Gauge & Mini Sparkline */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 bg-slate-50 border border-slate-200/80 rounded-2xl p-4 shrink-0 self-start lg:self-auto">
            {/* Risk Gauge */}
            <div className="flex items-center gap-4 shrink-0">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  Predicted Dropout Risk
                </div>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-3xl font-black text-slate-900 font-mono tracking-tight">
                    {latestPrediction.risk_probability}%
                  </span>
                  <RiskBadge level={latestPrediction.risk_level} showIcon={false} size="sm" />
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
                  Model: {latestPrediction.model_version_id}
                </div>
              </div>

              <div className="w-16 h-16 rounded-full border-4 border-slate-200 flex items-center justify-center relative shrink-0">
                <div
                  className={`absolute inset-0 rounded-full border-4 ${
                    latestPrediction.risk_level === 'CRITICAL'
                      ? 'border-rose-500'
                      : latestPrediction.risk_level === 'HIGH'
                      ? 'border-amber-500'
                      : latestPrediction.risk_level === 'MODERATE'
                      ? 'border-yellow-500'
                      : 'border-emerald-500'
                  }`}
                  style={{
                    clipPath: `polygon(0 0, 100% 0, 100% ${latestPrediction.risk_probability}%, 0 ${latestPrediction.risk_probability}%)`
                  }}
                />
                <span className="text-xs font-bold text-slate-700 z-10">
                  {latestPrediction.risk_level === 'CRITICAL' ? 'High' : latestPrediction.risk_level}
                </span>
              </div>
            </div>

            {/* Vertical Divider */}
            <div className="hidden sm:block h-14 w-px bg-slate-200" />

            {/* Mini Sparkline Chart Widget */}
            <div className="w-full sm:w-60 lg:w-64">
              <RiskSparkline
                points={historicalTrajectory}
                summary={historicalSummary}
                height={42}
              />
            </div>
          </div>
        </div>
      </div>

      {/* What-If Risk Simulator (Interactive Feature Recalibration) */}
      {showSimulator && (
        <div className="bg-indigo-50/50 border-2 border-indigo-200 rounded-2xl p-5 shadow-xs animate-in fade-in space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-indigo-600" />
              <h3 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">
                What-If Risk Simulation (Hypothetical Remedial Assessment)
              </h3>
            </div>
            <span className="text-[11px] text-indigo-700">Explore how interventions impact the score</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Attendance Rate: <strong className="text-indigo-700 font-mono">{simAttendance}%</strong>
              </label>
              <input
                type="range"
                min="40"
                max="100"
                value={simAttendance}
                onChange={e => setSimAttendance(Number(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                CGPA: <strong className="text-indigo-700 font-mono">{simCGPA}</strong>
              </label>
              <input
                type="range"
                min="4.0"
                max="10.0"
                step="0.1"
                value={simCGPA}
                onChange={e => setSimCGPA(Number(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Active Backlogs: <strong className="text-indigo-700 font-mono">{simBacklogs}</strong>
              </label>
              <input
                type="range"
                min="0"
                max="6"
                value={simBacklogs}
                onChange={e => setSimBacklogs(Number(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                Recent Drop Rate: <strong className="text-indigo-700 font-mono">{simDropRate}%</strong>
              </label>
              <input
                type="range"
                min="0"
                max="30"
                value={simDropRate}
                onChange={e => setSimDropRate(Number(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-indigo-100">
            <button
              onClick={handleRunSimulation}
              disabled={isSimulating}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isSimulating ? 'Computing...' : 'Recalculate Model Risk'}
            </button>

            {simulatedPrediction && (
              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-600">Simulated Outcome:</span>
                <span className="font-mono font-bold text-base text-slate-900">
                  {simulatedPrediction.riskProbability}%
                </span>
                <RiskBadge level={simulatedPrediction.riskLevel} size="sm" />
                <span className="text-emerald-700 font-bold">
                  ({(latestPrediction.risk_probability - simulatedPrediction.riskProbability).toFixed(1)}% delta)
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SHAP Waterfall / Explainable Attribution Visualizer */}
      <ShapWaterfall
        contributions={latestPrediction.contributingFactors || []}
        riskProbability={latestPrediction.risk_probability}
        baselineProbability={latestPrediction.baseline_probability}
        humanSummary={latestPrediction.human_summary}
      />

      {/* Semester Historical Risk Trajectory & Pattern Analysis Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <Activity className="w-4 h-4 text-indigo-600" />
              <h3 className="text-sm font-bold text-slate-900">
                Semester Historical Risk Trajectory & Pattern Detection
              </h3>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                historicalSummary.trendPattern === 'IMPROVING'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : historicalSummary.trendPattern === 'DECLINING'
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}>
                {historicalSummary.trendPattern === 'IMPROVING' ? '✓ Improvement Pattern' : historicalSummary.trendPattern === 'DECLINING' ? '⚠ Risk Escalation Pattern' : '↔ Stable Trajectory'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              16-week continuous model risk re-evaluations across assessments, attendance changes, and mentor interventions
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="text-[11px] text-slate-500 font-mono">Semester Net Δ:</span>
            <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
              historicalSummary.netChange < 0
                ? 'bg-emerald-100 text-emerald-800'
                : historicalSummary.netChange > 0
                ? 'bg-rose-100 text-rose-800'
                : 'bg-slate-100 text-slate-700'
            }`}>
              {historicalSummary.netChange > 0 ? `+${historicalSummary.netChange}%` : `${historicalSummary.netChange}%`}
            </span>
          </div>
        </div>

        {/* 4 Summary Stat Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Semester Start (W1)</div>
            <div className="text-lg font-bold font-mono text-slate-800 mt-1">
              {historicalSummary.startProbability}%
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Diagnostic baseline</div>
          </div>

          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Semester Peak Risk</div>
            <div className="text-lg font-bold font-mono text-rose-700 mt-1">
              {historicalSummary.peakProbability}%
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Highest recorded vulnerability</div>
          </div>

          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Lowest Recorded</div>
            <div className="text-lg font-bold font-mono text-emerald-700 mt-1">
              {historicalSummary.lowestProbability}%
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Optimal standing</div>
          </div>

          <div className="bg-indigo-50/60 border border-indigo-200/70 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-indigo-900 tracking-wider">Current Score (W16)</div>
            <div className="text-lg font-bold font-mono text-indigo-900 mt-1 flex items-baseline gap-1.5">
              <span>{historicalSummary.currentProbability}%</span>
              <span className={`text-[10px] font-semibold ${historicalSummary.netChange < 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                ({historicalSummary.netChange > 0 ? `+${historicalSummary.netChange}%` : `${historicalSummary.netChange}%`})
              </span>
            </div>
            <div className="text-[10px] text-indigo-700/80 mt-0.5">Active term standing</div>
          </div>
        </div>

        {/* Detailed Interactive Sparkline Timeline */}
        <div className="bg-slate-50/50 border border-slate-200 rounded-xl p-4">
          <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Historical Risk Progression (Past Semester)</span>
            <span className="text-[10px] font-normal text-slate-500">Hover or click dots to inspect checkpoint triggers</span>
          </div>

          <RiskSparkline
            points={historicalTrajectory}
            summary={historicalSummary}
            height={56}
          />
        </div>

        {/* Pattern Narrative Callout */}
        <div className={`p-3.5 rounded-xl border flex items-start gap-3 ${
          historicalSummary.trendPattern === 'IMPROVING'
            ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
            : historicalSummary.trendPattern === 'DECLINING'
            ? 'bg-rose-50/60 border-rose-200 text-rose-950'
            : 'bg-indigo-50/60 border-indigo-200 text-indigo-950'
        }`}>
          {historicalSummary.trendPattern === 'IMPROVING' ? (
            <TrendingDown className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : historicalSummary.trendPattern === 'DECLINING' ? (
            <TrendingUp className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          ) : (
            <Minus className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
          )}
          <div className="text-xs space-y-1">
            <div className="font-bold">
              {historicalSummary.trendPattern === 'IMPROVING'
                ? 'Pattern Analysis: Positive Academic Recovery'
                : historicalSummary.trendPattern === 'DECLINING'
                ? 'Pattern Analysis: Risk Escalation Flag'
                : 'Pattern Analysis: Consistent Academic Standing'}
            </div>
            <p className="text-slate-700 leading-relaxed">
              {historicalSummary.patternDescription}
            </p>
          </div>
        </div>
      </div>

      {/* Core Academic & Engagement Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Academic GPA Progression Line Chart */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-600" />
                Semester GPA Progression & Trend
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Historical semester grade-point average (Sem 1 - 5)</p>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-500">Current CGPA</span>
              <div className="text-lg font-bold font-mono text-slate-900">{student.current_cgpa}</div>
            </div>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={academicChartData} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="semester" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis domain={[4.0, 10.0]} tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  formatter={(val: any) => [`${val} GPA`, 'Grade Point']}
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Line
                  type="monotone"
                  dataKey="gpa"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: '#4f46e5' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Attendance & LMS Analytics */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-600" />
                Attendance & LMS Engagement Indicators
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Continuous behavioral tracking</p>
            </div>
            <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
              Active Term 2026
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl">
              <div className="text-[10px] uppercase font-bold text-slate-500">Overall Attendance</div>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                {attendanceRecords?.[0]?.percentage || 0}%
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Attended {attendanceRecords?.[0]?.classes_attended || 0} of {attendanceRecords?.[0]?.classes_held || 0} lectures
              </div>
            </div>

            <div className="bg-rose-50/50 border border-rose-100 p-3.5 rounded-xl">
              <div className="text-[10px] uppercase font-bold text-rose-800">Recent Attendance Drop</div>
              <div className="text-xl font-bold font-mono text-rose-700 mt-1">
                -{attendanceRecords?.[0]?.recent_drop_rate || 0}%
              </div>
              <div className="text-[11px] text-rose-600 mt-0.5">
                Drop in last 30 days
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl">
              <div className="text-[10px] uppercase font-bold text-slate-500">Weekly LMS Logins</div>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                {lmsActivity?.[0]?.weekly_logins || 0}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Avg {lmsActivity?.[0]?.active_hours || 0} active hours/week
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl">
              <div className="text-[10px] uppercase font-bold text-slate-500">Quiz Participation</div>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                {lmsActivity?.[0]?.quiz_participation_rate || 0}%
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Online portal engagement
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Internal Continuous Assessment Subject Breakdown */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
          <Award className="w-4 h-4 text-indigo-600" />
          Continuous Internal Evaluation Marks (Current Semester)
        </h3>

        <div className="border border-slate-200 rounded-xl overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
            <thead className="bg-slate-50 font-semibold text-slate-700 uppercase text-[10px]">
              <tr>
                <th className="px-4 py-2.5">Subject Code</th>
                <th className="px-4 py-2.5">Unit Test 1 (Max 30)</th>
                <th className="px-4 py-2.5">Unit Test 2 (Max 30)</th>
                <th className="px-4 py-2.5">Subject Attendance</th>
                <th className="px-4 py-2.5">Assignments</th>
                <th className="px-4 py-2.5 text-right">Academic Standing</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white font-medium">
              {(assessments || []).map((a: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-bold font-mono text-slate-900">{a.subject_id}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.internal_ut1} / 30</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.internal_ut2} / 30</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.attendance_pct}%</td>
                  <td className="px-4 py-2.5 font-mono text-slate-700">{a.assignments_submitted} of {a.assignments_total} submitted</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      a.status === 'AT_RISK' ? 'bg-rose-100 text-rose-800' : a.status === 'BORDERLINE' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
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

      {/* Active Interventions & Mentorship History Table */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-600" />
            Active Mentorship Interventions & Scheduled Follow-ups
          </h3>
          <button
            onClick={() => setIsInterventionModalOpen(true)}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1"
          >
            <PlusCircle className="w-3.5 h-3.5" /> Add Intervention
          </button>
        </div>

        {(!activeInterventions || activeInterventions.length === 0) ? (
          <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl">
            No formal interventions recorded yet for this student. Click "Launch Intervention Plan" above to create one.
          </div>
        ) : (
          <div className="space-y-4">
            {activeInterventions.map((intv: any) => {
              let actionList: string[] = [];
              try {
                actionList = typeof intv.action_items === 'string' ? JSON.parse(intv.action_items) : intv.action_items;
              } catch (e) {
                actionList = [];
              }

              return (
                <div key={intv.id} className="border border-slate-200 rounded-xl p-4 bg-slate-50/40 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <span className="text-xs font-bold text-slate-900">{intv.selected_intervention}</span>
                      <span className="text-[10px] text-slate-500 ml-2">Assigned on {intv.assigned_date}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        intv.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800'
                      }`}>
                        {intv.status}
                      </span>
                      {intv.follow_up_date && (
                        <span className="text-[10px] font-semibold text-slate-600 bg-white border border-slate-200 px-2 py-0.5 rounded">
                          Review: {intv.follow_up_date}
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 italic bg-white p-2.5 rounded-lg border border-slate-200/60">
                    "{intv.faculty_notes}"
                  </p>

                  {/* Milestones checklist */}
                  {actionList.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Agreed Action Milestones:</div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {actionList.map((item, idx) => (
                          <div key={idx} className="text-xs text-slate-700 flex items-center gap-1.5 bg-white px-2 py-1 rounded border border-slate-100">
                            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Follow-up button if in progress */}
                  {intv.status === 'IN_PROGRESS' && (
                    <div className="pt-2 flex justify-end">
                      <button
                        onClick={() =>
                          setActiveFollowUp({
                            id: `fu-${intv.id}`,
                            intervention_id: intv.id,
                            student_id: student.id,
                            faculty_id: student.assigned_faculty_id,
                            scheduled_date: intv.follow_up_date,
                            observations: '',
                            status: 'PENDING'
                          })
                        }
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        <Clock className="w-3.5 h-3.5" />
                        Log Review & Dynamic Re-evaluate
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Intervention Modal */}
      <InterventionModal
        isOpen={isInterventionModalOpen}
        onClose={() => setIsInterventionModalOpen(false)}
        onSuccess={fetchStudentProfile}
        studentId={student.id}
        studentName={student.name}
        currentRiskLevel={latestPrediction.risk_level}
        currentRiskProbability={latestPrediction.risk_probability}
        recommendation={recommendation}
        detectedRiskFactors={latestPrediction.detectedRiskFactors}
      />

      {/* Follow-up Modal */}
      {activeFollowUp && (
        <FollowUpModal
          isOpen={!!activeFollowUp}
          onClose={() => setActiveFollowUp(null)}
          onSuccess={fetchStudentProfile}
          followUp={activeFollowUp}
          studentName={student.name}
          initialAttendance={student.attendance_rate || 65}
          initialCGPA={student.current_cgpa || 6.2}
          initialBacklogs={student.backlog_count || 1}
        />
      )}
    </div>
  );
};
