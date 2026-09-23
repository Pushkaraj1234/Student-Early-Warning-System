/**
 * Student Early Warning System (SEWS)
 * Core Type Definitions
 */

export type UserRole = 'ADMIN' | 'FACULTY' | 'STUDENT';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  departmentId?: string;
  studentId?: string;
  avatarUrl?: string;
  createdAt?: string;
}

export interface Department {
  id: string;
  code: string;
  name: string;
  hodName?: string;
  studentCount?: number;
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  departmentId: string;
  credits: number;
  semester: number;
}

export interface Student {
  id: string; // STU-xxxx
  userId?: string;
  name: string;
  email: string;
  departmentId: string;
  department_id?: string;
  departmentName?: string;
  departmentCode?: string;
  program: string;
  semester: number;
  division: string;
  admissionYear: number;
  admission_year?: number;
  currentCGPA: number;
  current_cgpa?: number;
  previousCGPA: number;
  previous_cgpa?: number;
  backlogCount: number;
  backlog_count?: number;
  attendance_rate?: number;
  academicStatus: 'REGULAR' | 'PROBATION' | 'UNDER_REVIEW' | 'CRITICAL_WATCH';
  academic_status?: 'REGULAR' | 'PROBATION' | 'UNDER_REVIEW' | 'CRITICAL_WATCH';
  assignedFacultyId?: string;
  assigned_faculty_id?: string;
  assignedFacultyName?: string;
  // Dynamic current risk snapshot
  currentRiskProbability?: number;
  risk_probability?: number;
  currentRiskLevel?: RiskLevel;
  risk_level?: RiskLevel;
  primaryRiskFactor?: string;
  lastAssessedDate?: string;
  activeInterventionCount?: number;
}

export interface Faculty {
  id: string;
  userId: string;
  name: string;
  email: string;
  departmentId: string;
  designation: string;
  assignedStudentCount?: number;
  activeInterventionCount?: number;
}

export interface AcademicRecord {
  id: string;
  studentId: string;
  semester: number;
  gpa: number;
  totalCredits: number;
  creditsEarned: number;
  failedSubjects: number;
  academicYear: string;
  createdAt: string;
}

export interface SubjectAssessment {
  id: string;
  studentId: string;
  subjectId: string;
  subjectName?: string;
  semester: number;
  internalUT1: number; // Max 20 or 30
  internalUT2: number;
  maxInternal: number;
  attendancePercentage: number;
  assignmentsSubmitted: number;
  assignmentsTotal: number;
  status: 'PASSING' | 'BORDERLINE' | 'AT_RISK';
}

export interface AttendanceRecord {
  id: string;
  studentId: string;
  subjectId?: string;
  monthYear: string;
  classesHeld: number;
  classesAttended: number;
  percentage: number;
  recentDropRate: number; // e.g. -12% drop compared to previous period
  recordedAt: string;
}

export interface LMSActivity {
  id: string;
  studentId: string;
  weeklyLogins: number;
  activeHours: number;
  resourcesAccessed: number;
  quizParticipationRate: number; // 0 - 100
  recordedAt: string;
}

export interface StudentFeatures {
  studentId: string;
  currentCGPA: number;
  previousCGPA: number;
  cgpaDecline: number; // previous - current (positive means worsening)
  attendanceRate: number; // 0 - 100
  recentAttendanceDrop: number; // drop in last 4 weeks (%)
  backlogCount: number;
  failedSubjectCount: number;
  assignmentCompletionRate: number; // 0 - 100
  lmsEngagementScore: number; // 0 - 100
  internalExamAvg: number; // 0 - 100
  absenceFrequency: number;
  calculatedAt: string;
}

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

export interface SHAPContribution {
  featureKey: string;
  featureLabel: string;
  featureValue: number | string;
  shapValue: number; // impact on log-odds / risk probability
  relativeImpact: 'HIGH' | 'MEDIUM' | 'LOW';
  direction: 'RISK_INCREASING' | 'PROTECTIVE';
  humanDescription: string;
}

export interface RiskPrediction {
  id: string;
  studentId: string;
  studentName?: string;
  riskProbability: number; // e.g. 82.5 (%)
  riskLevel: RiskLevel;
  modelVersionId: string;
  modelVersionName?: string;
  baselineProbability: number;
  contributingFactors: SHAPContribution[];
  humanSummary: string;
  timestamp: string;
  isDynamicFollowUp?: boolean;
}

export interface RiskThresholds {
  lowMax: number;       // default: 30
  moderateMax: number;  // default: 55
  highMax: number;      // default: 75
  criticalMin: number;  // default: 76
}

export interface InterventionRecommendation {
  category: 'ATTENDANCE' | 'ACADEMIC_MENTORING' | 'REMEDIAL_CLASSES' | 'ASSIGNMENT_SUPPORT' | 'COUNSELLING' | 'COMBINED';
  title: string;
  urgency: 'ROUTINE' | 'MODERATE' | 'URGENT' | 'IMMEDIATE';
  description: string;
  suggestedActionItems: string[];
  rationale: string;
}

