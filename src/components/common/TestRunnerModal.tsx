import React, { useState } from 'react';
import { api } from '../../services/api.js';
import { CheckCircle2, XCircle, RefreshCw, X, ShieldCheck, Terminal } from 'lucide-react';

interface TestRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TestRunnerModal: React.FC<TestRunnerModalProps> = ({ isOpen, onClose }) => {
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [testOutput, setTestOutput] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRunTests = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const data = await api.runSystemTests();
      setTestOutput(data);
    } catch (err: any) {
      setError(err.message || 'Failed to execute system test runner');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div id="test-runner-modal" className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full overflow-hidden transition-all">
        {/* Header */}
        <div className="bg-slate-900 text-white p-5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Automated System & ML Test Runner
              </h2>
              <p className="text-xs text-slate-400">
                End-to-end verification of ML inference, SHAP logic, rules engine, and relational integrity.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between bg-slate-50 border border-slate-200 p-4 rounded-xl">
            <div>
              <div className="text-sm font-semibold text-slate-900">Verification Suite Status</div>
              <div className="text-xs text-slate-500 mt-0.5">
                {testOutput ? (
                  <span className="flex items-center gap-1.5">
                    {testOutput.overallStatus === 'ALL_TESTS_PASSED' ? (
                      <span className="text-emerald-600 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> All {testOutput.totalTests} Unit & Integration Tests Passed
                      </span>
                    ) : (
                      <span className="text-rose-600 font-bold flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> {testOutput.totalTests - testOutput.passedCount} of {testOutput.totalTests} Tests Failed
                      </span>
                    )}
                    <span className="text-slate-400">| Last run: {new Date(testOutput.timestamp).toLocaleTimeString()}</span>
                  </span>
                ) : (
                  'Ready to execute test suite against active SQLite database and ML pipeline.'
                )}
              </div>
            </div>

            <button
              id="execute-tests-btn"
              onClick={handleRunTests}
              disabled={isRunning}
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs px-4 py-2.5 rounded-lg shadow-xs transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
              {isRunning ? 'Running Tests...' : 'Execute Suite'}
            </button>
          </div>

          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700">
              <strong>Execution Error:</strong> {error}
            </div>
          )}

          {/* Test items */}
          <div className="space-y-3">
            {testOutput?.results ? (
              testOutput.results.map((test: any, idx: number) => (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border transition-all ${
                    test.passed
                      ? 'bg-emerald-50/40 border-emerald-200/80 text-emerald-950'
                      : 'bg-rose-50/40 border-rose-200 text-rose-950'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      {test.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="text-xs font-bold text-slate-900">{test.name}</div>
                        <div className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                          {test.message}
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/80 border border-slate-200 text-slate-600 shrink-0">
                      {test.category}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                <ShieldCheck className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                Click "Execute Suite" to verify ML inference, explainability bounds, and database constraints.
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex items-center justify-between text-xs text-slate-500">
          <span>Target Environment: SEWS Hybrid SQLite / In-Memory Wasm</span>
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 font-medium rounded-lg text-xs transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
