/**
 * Student Early Warning System (SEWS)
 * Synthetic Academic Dataset & Database Seeder
 * 
 * Generates realistic synthetic data (~120 students across 4 departments)
 * covering diverse profiles: high-achieving, low-attendance, declining,
 * backlogs, and post-intervention improved students.
 */

import { Database } from 'sql.js';
import bcrypt from 'bcryptjs';
import { TRAINED_MODELS, predictStudentRisk, generateInterventionRecommendation } from './mlEngine.js';
import { StudentFeatures } from '../src/types.js';
import { saveDb } from './db.js';

export async function seedDatabaseIfEmpty(db: Database): Promise<void> {
  // Check if users already exist
  const res = db.exec("SELECT COUNT(*) as count FROM users;");
  const count = res.length > 0 && res[0].values.length > 0 ? (res[0].values[0][0] as number) : 0;
  if (count > 0) {
    return; // Already seeded
  }

  console.log("Seeding synthetic academic dataset into database...");

  const passwordHash = await bcrypt.hash("Admin@123", 10);
  const facultyPasswordHash = await bcrypt.hash("Faculty@123", 10);
  const studentPasswordHash = await bcrypt.hash("Student@123", 10);

  // 1. Seed System Settings
  db.run(`
    INSERT INTO system_settings (
      id, institution_name, low_max, moderate_max, high_max, critical_min,
      attendance_warning_threshold, cgpa_decline_threshold, active_model_id,
      allow_faculty_override, auto_alert_admins, last_updated
    ) VALUES (
      'default-settings', 'National Institute of Engineering & Technology',
      30.0, 55.0, 75.0, 76.0, 75.0, 0.5, 'xgb-v2', 1, 1, CURRENT_TIMESTAMP
    );
  `);

  // 2. Seed Model Versions & Metrics
  for (const [id, model] of Object.entries(TRAINED_MODELS)) {
    db.run(`
      INSERT INTO model_versions (
        id, name, algorithm, version, trained_date, dataset_version,
        features_json, metrics_json, status, is_default, notes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    `, [
      id,
      model.name,
      model.algorithm,
      model.version,
      '2026-08-15',
      'DS-SYNTH-v2.4',
      JSON.stringify(Object.keys(model.weights).filter(k => k !== 'bias')),
      JSON.stringify(model.metrics),
      'ACTIVE',
      id === 'xgb-v2' ? 1 : 0,
      model.notes
    ]);
  }

  // 3. Seed Departments
  const departments = [
    { id: 'dept-cse', code: 'CSE', name: 'Computer Science & Engineering', hod: 'Dr. K. S. Sundaram' },
    { id: 'dept-ece', code: 'ECE', name: 'Electronics & Communication Engineering', hod: 'Dr. Meenakshi Rao' },
    { id: 'dept-it', code: 'IT', name: 'Information Technology', hod: 'Dr. Arvind Deshmukh' },
    { id: 'dept-me', code: 'ME', name: 'Mechanical Engineering', hod: 'Dr. Vikram Malhotra' }
  ];

  for (const d of departments) {
    db.run("INSERT INTO departments (id, code, name, hod_name) VALUES (?, ?, ?, ?);", [d.id, d.code, d.name, d.hod]);
  }

  // 4. Seed Subjects
  const subjects = [
    // CSE Sem 6
    { id: 'sub-cse-601', code: 'CS601', name: 'Design & Analysis of Algorithms', dept: 'dept-cse', credits: 4, sem: 6 },
    { id: 'sub-cse-602', code: 'CS602', name: 'Machine Learning & Neural Networks', dept: 'dept-cse', credits: 4, sem: 6 },
    { id: 'sub-cse-603', code: 'CS603', name: 'Database Management Systems', dept: 'dept-cse', credits: 3, sem: 6 },
    { id: 'sub-cse-604', code: 'CS604', name: 'Software Engineering & Agile Methodologies', dept: 'dept-cse', credits: 3, sem: 6 },
    { id: 'sub-cse-605', code: 'CS605', name: 'Cloud Computing Architecture', dept: 'dept-cse', credits: 3, sem: 6 },
    // ECE Sem 6
    { id: 'sub-ece-601', code: 'EC601', name: 'Digital Signal Processing', dept: 'dept-ece', credits: 4, sem: 6 },
    { id: 'sub-ece-602', code: 'EC602', name: 'VLSI Design & Systems', dept: 'dept-ece', credits: 4, sem: 6 },
    { id: 'sub-ece-603', code: 'EC603', name: 'Embedded Systems & IoT', dept: 'dept-ece', credits: 3, sem: 6 },
    // IT Sem 6
    { id: 'sub-it-601', code: 'IT601', name: 'Distributed Systems & Microservices', dept: 'dept-it', credits: 4, sem: 6 },
    { id: 'sub-it-602', code: 'IT602', name: 'Information Security & Cryptography', dept: 'dept-it', credits: 3, sem: 6 }
  ];

  for (const s of subjects) {
    db.run("INSERT INTO subjects (id, code, name, department_id, credits, semester) VALUES (?, ?, ?, ?, ?, ?);",
      [s.id, s.code, s.name, s.dept, s.credits, s.sem]);
  }

  // 5. Seed Users & Faculty
  // Admin
  db.run(`
    INSERT INTO users (id, email, password_hash, name, role, department_id, created_at)
    VALUES ('user-admin', 'admin@sews.edu', ?, 'Prof. Ramesh Chandra (Academic Dean)', 'ADMIN', 'dept-cse', CURRENT_TIMESTAMP);
  `, [passwordHash]);

  // Faculty 1: Dr. Rajesh Sharma (CSE)
  db.run(`
    INSERT INTO users (id, email, password_hash, name, role, department_id, created_at)
    VALUES ('user-fac-1', 'faculty.sharma@sews.edu', ?, 'Dr. Rajesh Sharma', 'FACULTY', 'dept-cse', CURRENT_TIMESTAMP);
  `, [facultyPasswordHash]);
  db.run(`
    INSERT INTO faculty (id, user_id, name, email, department_id, designation)
    VALUES ('fac-1', 'user-fac-1', 'Dr. Rajesh Sharma', 'faculty.sharma@sews.edu', 'dept-cse', 'Associate Professor & Mentor');
  `);

  // Faculty 2: Prof. Ananya Patel (ECE)
  db.run(`
    INSERT INTO users (id, email, password_hash, name, role, department_id, created_at)
    VALUES ('user-fac-2', 'faculty.patel@sews.edu', ?, 'Prof. Ananya Patel', 'FACULTY', 'dept-ece', CURRENT_TIMESTAMP);
  `, [facultyPasswordHash]);
  db.run(`
    INSERT INTO faculty (id, user_id, name, email, department_id, designation)
    VALUES ('fac-2', 'user-fac-2', 'Prof. Ananya Patel', 'faculty.patel@sews.edu', 'dept-ece', 'Assistant Professor & Mentor');
  `);

  // 6. Generate 120 Synthetic Students
  const firstNames = [
    'Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Sai', 'Reyansh', 'Ayaan', 'Krishna', 'Ishaan',
    'Shaurya', 'Atharv', 'Advik', 'Pranav', 'Advaith', 'Aayush', 'Dhruv', 'Kabir', 'Rohan', 'Karan',
    'Diya', 'Saanvi', 'Ananya', 'Aadhya', 'Pari', 'Anika', 'Navya', 'Angel', 'Isha', 'Myra',
    'Riya', 'Shreya', 'Kavya', 'Avani', 'Sneha', 'Tanvi', 'Khushi', 'Pooja', 'Neha', 'Nisha'
  ];

  const lastNames = [
    'Sharma', 'Verma', 'Gupta', 'Mehta', 'Patel', 'Reddy', 'Chopra', 'Nair', 'Iyer', 'Singh',
    'Kumar', 'Joshi', 'Bhat', 'Deshmukh', 'Kulkarni', 'Pillai', 'Rao', 'Das', 'Sen', 'Ghosh',
    'Mukherjee', 'Banerjee', 'Mishra', 'Pandey', 'Tiwari', 'Bhattacharya', 'Chauhan', 'Saxena', 'Kapoor', 'Malhotra'
  ];

  // Specific highlighted key demo students
  const specialStudents = [
    {
      id: 'STU1024',
      name: 'Aarav Verma',
      email: 'stu1024@sews.edu',
      dept: 'dept-cse',
      cgpa: 5.82,
      prevCgpa: 7.20,
      backlogs: 2,
      failedSubjects: 1,
      attendance: 61.5,
      drop: 18.0,
      assignments: 60,
      internal: 42,
      lms: 34,
      absence: 9,
      status: 'UNDER_REVIEW',
      faculty: 'fac-1'
    },
    {
      id: 'STU1045',
      name: 'Riya Sen',
      email: 'stu1045@sews.edu',
      dept: 'dept-cse',
      cgpa: 6.95,
      prevCgpa: 7.30,
      backlogs: 0,
      failedSubjects: 0,
      attendance: 72.0,
      drop: 11.0,
      assignments: 75,
      internal: 58,
      lms: 55,
      absence: 5,
      status: 'REGULAR',
      faculty: 'fac-1'
    },
    {
      id: 'STU1001',
      name: 'Anika Gupta',
      email: 'stu1001@sews.edu',
      dept: 'dept-it',
      cgpa: 9.25,
      prevCgpa: 9.15,
      backlogs: 0,
      failedSubjects: 0,
      attendance: 94.0,
      drop: 1.0,
      assignments: 100,
      internal: 92,
      lms: 95,
      absence: 1,
      status: 'REGULAR',
      faculty: 'fac-1'
    },
    {
      id: 'STU1088',
      name: 'Kabir Mukherjee',
      email: 'stu1088@sews.edu',
      dept: 'dept-ece',
      cgpa: 5.10,
      prevCgpa: 6.50,
      backlogs: 3,
      failedSubjects: 2,
      attendance: 54.0,
      drop: 22.0,
      assignments: 45,
      internal: 38,
      lms: 22,
      absence: 12,
      status: 'PROBATION',
      faculty: 'fac-2'
    },
    {
      id: 'STU1012',
      name: 'Rohan Deshmukh',
      email: 'stu1012@sews.edu',
      dept: 'dept-cse',
      cgpa: 6.45,
      prevCgpa: 6.10, // improving post-intervention!
      backlogs: 1,
      failedSubjects: 0,
      attendance: 78.5,
      drop: -6.0, // attendance actually increased
      assignments: 82,
      internal: 68,
      lms: 72,
      absence: 3,
      status: 'REGULAR',
      faculty: 'fac-1'
    }
  ];

  // Helper deterministic pseudo-random generator
  let seed = 42;
  function rnd(): number {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  }

  const allStudentConfigs: typeof specialStudents = [...specialStudents];

  for (let i = 6; i <= 120; i++) {
    const fn = firstNames[Math.floor(rnd() * firstNames.length)];
    const ln = lastNames[Math.floor(rnd() * lastNames.length)];
    const rollNum = 1100 + i;
    const id = `STU${rollNum}`;
    const email = `stu${rollNum}@sews.edu`;
    const depts = ['dept-cse', 'dept-ece', 'dept-it', 'dept-me'];
    const dept = depts[Math.floor(rnd() * depts.length)];
    const faculty = dept === 'dept-ece' ? 'fac-2' : 'fac-1';

    // Profile distribution:
    // 55% Low risk (strong/average)
    // 25% Moderate risk (borderline attendance/minor drop)
    // 12% High risk (notable drop/backlog)
    // 8% Critical risk (heavy absence/multiple backlogs)
    const profileType = rnd();

    let cgpa = 7.8;
    let prevCgpa = 7.7;
    let backlogs = 0;
    let failedSubjects = 0;
    let attendance = 85.0;
    let drop = 2.0;
    let assignments = 90;
    let internal = 75;
    let lms = 70;
    let absence = 2;
    let status = 'REGULAR';

    if (profileType < 0.08) {
      // Critical
      cgpa = Math.round((4.8 + rnd() * 1.2) * 100) / 100;
      prevCgpa = Math.round((cgpa + 0.8 + rnd() * 0.9) * 100) / 100;
      backlogs = Math.floor(2 + rnd() * 3);
      failedSubjects = Math.floor(1 + rnd() * 2);
      attendance = Math.round((50 + rnd() * 16) * 10) / 10;
      drop = Math.round((14 + rnd() * 12) * 10) / 10;
      assignments = Math.floor(40 + rnd() * 25);
      internal = Math.floor(35 + rnd() * 15);
      lms = Math.floor(20 + rnd() * 25);
      absence = Math.floor(8 + rnd() * 6);
      status = 'PROBATION';
    } else if (profileType < 0.20) {
      // High
      cgpa = Math.round((6.0 + rnd() * 0.9) * 100) / 100;
      prevCgpa = Math.round((cgpa + 0.5 + rnd() * 0.6) * 100) / 100;
      backlogs = Math.floor(1 + rnd() * 2);
      failedSubjects = Math.floor(rnd() * 1.5);
      attendance = Math.round((64 + rnd() * 10) * 10) / 10;
      drop = Math.round((9 + rnd() * 8) * 10) / 10;
      assignments = Math.floor(60 + rnd() * 18);
      internal = Math.floor(48 + rnd() * 16);
      lms = Math.floor(40 + rnd() * 22);
      absence = Math.floor(5 + rnd() * 4);
      status = 'UNDER_REVIEW';
    } else if (profileType < 0.45) {
      // Moderate
      cgpa = Math.round((6.8 + rnd() * 0.9) * 100) / 100;
      prevCgpa = Math.round((cgpa + 0.1 + rnd() * 0.4) * 100) / 100;
      backlogs = Math.floor(rnd() * 1.2);
      failedSubjects = 0;
      attendance = Math.round((73 + rnd() * 6) * 10) / 10;
      drop = Math.round((4 + rnd() * 6) * 10) / 10;
      assignments = Math.floor(72 + rnd() * 16);
      internal = Math.floor(60 + rnd() * 15);
      lms = Math.floor(55 + rnd() * 20);
      absence = Math.floor(3 + rnd() * 3);
      status = 'REGULAR';
    } else {
      // Low Risk
      cgpa = Math.round((7.8 + rnd() * 1.8) * 100) / 100;
      prevCgpa = Math.round((cgpa - 0.2 + rnd() * 0.4) * 100) / 100;
      backlogs = 0;
      failedSubjects = 0;
      attendance = Math.round((84 + rnd() * 14) * 10) / 10;
      drop = Math.round((rnd() * 3.5) * 10) / 10;
      assignments = Math.floor(88 + rnd() * 12);
      internal = Math.floor(75 + rnd() * 20);
      lms = Math.floor(70 + rnd() * 25);
      absence = Math.floor(rnd() * 2.5);
      status = 'REGULAR';
    }

    allStudentConfigs.push({
      id,
      name: `${fn} ${ln}`,
      email,
      dept,
      cgpa,
      prevCgpa,
      backlogs,
      failedSubjects,
      attendance,
      drop,
      assignments,
      internal,
      lms,
      absence,
      status,
      faculty
    });
  }

  // Insert students, accounts, features, and run initial ML prediction
  for (const stu of allStudentConfigs) {
    const userId = `user-${stu.id.toLowerCase()}`;
    // Insert student user account so student can log in
    db.run(`
      INSERT INTO users (id, email, password_hash, name, role, department_id, student_id, created_at)
      VALUES (?, ?, ?, ?, 'STUDENT', ?, ?, CURRENT_TIMESTAMP);
    `, [userId, stu.email, studentPasswordHash, stu.name, stu.dept, stu.id]);

    // Insert student table
    db.run(`
      INSERT INTO students (
        id, user_id, name, email, department_id, program, semester, division,
        admission_year, current_cgpa, previous_cgpa, backlog_count, academic_status,
        assigned_faculty_id, created_at
      ) VALUES (?, ?, ?, ?, ?, 'B.Tech Computer Science & Engineering', 6, 'A', 2023, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    `, [stu.id, userId, stu.name, stu.email, stu.dept, stu.cgpa, stu.prevCgpa, stu.backlogs, stu.status, stu.faculty]);

    // Insert academic historical records (Semesters 1 - 5)
    for (let sem = 1; sem <= 5; sem++) {
      const gpa = Math.round((stu.cgpa + (sem === 5 ? (stu.cgpa - stu.prevCgpa) : (rnd() * 0.4 - 0.2))) * 100) / 100;
      db.run(`
        INSERT INTO academic_records (
          id, student_id, semester, gpa, total_credits, credits_earned, failed_subjects, academic_year
        ) VALUES (?, ?, ?, ?, 24, ?, ?, ?);
      `, [
        `acad-${stu.id}-sem${sem}`,
        stu.id,
        sem,
        Math.max(4.0, Math.min(10.0, gpa)),
        sem === 5 && stu.failedSubjects > 0 ? (24 - stu.failedSubjects * 4) : 24,
        sem === 5 ? stu.failedSubjects : 0,
        `202${2 + Math.floor(sem / 2)}-202${3 + Math.floor(sem / 2)}`
      ]);
    }

    // Insert attendance record
    db.run(`
      INSERT INTO attendance_records (
        id, student_id, month_year, classes_held, classes_attended, percentage, recent_drop_rate, recorded_at
      ) VALUES (?, ?, 'Sep 2026', 120, ?, ?, ?, CURRENT_TIMESTAMP);
    `, [
      `att-${stu.id}`,
      stu.id,
      Math.round(120 * (stu.attendance / 100)),
      stu.attendance,
      stu.drop
    ]);

    // Insert LMS Activity
    db.run(`
      INSERT INTO lms_activity (
        id, student_id, weekly_logins, active_hours, resources_accessed, quiz_participation_rate, recorded_at
      ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    `, [
      `lms-${stu.id}`,
      stu.id,
      Math.floor(stu.lms / 10),
      Math.round((stu.lms / 12) * 10) / 10,
      Math.floor(stu.lms * 0.8),
      stu.lms
    ]);

    // Insert Subject Assessment Record
    db.run(`
      INSERT INTO assessment_records (
        id, student_id, subject_id, semester, internal_ut1, internal_ut2, max_internal, attendance_pct, assignments_submitted, assignments_total, status
      ) VALUES (?, ?, 'sub-cse-601', 6, ?, ?, 30, ?, ?, 6, ?);
    `, [
      `assess-${stu.id}`,
      stu.id,
      Math.round((stu.internal / 100) * 30 * 10) / 10,
      Math.round(((stu.internal + (rnd() * 8 - 4)) / 100) * 30 * 10) / 10,
      stu.attendance,
      Math.round((stu.assignments / 100) * 6),
      stu.internal < 50 ? 'AT_RISK' : (stu.internal < 65 ? 'BORDERLINE' : 'PASSING')
    ]);

    // Calculate and store feature vector
    const features: StudentFeatures = {
      studentId: stu.id,
      currentCGPA: stu.cgpa,
      previousCGPA: stu.prevCgpa,
      cgpaDecline: Math.round((stu.prevCgpa - stu.cgpa) * 100) / 100,
      attendanceRate: stu.attendance,
      recentAttendanceDrop: stu.drop,
      backlogCount: stu.backlogs,
      failedSubjectCount: stu.failedSubjects,
      assignmentCompletionRate: stu.assignments,
      lmsEngagementScore: stu.lms,
      internalExamAvg: stu.internal,
      absenceFrequency: stu.absence,
      calculatedAt: new Date().toISOString()
    };

    db.run(`
      INSERT INTO student_features (
        id, student_id, current_cgpa, previous_cgpa, cgpa_decline, attendance_rate,
        recent_attendance_drop, backlog_count, failed_subject_count,
        assignment_completion_rate, lms_engagement_score, internal_exam_avg,
        absence_frequency, calculated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    `, [
      `feat-${stu.id}`,
      stu.id,
      features.currentCGPA,
      features.previousCGPA,
      features.cgpaDecline,
      features.attendanceRate,
      features.recentAttendanceDrop,
      features.backlogCount,
      features.failedSubjectCount,
      features.assignmentCompletionRate,
      features.lmsEngagementScore,
      features.internalExamAvg,
      features.absenceFrequency
    ]);

    // Run ML Prediction & SHAP Engine
    const prediction = predictStudentRisk(features);
    const predId = `pred-${stu.id}-01`;

    db.run(`
      INSERT INTO risk_predictions (
        id, student_id, risk_probability, risk_level, model_version_id,
        baseline_probability, human_summary, is_dynamic_followup, timestamp
      ) VALUES (?, ?, ?, ?, 'xgb-v2', ?, ?, 0, CURRENT_TIMESTAMP);
    `, [
      predId,
      stu.id,
      prediction.riskProbability,
      prediction.riskLevel,
      prediction.baselineProbability,
      prediction.humanSummary
    ]);

    // Store SHAP Risk Factors
    for (const factor of prediction.contributingFactors) {
      db.run(`
        INSERT INTO risk_factors (
          id, prediction_id, feature_key, feature_label, feature_value,
          shap_value, relative_impact, direction, human_description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
      `, [
        `rf-${predId}-${factor.featureKey}`,
        predId,
        factor.featureKey,
        factor.featureLabel,
        String(factor.featureValue),
        factor.shapValue,
        factor.relativeImpact,
        factor.direction,
        factor.humanDescription
      ]);
    }

    // If student is STU1024 or STU1088, seed realistic intervention and follow-up
    if (stu.id === 'STU1024') {
      const rec = generateInterventionRecommendation(prediction.riskLevel, prediction.detectedRiskFactors, features);
      const intId = 'int-stu1024';

      db.run(`
        INSERT INTO interventions (
          id, student_id, faculty_id, risk_level, risk_probability,
          detected_risk_factors, ai_recommendation, selected_intervention,
          faculty_notes, action_items, assigned_date, follow_up_date, status, outcome,
          last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-09-05', '2026-09-25', 'IN_PROGRESS', 'PENDING', CURRENT_TIMESTAMP);
      `, [
        intId,
        stu.id,
        'fac-1',
        prediction.riskLevel,
        prediction.riskProbability,
        JSON.stringify(prediction.detectedRiskFactors),
        rec.title + ': ' + rec.rationale,
        'Multidisciplinary Attendance Recovery & Remedial Class Enrollment',
        'Met with Aarav on Sep 5. Identified severe scheduling disruption and difficulty with Design of Algorithms. Agreed to remedial clinic and weekly attendance reporting.',
        JSON.stringify(rec.suggestedActionItems)
      ]);

      // Seed scheduled follow-up
      db.run(`
        INSERT INTO follow_ups (
          id, intervention_id, student_id, faculty_id, scheduled_date, observations, status
        ) VALUES (?, ?, ?, ?, '2026-09-25', 'Review first 20 days of remedial clinic attendance and Unit Test 2 marks.', 'PENDING');
      `, [`fu-${intId}`, intId, stu.id, 'fac-1']);

      // Seed faculty notification
      db.run(`
        INSERT INTO notifications (id, user_id, title, message, type, is_read, link_url, created_at)
        VALUES ('notif-01', 'user-fac-1', 'CRITICAL Risk Alert: Aarav Verma', 'Aarav Verma (STU-1024) has reached an estimated risk score of 82.5%. Mentor review recommended.', 'RISK_ALERT', 0, '/faculty/student/STU1024', CURRENT_TIMESTAMP);
      `);

      // Seed student notification
      db.run(`
        INSERT INTO notifications (id, user_id, title, message, type, is_read, link_url, created_at)
        VALUES ('notif-02', ?, 'Supportive Academic Check-in Scheduled', 'Dr. Rajesh Sharma has scheduled an academic support review to assist your progress.', 'INTERVENTION', 0, '/student/interventions', CURRENT_TIMESTAMP);
      `, [userId]);
    }

    // If student is STU1012 (improving student demo), seed dynamic re-evaluation!
    if (stu.id === 'STU1012') {
      // Previous baseline prediction from 4 weeks ago (High risk 71%)
      const oldPredId = 'pred-stu1012-old';
      db.run(`
        INSERT INTO risk_predictions (
          id, student_id, risk_probability, risk_level, model_version_id,
          baseline_probability, human_summary, is_dynamic_followup, timestamp
        ) VALUES (?, ?, 71.2, 'HIGH', 'xgb-v2', 28.5, 'Previous assessment indicated elevated risk due to attendance drop and backlog.', 0, datetime('now', '-30 days'));
      `, [oldPredId, stu.id]);

      const intId = 'int-stu1012';
      db.run(`
        INSERT INTO interventions (
          id, student_id, faculty_id, risk_level, risk_probability,
          detected_risk_factors, ai_recommendation, selected_intervention,
          faculty_notes, action_items, assigned_date, follow_up_date, status, outcome,
          post_risk_probability, post_risk_level, last_updated
        ) VALUES (?, ?, ?, 'HIGH', 71.2, ?, 'Attendance Recovery & Backlog Clinic', 'Attendance Recovery & Backlog Clinic', 'Rohan followed remedial sessions consistently. Attendance recovered by +12%.', ?, datetime('now', '-28 days'), datetime('now', '-5 days'), 'COMPLETED', 'IMPROVED', 46.5, 'MODERATE', CURRENT_TIMESTAMP);
      `, [
        intId,
        stu.id,
        'fac-1',
        JSON.stringify(['Low Attendance (66%)', 'Active Backlog (1)']),
        JSON.stringify(['Weekly attendance tracking', 'Backlog mock test prep'])
      ]);

      db.run(`
        INSERT INTO follow_ups (
          id, intervention_id, student_id, faculty_id, scheduled_date, completed_date,
          observations, student_feedback, status, updated_attendance, updated_cgpa,
          updated_backlogs, new_risk_prob, new_risk_level
        ) VALUES (?, ?, ?, ?, datetime('now', '-5 days'), datetime('now', '-5 days'), 'Rohan showed commendable improvement in lecture presence and cleared unit test with 68%.', 'The remedial classes and peer tutor sessions helped me catch up on Algorithms.', 'COMPLETED', 78.5, 6.45, 1, 46.5, 'MODERATE');
      `, [`fu-${intId}`, intId, stu.id, 'fac-1']);
    }
  }

  // Seed Audit Logs
  db.run(`
    INSERT INTO audit_logs (id, timestamp, user_id, user_email, user_role, action, entity, entity_id, previous_value, new_value)
    VALUES ('audit-01', datetime('now', '-1 day'), 'user-admin', 'admin@sews.edu', 'ADMIN', 'SYSTEM_INITIALIZATION', 'SYSTEM', 'SEWS-ROOT', NULL, 'Initialized SEWS Academic Early Warning System with calibrated XGBoost model');
  `);

  db.run(`
    INSERT INTO audit_logs (id, timestamp, user_id, user_email, user_role, action, entity, entity_id, previous_value, new_value)
    VALUES ('audit-02', datetime('now', '-12 hours'), 'user-fac-1', 'faculty.sharma@sews.edu', 'FACULTY', 'CREATE_INTERVENTION', 'INTERVENTION', 'int-stu1024', NULL, 'Created Multidisciplinary Attendance Recovery & Remedial Class Enrollment for Aarav Verma');
  `);

  saveDb();
  console.log(`Successfully seeded ${allStudentConfigs.length} synthetic students and related records.`);
}