export interface Intervention {
  id: string;
  studentId: string;
  student_id?: string;
  studentName?: string;
  student_name?: string;
  studentRoll?: string;
  studentDepartment?: string;
  facultyId: string;
  faculty_id?: string;
  facultyName?: string;
  faculty_name?: string;
  riskLevelAtCreation?: RiskLevel;
  riskProbabilityAtCreation?: number;
  riskLevel?: RiskLevel;
  risk_level?: RiskLevel;
  riskProbability?: number;
  risk_probability?: number;
  detectedRiskFactors?: string[];
  aiRecommendation?: string;
  ai_recommendation?: string;
  selectedIntervention: string;
  selected_intervention?: string;
  facultyNotes: string;
  faculty_notes?: string;
  actionItems: string[] | string;
  action_items?: string[] | string;
  assignedDate: string;
  assigned_date?: string;
  followUpDate?: string;
  follow_up_date?: string;
  status: 'PLANNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  outcome?: 'IMPROVED' | 'NO_CHANGE' | 'DECLINED' | 'PENDING';
  postInterventionRiskProb?: number;
  post_risk_probability?: number;
  postInterventionRiskLevel?: RiskLevel;
  lastUpdated?: string;
}

export interface FollowUpRecord {
  id: string;
  interventionId: string;
  intervention_id?: string;
  studentId: string;
  student_id?: string;
  facultyId: string;
  faculty_id?: string;
  scheduledDate: string;
  scheduled_date?: string;
  completedDate?: string;
  completed_date?: string;
  facultyObservations?: string;
  observations?: string;
  studentFeedback?: string;
  status: 'PENDING' | 'COMPLETED' | 'OVERDUE';
  updatedAttendance?: number;
  updatedCGPA?: number;
  updatedBacklogs?: number;
  newRiskProbability?: number;
  newRiskLevel?: RiskLevel;
  createdAt?: string;
}

export interface NotificationItem {
  id: string;
  userId?: string;
  user_id?: string;
  title: string;
  message: string;
  type: string;
  isRead?: boolean;
  is_read?: boolean | number;
  linkUrl?: string;
  link_url?: string;
  createdAt?: string;
  created_at?: string;
}

export interface ModelVersion {
  id: string;
  name: string;
  algorithm: 'Logistic Regression' | 'Decision Tree' | 'Random Forest' | 'XGBoost Ensemble' | 'LightGBM Classifier';
  version: string;
  trainedDate: string;
  datasetVersion: string;
  features: string[];
  metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1Score: number;
    rocAuc: number;
    prAuc: number;
    confusionMatrix: {
      tp: number;
      fp: number;
      tn: number;
      fn: number;
    };
  };
  status: 'ACTIVE' | 'ARCHIVED' | 'TRAINING';
  isDefault: boolean;
  notes?: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userEmail: string;
  userRole: string;
  action: string;
  entity: string;
  entityId: string;
  previousValue?: string;
  newValue?: string;
}

export interface SystemSettings {
  institutionName: string;
  riskThresholds: RiskThresholds;
  attendanceWarningThreshold?: number; // default: 75%
  attendanceThreshold?: number;
  cgpaDeclineThreshold?: number; // default: 0.5
  activeModelId?: string;
  allowFacultyOverride?: boolean;
  autoAlertAdminsOnCritical?: boolean;
  lastUpdated?: string;
}

export interface HistoricalRiskPoint {
  id?: string;
  checkpoint: string; // e.g., "W1 Baseline", "W4 Quiz", "W8 Midterm", "W12 UT-2", "W16 Current"
  shortLabel: string; // e.g. "W1", "W4", "W8", "W12", "W16"
  date: string;
  riskProbability: number; // 0 to 100
  riskLevel: RiskLevel;
  eventNote: string;
  eventType?: 'BASELINE' | 'EXAM' | 'ATTENDANCE_DROP' | 'INTERVENTION' | 'RE_EVALUATION' | 'CURRENT';
  attendanceSnapshot?: number;
  cgpaSnapshot?: number;
}

export interface HistoricalRiskSummary {
  points: HistoricalRiskPoint[];
  trendPattern: 'IMPROVING' | 'DECLINING' | 'STABLE';
  netChange: number; // current - initial (negative = improvement/risk reduction, positive = decline/risk escalation)
  percentChange: number;
  startProbability: number;
  currentProbability: number;
  peakProbability: number;
  lowestProbability: number;
  patternDescription: string;
  interventionCount?: number;
}

export interface DashboardStats {
  totalStudents: number;
  lowRiskCount: number;
  moderateRiskCount: number;
  highRiskCount: number;
  criticalRiskCount: number;
  studentsRequiringIntervention?: number;
  activeInterventionsCount?: number;
  overdueFollowupsCount?: number;
  averageAttendance: number;
  averageCGPA: number;
  riskDistribution: { name: string; value: number; color: string }[];
  departmentBreakdown: { department: string; departmentCode?: string; total: number; atRisk?: number; critical?: number; high?: number; low?: number; percentage: number }[];
  riskFactorFrequency: { factor: string; count: number; percentage?: number }[];
  riskTrend?: { period: string; averageRisk: number; atRiskCount: number }[];
  metrics?: {
    totalStudents: number;
    criticalRiskCount: number;
    highRiskCount: number;
    avgAttendance: number;
    avgCGPA: number;
    activeInterventions: number;
  };
  topRiskFactors?: Array<{ factor: string; count: number; percentage: number }>;
  recentAlerts?: Array<{ studentId: string; name: string; primaryRiskFactor?: string; riskProbability: number }>;
  overdueFollowUps?: any[];
}
