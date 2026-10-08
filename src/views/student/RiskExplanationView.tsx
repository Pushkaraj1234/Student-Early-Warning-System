import React from 'react';
import { useApp } from '../../context/AppContext';
import { RiskBadge, TrajectoryBadge, ProvenanceBadge } from '../../components/RiskBadge';
import {
  formatDate,
  formatFeatureValue,
  getFeatureDisplayTitle,
  formatDirectionText,
} from '../../utils/formatting';
import {
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Info,
  Calendar,
  Layers,
  ArrowLeft,
  ShieldAlert,
} from 'lucide-react';

interface RiskExplanationViewProps {
  onBack: () => void;
}

export const RiskExplanationView: React.FC<RiskExplanationViewProps> = ({ onBack }) => {
  const { currentStudent, latestPrediction, predictions, riskFactors } = useApp();

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Back button */}
      <div>
        <button
          onClick={onBack}
          className="inline-flex items-center text-sm font-semibold text-teal-700 hover:text-teal-900 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Dashboard
        </button>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-teal-700 font-mono">
              Model Explainability &middot; SHAP Analysis
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
              Risk Signal Explanation
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              {currentStudent.fullName} ({currentStudent.rollNumber}) &middot; Semester {currentStudent.currentSemester}
            </p>
          </div>

          {latestPrediction && (
            <div className="flex flex-col sm:items-end">
              <div className="flex items-center space-x-2">
                <RiskBadge level={latestPrediction.riskLevel} size="lg" />
                <TrajectoryBadge trajectory={latestPrediction.trajectory} />
              </div>
              <div className="text-xs text-slate-400 mt-1">
                As of {formatDate(latestPrediction.predictionDate)}
              </div>
            </div>
          )}
        </div>

        {/* Ethical / Research Disclaimer Box */}
        <div className="mt-4 p-4 rounded-xl bg-amber-50/80 border border-amber-200 text-xs sm:text-sm text-amber-900 flex items-start space-x-3">
          <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-950">Ethical Notice & Interpretability Guidance</p>
            <p className="text-amber-800 leading-relaxed">
              Early warning predictions are probabilistic statistical estimates, <strong>never guaranteed outcomes</strong>.
              The factors listed below describe historical model associations, <strong>not direct causes</strong>.
              These indicators are provided solely to empower timely academic guidance and voluntary support.
            </p>
          </div>
        </div>
      </div>

      {/* Contributing Factors Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold text-slate-900 flex items-center">
            <Layers className="w-5 h-5 mr-2 text-teal-600" />
            Top Contributing Factors
          </h2>
          <span className="text-xs text-slate-400">Ranked by SHAP contribution</span>
        </div>
        <p className="text-xs text-slate-500 mb-6">
          Features that had the strongest influence on your current academic forecast:
        </p>

        {riskFactors.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No risk factors available.</p>
        ) : (
          <div className="space-y-4">
            {riskFactors.map((factor) => {
              const increases = factor.direction === 'increases_risk';
              const displayTitle = getFeatureDisplayTitle(factor.feature);
              const formattedVal = formatFeatureValue(factor);
              const impactPct = Math.min(100, Math.round(Math.abs(factor.contribution) * 100));

              return (
                <div
                  key={factor.rank}
                  className={`p-4 rounded-xl border transition ${
                    increases
                      ? 'bg-rose-50/40 border-rose-200/80'
                      : 'bg-emerald-50/40 border-emerald-200/80'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-start space-x-3">
                      <span
                        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold font-mono ${
                          increases
                            ? 'bg-rose-200 text-rose-800'
                            : 'bg-emerald-200 text-emerald-800'
                        }`}
                      >
                        {factor.rank}
                      </span>
                      <div>
                        <div className="font-bold text-sm text-slate-900">{displayTitle}</div>
                        <div className="text-xs text-slate-500 font-mono mt-0.5">
                          Key: {factor.feature}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 self-end sm:self-center">
                      <div className="text-right">
                        <div className="text-xs text-slate-500">Recorded Metric</div>
                        <div className="text-sm font-bold font-mono text-slate-800">{formattedVal}</div>
                      </div>

                      <div
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                          increases
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        }`}
                      >
                        {increases ? (
                          <TrendingUp className="w-3.5 h-3.5 mr-1" />
                        ) : (
                          <TrendingDown className="w-3.5 h-3.5 mr-1" />
                        )}
                        <span>{increases ? 'Raises Risk' : 'Lowers Risk'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Visual Impact Contribution Bar */}
                  <div className="mt-3 pt-3 border-t border-slate-200/60 flex items-center justify-between text-xs">
                    <span className="text-slate-500">{formatDirectionText(factor.direction)}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 sm:w-36 bg-slate-200 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            increases ? 'bg-rose-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${impactPct}%` }}
                        />
                      </div>
                      <span className="font-mono font-semibold text-slate-700">
                        {factor.contribution > 0 ? `+${factor.contribution.toFixed(2)}` : factor.contribution.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Historical Trajectory Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-2 flex items-center">
          <Calendar className="w-5 h-5 mr-2 text-teal-600" />
          Risk Trajectory Over Time
        </h2>
        <p className="text-xs text-slate-500 mb-6">
          Bi-weekly snapshots showing the trend in risk evaluation:
        </p>

        <div className="space-y-4">
          {predictions.map((pred, idx) => (
            <div
              key={pred.id}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 rounded-full bg-teal-100 border border-teal-200 flex items-center justify-center font-bold text-xs text-teal-800">
                  #{predictions.length - idx}
                </div>
                <div>
                  <div className="font-semibold text-sm text-slate-900">
                    {formatDate(pred.predictionDate)}
                  </div>
                  <div className="text-xs text-slate-500">
                    Model: <span className="font-mono">{pred.modelVersion}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <div className="text-xs text-slate-400">Risk Level</div>
                  <RiskBadge level={pred.riskLevel} size="sm" />
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400">Trajectory</div>
                  <TrajectoryBadge trajectory={pred.trajectory} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
