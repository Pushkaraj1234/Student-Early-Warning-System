import React, { useState, useRef } from 'react';
import { api } from '../../services/api.js';
import {
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Download,
  X,
  Sparkles,
  ArrowRight,
  Database
} from 'lucide-react';

interface DataImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const SAMPLE_CSV = `name,email,department_id,program,semester,admission_year,current_cgpa,previous_cgpa,backlog_count,attendance_rate,recent_attendance_drop,assignment_completion_rate,lms_engagement_score,internal_exam_avg,absence_frequency,assigned_faculty_id
Kavita Joshi,kavita.j@sews.edu,dept-cse,B.Tech CSE,6,2023,6.20,7.10,1,68.5,14.0,65,50,48,7,fac-1
Manish Rao,manish.r@sews.edu,dept-ece,B.Tech ECE,6,2023,8.40,8.20,0,89.0,2.0,92,80,82,1,fac-2
Tanvi Deshmukh,tanvi.d@sews.edu,dept-cse,B.Tech CSE,6,2023,5.40,6.80,3,56.0,20.0,45,35,40,9,fac-1
Gaurav Bhatia,gaurav.b@sews.edu,dept-it,B.Tech IT,6,2023,7.10,7.20,0,78.0,4.0,80,65,70,3,fac-1`;

