export type RiskLevel = 'stable' | 'watch' | 'elevated' | 'high';

export type Trajectory =
  | 'insufficient_history'
  | 'improving'
  | 'stable'
  | 'increasing'
  | 'rapidly_increasing';

export type DataProvenance = 'benchmark' | 'synthetic' | 'institutional';

export type FactorDirection = 'increases_risk' | 'decreases_risk';

export interface RiskFactor {
  rank: number;
  feature: string;
  featureValue: number | null;
  contribution: number;
  direction: FactorDirection;
}

export interface RiskPrediction {
  id: string;
  studentId: string;
  predictionDate: string;
  riskProbability: number;
  riskLevel: RiskLevel;
  modelVersion: string;
  provenance: DataProvenance;
  createdAt: string;
  trajectory: Trajectory;
}

export interface Student {
  id: string;
  rollNumber: string;
  fullName: string;
  email: string;
  programme: string;
  admissionYear: number;
  currentSemester: number;
  status: 'active' | 'graduated' | 'inactive';
  department: string;
  institutionName: string;
}

export interface CourseResult {
  id: string;
  courseCode: string;
  courseTitle: string;
  credits: number;
  semester: number;
  academicYear: string;
  marks: number | null;
  grade: string | null;
  gradePoints: number | null;
  status: 'completed' | 'enrolled' | 'withdrawn';
}

export interface AcademicRecord {
  semester: number;
  academicYear: string;
  sgpa: number | null;
  cgpa: number | null;
  creditsRegistered: number;
  creditsEarned: number;
  resultStatus: 'pass' | 'fail' | 'pending';
}

export interface AttendanceRecord {
  id: string;
  studentId: string;
  courseCode: string;
  courseTitle: string;
  date: string;
  sessionNumber: number;
  status: 'present' | 'absent' | 'excused';
}

export interface Assignment {
  id: string;
  courseCode: string;
  courseTitle: string;
  title: string;
  maxScore: number;
  dueAt: string;
  status: 'submitted' | 'late' | 'missing' | 'upcoming';
  score?: number | null;
  submittedAt?: string | null;
  gradedAt?: string | null;
}

export interface Intervention {
  id: string;
  studentId: string;
  studentName: string;
  interventionType: 'attendance_follow_up' | 'mentor_meeting' | 'academic_tutoring' | 'wellbeing_checkin';
  status: 'recommended' | 'approved' | 'in_progress' | 'completed' | 'declined';
  source: 'model_rule' | 'mentor_manual' | 'student_checkin';
  dueOn: string;
  reason: string;
  priority: 'high' | 'medium' | 'low';
  ruleId?: string;
  outcome?: string;
  declineReason?: string;
  createdAt: string;
}

export interface Checkin {
  id: string;
  studentId: string;
  studentName: string;
  category: 'academics' | 'attendance' | 'workload' | 'wellbeing' | 'other';
  stressLevel: 1 | 2 | 3 | 4 | 5;
  message: string;
  createdAt: string;
  acknowledgedByMentor: boolean;
}

export interface RegisteredModel {
  id: string;
  modelName: string;
  version: string;
  target: string;
  datasetVersion: string;
  featureVersion: string;
  provenance: DataProvenance;
  status: 'development' | 'staging' | 'production' | 'retired';
  trainingTimestamp: string;
  rocAuc: number;
  prAuc: number;
  f1Score: number;
}

export interface DriftAlert {
  id: string;
  modelRegistryId: string;
  modelName: string;
  alertType: 'prediction_drift' | 'feature_drift';
  subject: string;
  statistic: 'psi' | 'ks_test' | 'wasserstein';
  value: number;
  threshold: number;
  severity: 'critical' | 'warning';
  status: 'open' | 'acknowledged' | 'resolved';
  createdAt: string;
}

export interface MonitoringSnapshot {
  id: string;
  modelRegistryId: string;
  modelVersion: string;
  windowStart: string;
  windowEnd: string;
  predictionsCount: number;
  labelsAvailable: number;
}

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  type: 'alert' | 'intervention' | 'academic' | 'checkin';
  targetRole: 'student' | 'mentor' | 'admin' | 'all';
}

export type UserRole = 'student' | 'mentor' | 'admin';
