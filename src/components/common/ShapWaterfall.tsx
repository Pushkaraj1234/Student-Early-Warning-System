import React from 'react';
import { SHAPContribution } from '../../types.js';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine
} from 'recharts';
import { ArrowUpRight, ArrowDownRight, Info, Sparkles } from 'lucide-react';

interface ShapWaterfallProps {
  contributions: SHAPContribution[];
  riskProbability: number;
  baselineProbability?: number;
  humanSummary?: string;
  className?: string;
}

export const ShapWaterfall: React.FC<ShapWaterfallProps> = ({
  contributions = [],
  riskProbability,
  baselineProbability = 25.0,
  humanSummary,
  className = ''
}) => {
  // Sort into risk increasing and protective
  const riskIncreasing = contributions.filter(c => c.direction === 'RISK_INCREASING');
  const protective = contributions.filter(c => c.direction === 'PROTECTIVE');

  // Prepare chart data (top factors)
  const chartData = contributions.slice(0, 8).map(c => ({
    name: c.featureLabel,
    value: c.shapValue,
    featureValue: c.featureValue,
    impact: c.relativeImpact,
    direction: c.direction,
    description: c.humanDescription
  }));

  return (
    <div id="shap-explainability-panel" className={`bg-white rounded-xl border border-slate-200 shadow-xs p-5 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              Explainable AI (SHAP) Attribution Analysis
            </h3>
            <span className="text-[11px] font-medium bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-md border border-indigo-100">
              TreeSHAP v2.1
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Marginal Shapley feature contributions indicating deviations from institutional reference baseline ({baselineProbability}%).
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1 bg-rose-50 border border-rose-100 px-2 py-1 rounded text-rose-700 font-medium">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500 inline-block"></span>
            <span>Elevates Risk (+Δ)</span>
          </div>
          <div className="flex items-center gap-1 bg-emerald-50 border border-emerald-100 px-2 py-1 rounded text-emerald-700 font-medium">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 inline-block"></span>
            <span>Protective Buffer (-Δ)</span>
          </div>
        </div>
      </div>

      {/* Model Interpretation Note - Responsible AI Requirement */}
      {humanSummary && (
        <div className="mb-5 bg-slate-50 border border-slate-200/80 rounded-lg p-3.5 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed text-slate-700">
            <span className="font-semibold text-slate-900">Decision-Support Synthesis: </span>
            {humanSummary}
            <div className="mt-1 text-[11px] text-slate-500 italic">
              Note: SHAP values represent statistical feature attributions identified by the model; they do not assert direct clinical or behavioural causality.
            </div>
          </div>
        </div>
      )}

      {/* Horizontal Bar Chart */}
      <div className="h-64 w-full mb-6">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={chartData}
            margin={{ top: 5, right: 30, left: 140, bottom: 5 }}
          >
            <XAxis
              type="number"
              unit=" pts"
              tick={{ fontSize: 11, fill: '#64748b' }}
              domain={['dataMin - 2', 'dataMax + 2']}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: '#334155', fontWeight: 500 }}
              width={130}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-slate-900 text-white p-2.5 rounded-lg shadow-lg text-xs max-w-xs border border-slate-800">
                      <div className="font-semibold text-slate-100">{data.name}</div>
                      <div className="text-slate-300 mt-0.5">Observed Value: <span className="font-mono text-white">{data.featureValue}</span></div>
                      <div className="text-slate-300">SHAP Impact: <span className={data.value > 0 ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>{data.value > 0 ? `+${data.value}` : data.value} % points</span></div>
                      <div className="mt-1 text-[11px] text-slate-400 border-t border-slate-800 pt-1 leading-snug">{data.description}</div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="3 3" />
            <Bar dataKey="value" radius={[4, 4, 4, 4]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.value >= 0 ? '#f43f5e' : '#10b981'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Structured Factor Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Risk Elevating Factors */}
        <div className="bg-rose-50/40 border border-rose-100 rounded-lg p-3.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-rose-900 mb-2.5 uppercase tracking-wider">
            <ArrowUpRight className="w-4 h-4 text-rose-600" />
            <span>Elevated Risk Contributors ({riskIncreasing.length})</span>
          </div>
          <div className="space-y-2">
            {riskIncreasing.length === 0 ? (
              <div className="text-xs text-slate-500 italic py-2">No significant risk-elevating factors detected.</div>
            ) : (
              riskIncreasing.slice(0, 4).map((f) => (
                <div key={f.featureKey} className="bg-white border border-rose-100/80 rounded-md p-2.5 text-xs shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">{f.featureLabel}</span>
                    <span className="font-mono font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                      +{f.shapValue}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
                    <span>Student Value: <strong className="text-slate-800">{f.featureValue}</strong></span>
                    <span className={`px-1.5 py-0.2 rounded font-semibold ${f.relativeImpact === 'HIGH' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}`}>
                      {f.relativeImpact} IMPACT
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                    {f.humanDescription}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Protective Factors */}
        <div className="bg-emerald-50/40 border border-emerald-100 rounded-lg p-3.5">
          <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-900 mb-2.5 uppercase tracking-wider">
            <ArrowDownRight className="w-4 h-4 text-emerald-600" />
            <span>Protective Buffer Factors ({protective.length})</span>
          </div>
          <div className="space-y-2">
            {protective.length === 0 ? (
              <div className="text-xs text-slate-500 italic py-2">No strong protective factors identified.</div>
            ) : (
              protective.slice(0, 4).map((f) => (
                <div key={f.featureKey} className="bg-white border border-emerald-100/80 rounded-md p-2.5 text-xs shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">{f.featureLabel}</span>
                    <span className="font-mono font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                      {f.shapValue}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
                    <span>Student Value: <strong className="text-slate-800">{f.featureValue}</strong></span>
                    <span className="px-1.5 py-0.2 rounded font-semibold bg-emerald-100 text-emerald-800">
                      STABILIZER
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                    {f.humanDescription}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
