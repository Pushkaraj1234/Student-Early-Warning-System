/**
 * Student Early Warning System (SEWS)
 * API Client Services
 */

import { User, Student, RiskPrediction, Intervention, FollowUpRecord, NotificationItem, ModelVersion, DashboardStats, SystemSettings } from '../types.js';

const API_BASE = '/api';

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('sews_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    localStorage.removeItem('sews_token');
    localStorage.removeItem('sews_user');
    window.dispatchEvent(new Event('sews_auth_change'));
    throw new Error('Session expired. Please log in again.');
  }

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `HTTP error ${res.status}`);
  }
  return data;
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    return handleResponse(res);
  },

  async getMe(): Promise<{ user: User }> {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers: getHeaders() });
    } finally {
      localStorage.removeItem('sews_token');
      localStorage.removeItem('sews_user');
      window.dispatchEvent(new Event('sews_auth_change'));
    }
  },

  // Dashboard & Statistics
  async getDashboardStats(departmentId?: string): Promise<DashboardStats> {
    const query = departmentId && departmentId !== 'ALL' ? `?departmentId=${departmentId}` : '';
    const res = await fetch(`${API_BASE}/dashboard/statistics${query}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // Students
  async getStudents(params: {
    departmentId?: string;
    riskLevel?: string;
    semester?: string;
    search?: string;
    page?: number;
    limit?: number;
    assignedOnly?: boolean;
  } = {}): Promise<{ students: Student[]; total: number; page: number; pageSize: number; totalPages: number }> {
    const q = new URLSearchParams();
    if (params.departmentId) q.append('departmentId', params.departmentId);
    if (params.riskLevel) q.append('riskLevel', params.riskLevel);
    if (params.semester) q.append('semester', params.semester);
    if (params.search) q.append('search', params.search);
    if (params.page) q.append('page', String(params.page));
    if (params.limit) q.append('limit', String(params.limit));
    if (params.assignedOnly) q.append('facultyAssignedOnly', 'true');

    const res = await fetch(`${API_BASE}/students?${q.toString()}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async getStudentById(id: string): Promise<any> {
    const res = await fetch(`${API_BASE}/students/${id}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async recalculatePrediction(studentId: string, updates: {
    updatedAttendance?: number;
    updatedCGPA?: number;
    updatedBacklogs?: number;
    updatedDropRate?: number;
  }): Promise<{ prediction: RiskPrediction }> {
    const res = await fetch(`${API_BASE}/predictions/recalculate/${studentId}`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(updates)
    });
    return handleResponse(res);
  },

  // Interventions & Follow-ups
  async getInterventions(params: { studentId?: string; facultyId?: string; status?: string } = {}): Promise<{ interventions: Intervention[] }> {
    const q = new URLSearchParams();
    if (params.studentId) q.append('studentId', params.studentId);
    if (params.facultyId) q.append('facultyId', params.facultyId);
    if (params.status) q.append('status', params.status);

    const res = await fetch(`${API_BASE}/interventions?${q.toString()}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async createIntervention(data: Partial<Intervention>): Promise<{ id: string; message: string }> {
    const res = await fetch(`${API_BASE}/interventions`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data)
    });
    return handleResponse(res);
  },

  async updateIntervention(id: string, data: Partial<Intervention>): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/interventions/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data)
    });
    return handleResponse(res);
  },

  async completeFollowUp(id: string, data: {
    observations: string;
    studentFeedback?: string;
    updatedAttendance?: number;
    updatedCGPA?: number;
    updatedBacklogs?: number;
  }): Promise<{
    message: string;
    outcome: string;
    previousRisk: number;
    newRisk: number;
    riskLevel: string;
    improvedDelta: number;
  }> {
    const res = await fetch(`${API_BASE}/follow-ups/${id}/complete`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data)
    });
    return handleResponse(res);
  },

  // CSV Data Import
  async importStudentData(csvContent: string, dryRun: boolean = false): Promise<any> {
    const res = await fetch(`${API_BASE}/data/import`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ csvContent, dryRun })
    });
    return handleResponse(res);
  },

  // Model Evaluation & Research
  async getModelMetrics(): Promise<{
    models: ModelVersion[];
    activeModelId: string;
    featureImportance: Array<{ feature: string; importance: number }>;
    researchAblation: Array<{ configuration: string; recall: number; precision: number; f1: number; rocAuc: number }>;
  }> {
    const res = await fetch(`${API_BASE}/model/metrics`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async switchModel(modelId: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/model/switch`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ modelId })
    });
    return handleResponse(res);
  },

  // Notifications
  async getNotifications(): Promise<{ notifications: NotificationItem[]; unreadCount: number }> {
    const res = await fetch(`${API_BASE}/notifications`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async markNotificationRead(id: string): Promise<void> {
    await fetch(`${API_BASE}/notifications/${id}/read`, { method: 'PUT', headers: getHeaders() });
  },

  // Audit Logs
  async getAuditLogs(): Promise<{ logs: any[] }> {
    const res = await fetch(`${API_BASE}/audit-logs`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // Settings
  async getSettings(): Promise<{ settings: SystemSettings }> {
    const res = await fetch(`${API_BASE}/settings`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async updateSettings(data: any): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data)
    });
    return handleResponse(res);
  },

  // Automated System Test Suite
  async runSystemTests(): Promise<{
    timestamp: string;
    overallStatus: string;
    totalTests: number;
    passedCount: number;
    results: Array<{ name: string; category: string; passed: boolean; message: string }>;
  }> {
    const res = await fetch(`${API_BASE}/test/run`, { headers: getHeaders() });
    return handleResponse(res);
  }
};
