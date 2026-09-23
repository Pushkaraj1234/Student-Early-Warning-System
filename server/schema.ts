import { Database } from 'sql.js';
import { saveDb } from './db.js';

export function initializeSchema(db: Database): void {
  const schemaSQL = `
    -- Users Table
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      name TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('ADMIN', 'FACULTY', 'STUDENT')),
      department_id TEXT,
      student_id TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Departments
    CREATE TABLE IF NOT EXISTS departments (
      id TEXT PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      hod_name TEXT
    );

    -- Faculty
    CREATE TABLE IF NOT EXISTS faculty (
      id TEXT PRIMARY KEY,
      user_id TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      department_id TEXT NOT NULL,
      designation TEXT NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (department_id) REFERENCES departments(id)
    );

    -- Courses
    CREATE TABLE IF NOT EXISTS courses (
      id TEXT PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      department_id TEXT NOT NULL,
      total_semesters INTEGER NOT NULL DEFAULT 8,
      FOREIGN KEY (department_id) REFERENCES departments(id)
    );

    -- Subjects
    CREATE TABLE IF NOT EXISTS subjects (
      id TEXT PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      department_id TEXT NOT NULL,
      credits INTEGER NOT NULL DEFAULT 3,
      semester INTEGER NOT NULL,
      FOREIGN KEY (department_id) REFERENCES departments(id)
    );

    -- Students
    CREATE TABLE IF NOT EXISTS students (
      id TEXT PRIMARY KEY,
      user_id TEXT UNIQUE,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      department_id TEXT NOT NULL,
      program TEXT NOT NULL DEFAULT 'B.Tech Computer Science & Engineering',
      semester INTEGER NOT NULL DEFAULT 6,
      division TEXT NOT NULL DEFAULT 'A',
      admission_year INTEGER NOT NULL DEFAULT 2023,
      current_cgpa REAL NOT NULL DEFAULT 7.5,
      previous_cgpa REAL NOT NULL DEFAULT 7.8,
      backlog_count INTEGER NOT NULL DEFAULT 0,
      academic_status TEXT NOT NULL DEFAULT 'REGULAR',
      assigned_faculty_id TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
      FOREIGN KEY (department_id) REFERENCES departments(id),
      FOREIGN KEY (assigned_faculty_id) REFERENCES faculty(id)
    );

    -- Enrollments
    CREATE TABLE IF NOT EXISTS enrollments (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      subject_id TEXT NOT NULL,
      semester INTEGER NOT NULL,
      academic_year TEXT NOT NULL,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
      FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );

    -- Academic Records (Historical Semester Performance)
    CREATE TABLE IF NOT EXISTS academic_records (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      semester INTEGER NOT NULL,
      gpa REAL NOT NULL,
      total_credits INTEGER NOT NULL,
      credits_earned INTEGER NOT NULL,
      failed_subjects INTEGER NOT NULL DEFAULT 0,
      academic_year TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- Attendance Records
    CREATE TABLE IF NOT EXISTS attendance_records (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      subject_id TEXT,
      month_year TEXT NOT NULL,
      classes_held INTEGER NOT NULL,
      classes_attended INTEGER NOT NULL,
      percentage REAL NOT NULL,
      recent_drop_rate REAL NOT NULL DEFAULT 0,
      recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- Assessment Records
    CREATE TABLE IF NOT EXISTS assessment_records (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      subject_id TEXT NOT NULL,
      semester INTEGER NOT NULL,
      internal_ut1 REAL NOT NULL,
      internal_ut2 REAL NOT NULL,
      max_internal REAL NOT NULL DEFAULT 30,
      attendance_pct REAL NOT NULL,
      assignments_submitted INTEGER NOT NULL,
      assignments_total INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'PASSING',
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
      FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );

    -- LMS Activity Records
    CREATE TABLE IF NOT EXISTS lms_activity (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      weekly_logins INTEGER NOT NULL,
      active_hours REAL NOT NULL,
      resources_accessed INTEGER NOT NULL,
      quiz_participation_rate REAL NOT NULL,
      recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- Calculated Student Feature Vectors for ML
    CREATE TABLE IF NOT EXISTS student_features (
      id TEXT PRIMARY KEY,
      student_id TEXT UNIQUE NOT NULL,
      current_cgpa REAL NOT NULL,
      previous_cgpa REAL NOT NULL,
      cgpa_decline REAL NOT NULL,
      attendance_rate REAL NOT NULL,
      recent_attendance_drop REAL NOT NULL,
      backlog_count INTEGER NOT NULL,
      failed_subject_count INTEGER NOT NULL,
      assignment_completion_rate REAL NOT NULL,
      lms_engagement_score REAL NOT NULL,
      internal_exam_avg REAL NOT NULL,
      absence_frequency INTEGER NOT NULL,
      calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- Model Versions
    CREATE TABLE IF NOT EXISTS model_versions (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      algorithm TEXT NOT NULL,
      version TEXT NOT NULL,
      trained_date TEXT NOT NULL,
      dataset_version TEXT NOT NULL,
      features_json TEXT NOT NULL,
      metrics_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'ACTIVE',
      is_default INTEGER NOT NULL DEFAULT 0,
      notes TEXT
    );

    -- Risk Predictions
    CREATE TABLE IF NOT EXISTS risk_predictions (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      risk_probability REAL NOT NULL,
      risk_level TEXT NOT NULL CHECK(risk_level IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')),
      model_version_id TEXT NOT NULL,
      baseline_probability REAL NOT NULL,
      human_summary TEXT NOT NULL,
      is_dynamic_followup INTEGER NOT NULL DEFAULT 0,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
      FOREIGN KEY (model_version_id) REFERENCES model_versions(id)
    );

    -- Risk Factors (Explainability / SHAP)
    CREATE TABLE IF NOT EXISTS risk_factors (
      id TEXT PRIMARY KEY,
      prediction_id TEXT NOT NULL,
      feature_key TEXT NOT NULL,
      feature_label TEXT NOT NULL,
      feature_value TEXT NOT NULL,
      shap_value REAL NOT NULL,
      relative_impact TEXT NOT NULL,
      direction TEXT NOT NULL,
      human_description TEXT NOT NULL,
      FOREIGN KEY (prediction_id) REFERENCES risk_predictions(id) ON DELETE CASCADE
    );

    -- Interventions
    CREATE TABLE IF NOT EXISTS interventions (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      faculty_id TEXT NOT NULL,
      risk_level TEXT NOT NULL,
      risk_probability REAL NOT NULL,
      detected_risk_factors TEXT NOT NULL,
      ai_recommendation TEXT NOT NULL,
      selected_intervention TEXT NOT NULL,
      faculty_notes TEXT NOT NULL,
      action_items TEXT NOT NULL,
      assigned_date TEXT NOT NULL,
      follow_up_date TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'PLANNED',
      outcome TEXT NOT NULL DEFAULT 'PENDING',
      post_risk_probability REAL,
      post_risk_level TEXT,
      last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
      FOREIGN KEY (faculty_id) REFERENCES faculty(id)
    );

    -- Follow-ups
    CREATE TABLE IF NOT EXISTS follow_ups (
      id TEXT PRIMARY KEY,
      intervention_id TEXT NOT NULL,
      student_id TEXT NOT NULL,
      faculty_id TEXT NOT NULL,
      scheduled_date TEXT NOT NULL,
      completed_date TEXT,
      observations TEXT NOT NULL,
      student_feedback TEXT,
      status TEXT NOT NULL DEFAULT 'PENDING',
      updated_attendance REAL,
      updated_cgpa REAL,
      updated_backlogs INTEGER,
      new_risk_prob REAL,
      new_risk_level TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE,
      FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
      FOREIGN KEY (faculty_id) REFERENCES faculty(id)
    );

    -- Notifications
    CREATE TABLE IF NOT EXISTS notifications (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      title TEXT NOT NULL,
      message TEXT NOT NULL,
      type TEXT NOT NULL,
      is_read INTEGER NOT NULL DEFAULT 0,
      link_url TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Audit Logs
    CREATE TABLE IF NOT EXISTS audit_logs (
      id TEXT PRIMARY KEY,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      user_id TEXT NOT NULL,
      user_email TEXT NOT NULL,
      user_role TEXT NOT NULL,
      action TEXT NOT NULL,
      entity TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      previous_value TEXT,
      new_value TEXT
    );

    -- System Settings
    CREATE TABLE IF NOT EXISTS system_settings (
      id TEXT PRIMARY KEY,
      institution_name TEXT NOT NULL,
      low_max REAL NOT NULL DEFAULT 30.0,
      moderate_max REAL NOT NULL DEFAULT 55.0,
      high_max REAL NOT NULL DEFAULT 75.0,
      critical_min REAL NOT NULL DEFAULT 76.0,
      attendance_warning_threshold REAL NOT NULL DEFAULT 75.0,
      cgpa_decline_threshold REAL NOT NULL DEFAULT 0.5,
      active_model_id TEXT NOT NULL,
      allow_faculty_override INTEGER NOT NULL DEFAULT 1,
      auto_alert_admins INTEGER NOT NULL DEFAULT 1,
      last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Performance Indexes
    CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department_id);
    CREATE INDEX IF NOT EXISTS idx_students_faculty ON students(assigned_faculty_id);
    CREATE INDEX IF NOT EXISTS idx_predictions_student ON risk_predictions(student_id);
    CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON risk_predictions(timestamp);
    CREATE INDEX IF NOT EXISTS idx_interventions_student ON interventions(student_id);
    CREATE INDEX IF NOT EXISTS idx_interventions_faculty ON interventions(faculty_id);
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
  `;

  db.run(schemaSQL);
  saveDb();
}
