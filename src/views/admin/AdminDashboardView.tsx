import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { ProvenanceBadge } from '../../components/RiskBadge';
import { formatDate } from '../../utils/formatting';
import {
  Layers,
  AlertTriangle,
  Activity,
  CheckCircle2,
  Clock,
  ShieldCheck,
  TrendingUp,
  RotateCcw,
} from 'lucide-react';
import { RegisteredModel } from '../../types';

export const AdminDashboardView: React.FC = () => {
  const {
    models,
    driftAlerts,
    snapshots,
    updateDriftAlertStatus,
    updateModelStatus,
  } = useApp();

  const [activeTab, setActiveTab] = useState<'models' | 'drift' | 'windows'>('models');

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase font-bold tracking-wider text-emerald-700 font-mono">
              Model Governance & Drift Oversight
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
              ML System Administration & Monitoring
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Production model registry, population stability monitoring (PSI), and feature drift audits.
            </p>
          </div>

          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setActiveTab('models')}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === 'models'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Models ({models.length})
            </button>
            <button
              onClick={() => setActiveTab('drift')}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === 'drift'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Drift Alerts ({driftAlerts.filter((a) => a.status === 'open').length} Open)
            </button>
            <button
              onClick={() => setActiveTab('windows')}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === 'windows'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Monitoring Windows
            </button>
          </div>
        </div>

        {/* Governance banner */}
        <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs sm:text-sm text-slate-700 flex items-start space-x-3">
          <ShieldCheck className="w-5 h-5 text-teal-700 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-slate-900">Governance Policy: </span>
            <span>
              Only models in <strong>Production</strong> may score real students. Production status requires verified institutional training data, probability calibration, and recorded institutional audit approval (OULAD benchmark models remain restricted to benchmark exploration).
            </span>
          </div>
        </div>
      </div>

      {/* Models View */}
      {activeTab === 'models' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
              <Layers className="w-5 h-5 mr-2 text-teal-600" />
              Registered Models Registry
            </h2>

            <div className="space-y-4">
              {models.map((model) => {
                const isProd = model.status === 'production';
                const isDev = model.status === 'development';
                const isStaging = model.status === 'staging';

                return (
                  <div
                    key={model.id}
                    className="p-5 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-base font-bold text-slate-900">
                          {model.version}
                        </span>
                        <span
                          className={`text-xs uppercase font-bold px-2 py-0.5 rounded-full ${
                            isProd
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : isStaging
                              ? 'bg-blue-100 text-blue-800 border border-blue-300'
                              : 'bg-amber-100 text-amber-800 border border-amber-300'
                          }`}
                        >
                          {model.status}
                        </span>
                        <ProvenanceBadge provenance={model.provenance} />
                      </div>

                      <p className="text-xs text-slate-600">
                        Model Name: <strong>{model.modelName}</strong> &middot; Target: <strong>{model.target}</strong> &middot; Feature Set: <span className="font-mono">{model.featureVersion}</span>
                      </p>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1 font-mono">
                        <span>ROC-AUC: <strong className="text-slate-800">{model.rocAuc}</strong></span>
                        <span>PR-AUC: <strong className="text-slate-800">{model.prAuc}</strong></span>
                        <span>F1: <strong className="text-slate-800">{model.f1Score}</strong></span>
                        <span>Trained: {formatDate(model.trainingTimestamp)}</span>
                      </div>
                    </div>

                    {/* Status Management */}
                    <div className="flex items-center space-x-2 self-end md:self-center">
                      {isDev && (
                        <button
                          onClick={() => updateModelStatus(model.id, 'staging')}
                          className="px-3 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold transition"
                        >
                          Promote to Staging
                        </button>
                      )}
                      {isStaging && (
                        <button
                          onClick={() => updateModelStatus(model.id, 'production')}
                          className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold transition"
                        >
                          Promote to Production
                        </button>
                      )}
                      {isProd && (
                        <button
                          onClick={() => updateModelStatus(model.id, 'development')}
                          className="px-3 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold transition"
                        >
                          Demote to Dev
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Drift Alerts View */}
      {activeTab === 'drift' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
              <AlertTriangle className="w-5 h-5 mr-2 text-rose-600" />
              Statistical Drift Monitoring
            </h2>

            <div className="space-y-3">
              {driftAlerts.map((alert) => {
                const isOpen = alert.status === 'open';
                const isAck = alert.status === 'acknowledged';
                const isResolved = alert.status === 'resolved';

                return (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-xl border transition flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                      isOpen
                        ? 'bg-rose-50/60 border-rose-200'
                        : isAck
                        ? 'bg-amber-50/60 border-amber-200'
                        : 'bg-slate-50 border-slate-200 opacity-70'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${
                            alert.severity === 'critical'
                              ? 'bg-rose-100 text-rose-800 border border-rose-300'
                              : 'bg-amber-100 text-amber-800 border border-amber-300'
                          }`}
                        >
                          {alert.severity}
                        </span>
                        <span className="font-bold text-sm text-slate-900 capitalize">
                          {alert.alertType.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">
                          Model: {alert.modelName}
                        </span>
                      </div>

                      <div className="text-xs text-slate-700">
                        Subject: <strong className="font-mono">{alert.subject}</strong> &middot; Metric:{' '}
                        <strong className="font-mono uppercase">{alert.statistic}</strong>
                      </div>

                      <div className="text-xs font-mono text-slate-600 pt-0.5">
                        Observed Value: <strong className="text-rose-700">{alert.value}</strong> (Threshold:{' '}
                        {alert.threshold}) &middot; Detected: {formatDate(alert.createdAt)}
                      </div>
                    </div>

                    {/* Alert Actions */}
                    <div className="flex items-center space-x-2 self-end md:self-center">
                      {isOpen && (
                        <>
                          <button
                            onClick={() => updateDriftAlertStatus(alert.id, 'acknowledged')}
                            className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold transition"
                          >
                            Acknowledge
                          </button>
                          <button
                            onClick={() => updateDriftAlertStatus(alert.id, 'resolved')}
                            className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold transition"
                          >
                            Resolve Alert
                          </button>
                        </>
                      )}

                      {isAck && (
                        <button
                          onClick={() => updateDriftAlertStatus(alert.id, 'resolved')}
                          className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold transition"
                        >
                          Mark Resolved
                        </button>
                      )}

                      {isResolved && (
                        <span className="text-xs font-semibold text-emerald-700 flex items-center">
                          <CheckCircle2 className="w-4 h-4 mr-1" />
                          Resolved
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Monitoring Windows View */}
      {activeTab === 'windows' && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
            <Clock className="w-5 h-5 mr-2 text-teal-600" />
            Bi-Weekly Monitoring Windows
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-semibold border-y border-slate-200">
                <tr>
                  <th className="py-3 px-4">Evaluation Window</th>
                  <th className="py-3 px-4">Scored Model</th>
                  <th className="py-3 px-4">Predictions Evaluated</th>
                  <th className="py-3 px-4">Outcomes Verified</th>
                  <th className="py-3 px-4">Verification State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {snapshots.map((snap) => (
                  <tr key={snap.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-medium text-slate-800">
                      {formatDate(snap.windowStart)} &ndash; {formatDate(snap.windowEnd)}
                    </td>
                    <td className="py-3 px-4 font-mono text-teal-800 font-semibold">
                      {snap.modelVersion}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                      {snap.predictionsCount} predictions
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">
                      {snap.labelsAvailable} labels
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                        Audited
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