export const DataImportModal: React.FC<DataImportModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [csvContent, setCsvContent] = useState<string>('');
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [importedSummary, setImportedSummary] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile.name.endsWith('.csv') && !selectedFile.type.includes('csv') && !selectedFile.type.includes('text')) {
      setErrorMessage('Please provide a valid CSV file.');
      return;
    }
    setFile(selectedFile);
    setErrorMessage(null);
    setValidationResult(null);
    setImportedSummary(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setCsvContent(content);
      runDryRunValidation(content);
    };
    reader.readAsText(selectedFile);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const runDryRunValidation = async (content: string) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await api.importStudentData(content, true); // dryRun = true
      setValidationResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Validation failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExecuteImport = async () => {
    if (!csvContent) return;
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await api.importStudentData(csvContent, false); // dryRun = false
      setImportedSummary(res);
      onSuccess();
    } catch (err: any) {
      setErrorMessage(err.message || 'Import execution failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLoadSample = () => {
    setCsvContent(SAMPLE_CSV);
    setFile(new File([SAMPLE_CSV], 'sample_academic_roster.csv', { type: 'text/csv' }));
    runDryRunValidation(SAMPLE_CSV);
  };

  const handleDownloadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sews_student_roster_template.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadErrorReport = () => {
    if (!validationResult?.errors?.length) return;
    const reportText = [
      'SEWS DATA VALIDATION REPORT',
      `Timestamp: ${new Date().toISOString()}`,
      `Total Rows: ${validationResult.totalRowsProcessed}`,
      `Valid Rows: ${validationResult.validRowCount}`,
      `Invalid Rows: ${validationResult.invalidRowCount}`,
      '',
      'DETAILED ROW ISSUES:',
      ...validationResult.errors.map((e: any) => `Row ${e.row}: [${e.field}] ${e.message}`)
    ].join('\n');

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sews_validation_error_report.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div id="data-import-modal" className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full overflow-hidden transition-all max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-slate-900 text-white p-5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Bulk Student Data Ingestion Engine
              </h2>
              <p className="text-xs text-slate-400">
                CSV upload with automated schema validation, anomaly detection, and ML risk scoring.
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

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {errorMessage && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{errorMessage}</span>
            </div>
          )}

          {importedSummary ? (
            /* Success confirmation */
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 text-center space-y-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
              <h3 className="text-base font-bold text-slate-900">
                Data Successfully Ingested & Evaluated
              </h3>
              <p className="text-xs text-slate-600 max-w-md mx-auto">
                {importedSummary.importedStudents} students imported, feature vectors synthesized, and {importedSummary.predictionsGenerated} ML risk predictions generated.
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs"
                >
                  Return to Dashboard
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Drag and drop zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-50/50'
                    : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/60'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={e => e.target.files && handleFileSelect(e.target.files[0])}
                  accept=".csv,text/csv"
                  className="hidden"
                />
                <UploadCloud className="w-10 h-10 text-indigo-500 mx-auto mb-2" />
                <div className="text-sm font-bold text-slate-800">
                  {file ? file.name : 'Click to browse or drop student CSV file here'}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Supports semester academic records, attendance percentages, and internal exam metrics
                </p>
                <div className="mt-3 flex items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleLoadSample();
                    }}
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-600 font-semibold hover:text-indigo-800 bg-indigo-50 px-2.5 py-1 rounded-md border border-indigo-100"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Load Sample Roster
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownloadSample();
                    }}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-600 font-semibold hover:text-slate-800 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download CSV Template
                  </button>
                </div>
              </div>

              {/* Validation Summary Report */}
              {validationResult && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Pre-Import Validation Analysis
                    </h4>
                    <div className="flex items-center gap-2">
                      {validationResult.errors?.length > 0 && (
                        <button
                          onClick={handleDownloadErrorReport}
                          className="text-xs text-rose-600 hover:text-rose-800 font-semibold flex items-center gap-1"
                        >
                          <Download className="w-3.5 h-3.5" /> Download Error Report
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl text-center">
                      <div className="text-[11px] font-semibold text-slate-500 uppercase">Total Rows</div>
                      <div className="text-lg font-bold text-slate-900">{validationResult.totalRowsProcessed}</div>
                    </div>
                    <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-xl text-center">
                      <div className="text-[11px] font-semibold text-emerald-700 uppercase">Valid Rows</div>
                      <div className="text-lg font-bold text-emerald-700">{validationResult.validRowCount}</div>
                    </div>
                    <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl text-center">
                      <div className="text-[11px] font-semibold text-rose-700 uppercase">Invalid Rows</div>
                      <div className="text-lg font-bold text-rose-700">{validationResult.invalidRowCount}</div>
                    </div>
                  </div>

                  {/* Anomaly & Issue Alerts */}
                  {validationResult.errors?.length > 0 && (
                    <div className="bg-rose-50/50 border border-rose-200 rounded-xl p-3.5 max-h-40 overflow-y-auto space-y-1 text-xs">
                      <div className="font-bold text-rose-900 flex items-center gap-1.5 mb-1.5">
                        <AlertTriangle className="w-4 h-4 text-rose-600" />
                        Detected Ingestion Issues ({validationResult.errors.length}):
                      </div>
                      {validationResult.errors.slice(0, 10).map((err: any, idx: number) => (
                        <div key={idx} className="text-rose-800">
                          Row {err.row}: <span className="font-semibold">{err.field}</span> - {err.message}
                        </div>
                      ))}
                      {validationResult.errors.length > 10 && (
                        <div className="text-slate-500 italic pt-1">
                          + {validationResult.errors.length - 10} additional issues...
                        </div>
                      )}
                    </div>
                  )}

                  {/* Preview Table */}
                  {validationResult.previewRows?.length > 0 && (
                    <div>
                      <div className="text-xs font-bold text-slate-800 mb-2">
                        Preview of Processed Records (First {validationResult.previewRows.length} Rows):
                      </div>
                      <div className="border border-slate-200 rounded-xl overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                          <thead className="bg-slate-50 font-semibold text-slate-700">
                            <tr>
                              <th className="px-3 py-2">Name</th>
                              <th className="px-3 py-2">Email</th>
                              <th className="px-3 py-2">Dept</th>
                              <th className="px-3 py-2">CGPA</th>
                              <th className="px-3 py-2">Att %</th>
                              <th className="px-3 py-2">Drop %</th>
                              <th className="px-3 py-2">Backlogs</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {validationResult.previewRows.map((r: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-3 py-2 font-medium text-slate-900">{r.name}</td>
                                <td className="px-3 py-2 text-slate-500">{r.email}</td>
                                <td className="px-3 py-2 uppercase font-mono text-slate-700">{r.department_id}</td>
                                <td className="px-3 py-2 font-mono text-slate-900">{r.current_cgpa}</td>
                                <td className="px-3 py-2 font-mono text-slate-900">{r.attendance_rate}%</td>
                                <td className="px-3 py-2 font-mono text-slate-900">{r.recent_attendance_drop}%</td>
                                <td className="px-3 py-2 font-mono text-slate-900">{r.backlog_count}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {!importedSummary && (
          <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex items-center justify-between">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              id="confirm-import-btn"
              onClick={handleExecuteImport}
              disabled={isProcessing || !validationResult || validationResult.validRowCount === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors disabled:opacity-50"
            >
              {isProcessing ? 'Processing...' : `Execute Import (${validationResult?.validRowCount || 0} Valid Records)`}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
