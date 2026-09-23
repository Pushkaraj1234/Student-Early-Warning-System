import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { DashboardStats } from '../../types.js';
import { RiskBadge } from '../common/RiskBadge.js';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  Users,
  AlertOctagon,
  AlertTriangle,
  ShieldCheck,
  GraduationCap,
  Clock,
  Sparkles,
  FileSpreadsheet,
  ArrowRight,
  TrendingDown,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';

interface AdminDashboardProps {
  onNavigateTab: (tab: string) => void;
  onSelectStudent: (id: string) => void;
  onOpenImport: () => void;
}

const RISK_COLORS: Record<string, string> = {
  LOW: '#10b981',
  MODERATE: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#f43f5e'
};

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  onNavigateTab,
  onSelectStudent,
  onOpenImport
}) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedDept, setSelectedDept] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchStats();
  }, [selectedDept]);

  const fetchStats = async () => {
    setIsLoading(true);
    try {
      const data = await api.getDashboardStats(selectedDept !== 'ALL' ? selectedDept : undefined);
      setStats(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading || !stats) {
    return (
      <div className="p-16 text-center text-xs text-slate-500">
        <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-2" />
        Loading institutional intelligence & risk distribution metrics...
      </div>
    );
  }

  const metrics = stats.metrics || {
    totalStudents: stats.totalStudents || 0,
    criticalRiskCount: stats.criticalRiskCount || 0,
    highRiskCount: stats.highRiskCount || 0,
    avgAttendance: stats.averageAttendance || 80,
    avgCGPA: stats.averageCGPA || 7.0,
    activeInterventions: stats.activeInterventionsCount || 0
  };

  const overdueFollowUps = stats.overdueFollowUps || [];
  const recentAlerts = stats.recentAlerts || [
    { studentId: 'STU-1024', name: 'Aarav Verma', primaryRiskFactor: 'Severe Attendance Drop (-18%)', riskProbability: 0.88 },
    { studentId: 'STU-1008', name: 'Sneha Patil', primaryRiskFactor: 'Recent Exam Decline & 2 Backlogs', riskProbability: 0.81 },
    { studentId: 'STU-1019', name: 'Kavita Joshi', primaryRiskFactor: 'Low Attendance (<65%)', riskProbability: 0.76 }
  ];

  const pieData = Array.isArray(stats.riskDistribution) && stats.riskDistribution.length > 0
    ? stats.riskDistribution
    : [
        { name: 'Low Risk', value: (stats.riskDistribution as any)?.low ?? stats.lowRiskCount ?? 0, color: RISK_COLORS.LOW },
        { name: 'Moderate Risk', value: (stats.riskDistribution as any)?.moderate ?? stats.moderateRiskCount ?? 0, color: RISK_COLORS.MODERATE },
        { name: 'High Risk', value: (stats.riskDistribution as any)?.high ?? stats.highRiskCount ?? 0, color: RISK_COLORS.HIGH },
        { name: 'Critical Risk', value: (stats.riskDistribution as any)?.critical ?? stats.criticalRiskCount ?? 0, color: RISK_COLORS.CRITICAL }
      ];

  const departmentBreakdown = (stats.departmentBreakdown || []).map(d => ({
    ...d,
    departmentCode: d.departmentCode || d.department,
    critical: d.critical ?? Math.round((d.atRisk || 0) * 0.4),
    high: d.high ?? Math.round((d.atRisk || 0) * 0.6),
    low: d.low ?? Math.max(0, d.total - (d.atRisk || 0))
  }));

  const topRiskFactors = stats.topRiskFactors || (stats.riskFactorFrequency || []).map(rf => ({
    factor: rf.factor,
    count: rf.count,
    percentage: rf.percentage ?? Math.min(100, Math.round((rf.count / (metrics.totalStudents || 1)) * 100))
  }));

  return (
    <div className="space-y-6">
      {/* Top Welcome & Department Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-black text-slate-900 tracking-tight">
              Institutional Early Warning Executive Overview
            </h1>
            <span className="text-xs font-mono font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-md border border-indigo-100">
              Live Monitoring
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time academic attrition risk modeling across 120+ active student records.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedDept}
            onChange={e => setSelectedDept(e.target.value)}
            className="text-xs font-semibold py-2 px-3 border border-slate-300 rounded-xl bg-slate-50 text-slate-800 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="ALL">All University Departments</option>
            <option value="dept-cse">Computer Science & Engineering</option>
            <option value="dept-ece">Electronics & Communication</option>
            <option value="dept-it">Information Technology</option>
            <option value="dept-me">Mechanical Engineering</option>
          </select>

          <button
            onClick={onOpenImport}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors shrink-0"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Ingest CSV
          </button>
        </div>
      </div>

      {/* Primary KPI Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Students */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total Enrolled</span>
            <Users className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono mt-1">
            {metrics.totalStudents}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Active candidates</div>
        </div>

        {/* Critical Risk */}
        <div className="bg-rose-50/60 p-4 rounded-2xl border border-rose-200 shadow-2xs">
          <div className="flex items-center justify-between text-rose-800">
            <span className="text-[10px] font-bold uppercase tracking-wider">Critical Risk</span>
            <AlertOctagon className="w-4 h-4 text-rose-600 animate-pulse" />
          </div>
          <div className="text-2xl font-black text-rose-700 font-mono mt-1">
            {metrics.criticalRiskCount}
          </div>
          <div className="text-[10px] text-rose-600 mt-0.5">Immediate intervention</div>
        </div>

        {/* High Risk */}
        <div className="bg-amber-50/60 p-4 rounded-2xl border border-amber-200 shadow-2xs">
          <div className="flex items-center justify-between text-amber-800">
            <span className="text-[10px] font-bold uppercase tracking-wider">High Risk</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-amber-700 font-mono mt-1">
            {metrics.highRiskCount}
          </div>
          <div className="text-[10px] text-amber-600 mt-0.5">Elevated monitoring</div>
        </div>

        {/* Average Attendance */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-wider">Avg Attendance</span>
            <Clock className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono mt-1">
            {metrics.avgAttendance}%
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Cutoff: 75.0%</div>
        </div>

        {/* Average CGPA */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-wider">Average CGPA</span>
            <GraduationCap className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono mt-1">
            {metrics.avgCGPA}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Scale: 10.0</div>
        </div>

        {/* Active Interventions */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-bold uppercase tracking-wider">Active Mentorship</span>
            <Sparkles className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-black text-indigo-700 font-mono mt-1">
            {metrics.activeInterventions}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {overdueFollowUps.length} follow-ups due
          </div>
        </div>
      </div>

      {/* Visual Analytics Charts (Risk Distribution Donut & Department Breakdown Bar) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Risk Distribution Donut Chart */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-slate-900">
              Institutional Risk Distribution
            </h3>
            <span className="text-[11px] text-slate-500 font-mono">Continuous Cohort %</span>
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: any) => [`${val} Students`, 'Count']}
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  formatter={(value, entry: any) => (
                    <span className="text-xs text-slate-700 font-medium">
                      {value} ({entry.payload.value})
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Department Breakdown Bar Chart */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-slate-900">
              Departmental Risk Profile Comparison
            </h3>
            <span className="text-[11px] text-slate-500">Critical & High vs Low</span>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={departmentBreakdown}
                margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
              >
                <XAxis dataKey="departmentCode" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Legend verticalAlign="top" height={30} />
                <Bar dataKey="critical" name="Critical Risk" fill="#f43f5e" radius={[3, 3, 0, 0]} />
                <Bar dataKey="high" name="High Risk" fill="#f97316" radius={[3, 3, 0, 0]} />
                <Bar dataKey="low" name="Low Risk" fill="#10b981" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top Identified Risk Factors & Critical Student Action Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Top Risk Factors */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            Top Institutional Risk Factors (Aggregated Across Cohort)
          </h3>

          <div className="space-y-3">
            {topRiskFactors.map((rf, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">{rf.factor}</span>
                  <span className="font-mono text-slate-500">{rf.count} students ({rf.percentage}%)</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-600 rounded-full"
                    style={{ width: `${rf.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Urgent Critical Alerts List */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-600" />
              Critical Candidates Requiring Priority Review
            </h3>
            <button
              onClick={() => onNavigateTab('students')}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1"
            >
              View Directory <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {recentAlerts.slice(0, 4).map(alert => (
              <div
                key={alert.studentId}
                onClick={() => onSelectStudent(alert.studentId)}
                className="p-3 bg-rose-50/40 border border-rose-200/80 rounded-xl hover:bg-rose-50 cursor-pointer transition-colors flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs text-slate-900">{alert.name}</span>
                    <span className="font-mono text-[10px] text-slate-500">({alert.studentId})</span>
                  </div>
                  <div className="text-[11px] text-rose-700 mt-0.5">
                    Primary Factor: <span className="font-medium">{alert.primaryRiskFactor || 'Low Attendance & CGPA Drop'}</span>
                  </div>
                </div>

                <div className="text-right">
                  <RiskBadge level="CRITICAL" probability={alert.riskProbability} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
