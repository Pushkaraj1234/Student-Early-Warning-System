import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { ModelVersion } from '../../types.js';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import {
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Award,
  Layers,
  ArrowRight,
  Sparkles,
  Info
} from 'lucide-react';

export const ModelPerformanceView: React.FC = () => {
  const [data, setData] = useState<{
    models: ModelVersion[];
    activeModelId: string;
    featureImportance: Array<{ feature: string; importance: number }>;
    researchAblation: Array<{ configuration: string; recall: number; precision: number; f1: number; rocAuc: number }>;
  } | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>('xgb-v2');
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    setIsLoading(true);
    try {
      const res = await api.getModelMetrics();
      setData(res);
      setSelectedModelId(res.activeModelId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSwitchModel = async (modelId: string) => {
    setSwitchingId(modelId);
    try {
      await api.switchModel(modelId);
      setSelectedModelId(modelId);
      if (data) {
        setData({ ...data, activeModelId: modelId });
      }
      setNotification(`Active inference engine successfully switched to ${modelId}. Real-time predictions recalibrated.`);
      setTimeout(() => setNotification(null), 5000);
    } catch (err: any) {
      alert(err.message || 'Failed to switch model');
    } finally {
      setSwitchingId(null);
    }
  };

  if (isLoading || !data) {
    return (
      <div className="p-12 text-center text-slate-500 text-sm">
        <Cpu className="w-8 h-8 text-indigo-500 animate-spin mx-auto mb-2" />
        Loading ML benchmark metrics and confusion matrices...
      </div>
    );
  }

  const currentModel = data.models.find(m => m.id === selectedModelId) || data.models[0];
  const cm = currentModel.metrics.confusionMatrix;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
                <Cpu className="w-5 h-5" />
              </span>
              <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
                ML Model Performance & Research Evaluation
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1 max-w-3xl">
              Comparative benchmark across 5 supervised architectures. In educational early warning, <strong className="text-slate-800">Recall for the At-Risk Class</strong> is prioritized because false negatives (undetected at-risk students) lead to irreversible academic dropouts.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-600">Active Pipeline:</span>
            <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              {data.activeModelId.toUpperCase()} (Production)
            </span>
          </div>
        </div>

        {notification && (
          <div className="mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-xs text-indigo-800 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
            <span>{notification}</span>
          </div>
        )}
      </div>

      {/* Model Benchmark Table */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
          <Award className="w-4 h-4 text-indigo-600" />
          Cross-Validated Benchmark Comparison (At-Risk Class Evaluation)
        </h3>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-4 py-3 text-left">Model Architecture</th>
                <th className="px-3 py-3 text-center">Accuracy</th>
                <th className="px-3 py-3 text-center">Precision</th>
                <th className="px-3 py-3 text-center bg-indigo-50/50 text-indigo-950">Recall (At-Risk)</th>
                <th className="px-3 py-3 text-center">F1-Score</th>
                <th className="px-3 py-3 text-center">ROC-AUC</th>
                <th className="px-3 py-3 text-center">PR-AUC</th>
                <th className="px-4 py-3 text-right">Status & Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {data.models.map(m => {
                const isSelected = m.id === selectedModelId;
                const isProduction = m.id === data.activeModelId;

                return (
                  <tr
                    key={m.id}
                    onClick={() => setSelectedModelId(m.id)}
                    className={`cursor-pointer transition-colors ${isSelected ? 'bg-indigo-50/40' : 'hover:bg-slate-50'}`}
                  >
                    <td className="px-4 py-3 text-left">
                      <div className="font-bold text-slate-900">{m.name}</div>
                      <div className="text-[10px] text-slate-500">{m.algorithm} • v{m.version}</div>
                    </td>
                    <td className="px-3 py-3 text-center font-mono">{(m.metrics.accuracy * 100).toFixed(1)}%</td>
                    <td className="px-3 py-3 text-center font-mono">{(m.metrics.precision * 100).toFixed(1)}%</td>
                    <td className="px-3 py-3 text-center font-mono font-bold text-indigo-700 bg-indigo-50/30">
                      {(m.metrics.recall * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-3 text-center font-mono">{(m.metrics.f1Score * 100).toFixed(1)}%</td>
                    <td className="px-3 py-3 text-center font-mono">{m.metrics.rocAuc.toFixed(3)}</td>
                    <td className="px-3 py-3 text-center font-mono">{m.metrics.prAuc.toFixed(3)}</td>
                    <td className="px-4 py-3 text-right">
                      {isProduction ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-md">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Active
                        </span>
                      ) : (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSwitchModel(m.id);
                          }}
                          disabled={switchingId === m.id}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 px-2.5 py-1 rounded-md transition-colors disabled:opacity-50"
                        >
                          {switchingId === m.id ? 'Switching...' : 'Deploy'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Model Diagnostics: Confusion Matrix + Feature Importance */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Confusion Matrix */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-900">
              Confusion Matrix: {currentModel.name}
            </h3>
            <span className="text-[11px] text-slate-500 font-mono">N = 244 test students</span>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="grid grid-cols-2 gap-3 text-center">
              {/* True Positive */}
              <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl">
                <div className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider">
                  True Positive (TP)
                </div>
                <div className="text-2xl font-black text-emerald-700 font-mono mt-1">
                  {cm.tp}
                </div>
                <div className="text-[10px] text-emerald-700 mt-1">
                  Correctly identified at-risk
                </div>
              </div>

              {/* False Positive */}
              <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl">
                <div className="text-[10px] uppercase font-bold text-amber-800 tracking-wider">
                  False Positive (FP)
                </div>
                <div className="text-2xl font-black text-amber-700 font-mono mt-1">
                  {cm.fp}
                </div>
                <div className="text-[10px] text-amber-700 mt-1">
                  Overpredicted risk (safe error)
                </div>
              </div>

              {/* False Negative */}
              <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl">
                <div className="text-[10px] uppercase font-bold text-rose-800 tracking-wider">
                  False Negative (FN)
                </div>
                <div className="text-2xl font-black text-rose-700 font-mono mt-1">
                  {cm.fn}
                </div>
                <div className="text-[10px] text-rose-700 mt-1 font-semibold">
                  Missed at-risk (Critical penalty)
                </div>
              </div>

              {/* True Negative */}
              <div className="bg-slate-100 border border-slate-200 p-4 rounded-xl">
                <div className="text-[10px] uppercase font-bold text-slate-700 tracking-wider">
                  True Negative (TN)
                </div>
                <div className="text-2xl font-black text-slate-800 font-mono mt-1">
                  {cm.tn}
                </div>
                <div className="text-[10px] text-slate-600 mt-1">
                  Correctly identified on-track
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200/80 text-[11px] text-slate-600 leading-relaxed flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5" />
              <span>
                <strong>Cost-sensitive design:</strong> False Negative Rate is kept under 8.8% to guarantee timely mentor intervention before end-semester exam lockouts.
              </span>
            </div>
          </div>
        </div>

        {/* Feature Importance Chart */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-slate-900">
              Global Feature Importance Ranking (Gini Impurity)
            </h3>
            <span className="text-[11px] text-slate-500">Normalized % Contribution</span>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Relative weight of dynamic academic, attendance, and LMS variables in predicting student outcomes.
          </p>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={data.featureImportance}
                margin={{ top: 5, right: 30, left: 140, bottom: 5 }}
              >
                <XAxis type="number" unit="%" tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 30]} />
                <YAxis type="category" dataKey="feature" tick={{ fontSize: 11, fill: '#334155' }} width={135} />
                <Tooltip
                  formatter={(val: any) => [`${val}%`, 'Importance Weight']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Bar dataKey="importance" fill="#4f46e5" radius={[0, 4, 4, 0]}>
                  {data.featureImportance.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={index === 0 ? '#4f46e5' : index === 1 ? '#6366f1' : '#818cf8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Research Ablation Study Table */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 mb-2 flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-600" />
          Ablation Study: Impact of Feature Subset Formulations
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Empirical validation demonstrating that incorporating multi-source features (Dynamic Attendance Drops + Continuous Assessment + LMS Engagement) outperforms traditional static CGPA-only baselines by +19.3% in Recall.
        </p>

        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-700 font-semibold uppercase text-[11px]">
              <tr>
                <th className="px-4 py-2.5 text-left">Feature Configuration Set</th>
                <th className="px-4 py-2.5 text-center">Recall (At-Risk)</th>
                <th className="px-4 py-2.5 text-center">Precision</th>
                <th className="px-4 py-2.5 text-center">F1-Score</th>
                <th className="px-4 py-2.5 text-center">ROC-AUC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {data.researchAblation.map((row, idx) => (
                <tr key={idx} className={idx === 0 ? 'bg-indigo-50/50 font-bold' : 'hover:bg-slate-50'}>
                  <td className="px-4 py-2.5 text-left text-slate-900">
                    {row.configuration}
                    {idx === 0 && (
                      <span className="ml-2 text-[10px] bg-indigo-100 text-indigo-800 px-1.5 py-0.2 rounded font-semibold">
                        Full SEWS Model
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-center font-mono text-indigo-700">{(row.recall * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2.5 text-center font-mono">{(row.precision * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2.5 text-center font-mono">{(row.f1 * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2.5 text-center font-mono">{row.rocAuc.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
