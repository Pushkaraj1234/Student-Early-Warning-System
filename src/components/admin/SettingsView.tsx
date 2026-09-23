import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { SystemSettings } from '../../types.js';
import { Sliders, Save, CheckCircle2, AlertTriangle, Shield, Building, Info } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setIsLoading(true);
    try {
      const data = await api.getSettings();
      setSettings(data.settings);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    // Validation
    const { lowMax, moderateMax, highMax, criticalMin } = settings.riskThresholds;
    if (lowMax >= moderateMax || moderateMax >= highMax || highMax >= criticalMin) {
      setError('Thresholds must follow strict ascending order: Low Max < Moderate Max < High Max ≤ Critical Min.');
      setIsSaving(false);
      return;
    }

    try {
      await api.updateSettings(settings);
      setSuccessMessage('Threshold configuration and institutional policies updated. Real-time classifications aligned.');
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !settings) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading system settings...</div>;
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs max-w-4xl mx-auto space-y-6">
      <div className="border-b border-slate-100 pb-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-100">
              <Sliders className="w-5 h-5" />
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Institutional Risk Thresholds & System Parameters
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Configure dynamic decision bounds, attendance criteria, and alert policies.
          </p>
        </div>
      </div>

      {successMessage && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Risk Thresholds Card */}
        <div className="bg-slate-50/60 border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-600" />
              Dynamic Risk Classification Thresholds (%)
            </h3>
            <span className="text-[11px] text-slate-500">Continuous Probability Boundaries</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Low Max */}
            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
              <label className="text-xs font-bold text-emerald-700 block mb-1">
                Low Risk Ceiling (≤ %)
              </label>
              <input
                type="number"
                min="10"
                max="50"
                value={settings.riskThresholds.lowMax}
                onChange={e =>
                  setSettings({
                    ...settings,
                    riskThresholds: {
                      ...settings.riskThresholds,
                      lowMax: Number(e.target.value)
                    }
                  })
                }
                className="w-full text-sm font-mono border border-slate-300 rounded-md p-2 text-slate-900"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Default: 30%</span>
            </div>

            {/* Moderate Max */}
            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
              <label className="text-xs font-bold text-yellow-700 block mb-1">
                Moderate Risk Ceiling (≤ %)
              </label>
              <input
                type="number"
                min="31"
                max="70"
                value={settings.riskThresholds.moderateMax}
                onChange={e =>
                  setSettings({
                    ...settings,
                    riskThresholds: {
                      ...settings.riskThresholds,
                      moderateMax: Number(e.target.value)
                    }
                  })
                }
                className="w-full text-sm font-mono border border-slate-300 rounded-md p-2 text-slate-900"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Default: 55%</span>
            </div>

            {/* High Max */}
            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
              <label className="text-xs font-bold text-amber-700 block mb-1">
                High Risk Ceiling (≤ %)
              </label>
              <input
                type="number"
                min="56"
                max="85"
                value={settings.riskThresholds.highMax}
                onChange={e =>
                  setSettings({
                    ...settings,
                    riskThresholds: {
                      ...settings.riskThresholds,
                      highMax: Number(e.target.value)
                    }
                  })
                }
                className="w-full text-sm font-mono border border-slate-300 rounded-md p-2 text-slate-900"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Default: 75%</span>
            </div>

            {/* Critical Min */}
            <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs">
              <label className="text-xs font-bold text-rose-700 block mb-1">
                Critical Risk Floor (≥ %)
              </label>
              <input
                type="number"
                min="60"
                max="90"
                value={settings.riskThresholds.criticalMin}
                onChange={e =>
                  setSettings({
                    ...settings,
                    riskThresholds: {
                      ...settings.riskThresholds,
                      criticalMin: Number(e.target.value)
                    }
                  })
                }
                className="w-full text-sm font-mono border border-slate-300 rounded-md p-2 text-slate-900"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Default: 76%</span>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 flex items-start gap-1.5 pt-1">
            <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
            <span>
              Adjusting thresholds changes the color classification boundaries and triggers automated notifications to faculty mentors when cohorts shift risk bands.
            </span>
          </div>
        </div>

        {/* Institutional Settings */}
        <div className="bg-slate-50/60 border border-slate-200 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Building className="w-4 h-4 text-indigo-600" />
            Institutional Context & Mandatory Rules
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Institution Name
              </label>
              <input
                type="text"
                value={settings.institutionName}
                onChange={e => setSettings({ ...settings, institutionName: e.target.value })}
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-900"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Mandatory Attendance Floor (%)
              </label>
              <input
                type="number"
                min="60"
                max="85"
                value={settings.attendanceThreshold}
                onChange={e => setSettings({ ...settings, attendanceThreshold: Number(e.target.value) })}
                className="w-full text-xs font-mono border border-slate-300 rounded-lg p-2.5 text-slate-900"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Statutory exam eligibility cutoff (Usually 75%)</span>
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving Configurations...' : 'Save Configuration Changes'}
          </button>
        </div>
      </form>
    </div>
  );
};
