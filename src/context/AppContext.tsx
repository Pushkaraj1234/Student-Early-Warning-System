import React, { createContext, useContext, useState, ReactNode } from 'react';
import {
  Student,
  RiskPrediction,
  RiskFactor,
  CourseResult,
  AcademicRecord,
  Assignment,
  Intervention,
  Checkin,
  RegisteredModel,
  DriftAlert,
  MonitoringSnapshot,
  AppNotification,
  UserRole,
} from '../types';
import {
  INITIAL_STUDENTS,
  INITIAL_PREDICTIONS,
  INITIAL_RISK_FACTORS,
  INITIAL_COURSES,
  INITIAL_ACADEMICS,
  INITIAL_ASSIGNMENTS,
  INITIAL_INTERVENTIONS,
  INITIAL_CHECKINS,
  INITIAL_MODELS,
  INITIAL_DRIFT_ALERTS,
  INITIAL_SNAPSHOTS,
  INITIAL_NOTIFICATIONS,
} from '../data/initialData';

interface AppContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  activeStudentId: string;
  setActiveStudentId: (id: string) => void;
  students: Student[];
  currentStudent: Student;
  predictions: RiskPrediction[];
  latestPrediction: RiskPrediction | null;
  riskFactors: RiskFactor[];
  courses: CourseResult[];
  academics: AcademicRecord[];
  assignments: Assignment[];
  interventions: Intervention[];
  checkins: Checkin[];
  models: RegisteredModel[];
  driftAlerts: DriftAlert[];
  snapshots: MonitoringSnapshot[];
  notifications: AppNotification[];
  // Actions
  addCheckin: (category: Checkin['category'], stressLevel: Checkin['stressLevel'], message: string) => void;
  updateInterventionStatus: (
    id: string,
    status: Intervention['status'],
    details?: { outcome?: string; declineReason?: string }
  ) => void;
  addIntervention: (intervention: Omit<Intervention, 'id' | 'createdAt'>) => void;
  acknowledgeCheckin: (checkinId: string) => void;
  updateDriftAlertStatus: (id: string, status: DriftAlert['status']) => void;
  updateModelStatus: (id: string, status: RegisteredModel['status']) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  submitAssignment: (assignmentId: string) => void;
  attendanceStats: {
    attendedCount: number;
    totalCount: number;
    ratePct: number;
    rate14dPct: number;
  };
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<UserRole>('student');
  const [activeStudentId, setActiveStudentId] = useState<string>('s2'); // Default to Student Beta (rich demo case)
  const [students] = useState<Student[]>(INITIAL_STUDENTS);
  const [allPredictions] = useState(INITIAL_PREDICTIONS);
  const [allFactors] = useState(INITIAL_RISK_FACTORS);
  const [allCourses] = useState(INITIAL_COURSES);
  const [allAcademics] = useState(INITIAL_ACADEMICS);
  const [allAssignments, setAllAssignments] = useState(INITIAL_ASSIGNMENTS);
  const [interventions, setInterventions] = useState<Intervention[]>(INITIAL_INTERVENTIONS);
  const [checkins, setCheckins] = useState<Checkin[]>(INITIAL_CHECKINS);
  const [models, setModels] = useState<RegisteredModel[]>(INITIAL_MODELS);
  const [driftAlerts, setDriftAlerts] = useState<DriftAlert[]>(INITIAL_DRIFT_ALERTS);
  const [snapshots] = useState<MonitoringSnapshot[]>(INITIAL_SNAPSHOTS);
  const [notifications, setNotifications] = useState<AppNotification[]>(INITIAL_NOTIFICATIONS);

  const currentStudent = students.find((s) => s.id === activeStudentId) || students[0];
  const predictions = allPredictions[activeStudentId] || [];
  const latestPrediction = predictions.length > 0 ? predictions[0] : null;
  const riskFactors = allFactors[activeStudentId] || [];
  const courses = allCourses[activeStudentId] || [];
  const academics = allAcademics[activeStudentId] || [];
  const assignments = allAssignments[activeStudentId] || [];

  // Attendance stats based on student
  const attendanceStats = activeStudentId === 's1'
    ? { attendedCount: 39, totalCount: 42, ratePct: 92.8, rate14dPct: 93.0 }
    : activeStudentId === 's2'
    ? { attendedCount: 22, totalCount: 42, ratePct: 52.4, rate14dPct: 52.0 }
    : { attendedCount: 34, totalCount: 42, ratePct: 81.0, rate14dPct: 82.0 };

  const addCheckin = (category: Checkin['category'], stressLevel: Checkin['stressLevel'], message: string) => {
    const newCheckin: Checkin = {
      id: `chk_${Date.now()}`,
      studentId: currentStudent.id,
      studentName: currentStudent.fullName,
      category,
      stressLevel,
      message,
      createdAt: new Date().toISOString(),
      acknowledgedByMentor: false,
    };
    setCheckins((prev) => [newCheckin, ...prev]);

    // Create a notification for mentor
    const notif: AppNotification = {
      id: `notif_${Date.now()}`,
      title: `New Check-in: ${currentStudent.fullName}`,
      message: `${currentStudent.fullName} reported stress level ${stressLevel}/5: "${message.slice(0, 60)}..."`,
      timestamp: new Date().toISOString(),
      read: false,
      type: 'checkin',
      targetRole: 'mentor',
    };
    setNotifications((prev) => [notif, ...prev]);
  };

  const updateInterventionStatus = (
    id: string,
    status: Intervention['status'],
    details?: { outcome?: string; declineReason?: string }
  ) => {
    setInterventions((prev) =>
      prev.map((iv) => {
        if (iv.id === id) {
          return {
            ...iv,
            status,
            outcome: details?.outcome !== undefined ? details.outcome : iv.outcome,
            declineReason: details?.declineReason !== undefined ? details.declineReason : iv.declineReason,
          };
        }
        return iv;
      })
    );
  };

  const addIntervention = (intervention: Omit<Intervention, 'id' | 'createdAt'>) => {
    const newIv: Intervention = {
      ...intervention,
      id: `iv_${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    setInterventions((prev) => [newIv, ...prev]);
  };

  const acknowledgeCheckin = (checkinId: string) => {
    setCheckins((prev) =>
      prev.map((c) => (c.id === checkinId ? { ...c, acknowledgedByMentor: true } : c))
    );
  };

  const updateDriftAlertStatus = (id: string, status: DriftAlert['status']) => {
    setDriftAlerts((prev) =>
      prev.map((al) => (al.id === id ? { ...al, status } : al))
    );
  };

  const updateModelStatus = (id: string, status: RegisteredModel['status']) => {
    setModels((prev) =>
      prev.map((m) => (m.id === id ? { ...m, status } : m))
    );
  };

  const markNotificationRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const submitAssignment = (assignmentId: string) => {
    setAllAssignments((prev) => ({
      ...prev,
      [activeStudentId]: prev[activeStudentId].map((a) =>
        a.id === assignmentId
          ? {
              ...a,
              status: 'submitted',
              submittedAt: new Date().toISOString(),
            }
          : a
      ),
    }));
  };

  return (
    <AppContext.Provider
      value={{
        role,
        setRole,
        activeStudentId,
        setActiveStudentId,
        students,
        currentStudent,
        predictions,
        latestPrediction,
        riskFactors,
        courses,
        academics,
        assignments,
        interventions,
        checkins,
        models,
        driftAlerts,
        snapshots,
        notifications,
        addCheckin,
        updateInterventionStatus,
        addIntervention,
        acknowledgeCheckin,
        updateDriftAlertStatus,
        updateModelStatus,
        markNotificationRead,
        markAllNotificationsRead,
        submitAssignment,
        attendanceStats,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
