/// SYNTHETIC rows shaped like the V2–V4 database functions and tables.
library;

Map<String, dynamic> caseloadRow({
  String studentId = 's1',
  String name = 'Synthetic Student Beta',
  String? level = 'high',
  String trajectory = 'rapidly_increasing',
  num? delta = 0.18,
  int open = 1,
}) =>
    {
      'student_id': studentId,
      'full_name': name,
      'roll_number': 'SYN-$studentId',
      'current_semester': 3,
      'risk_level': level,
      'risk_probability': level == null ? null : 0.74,
      'trajectory': level == null ? null : trajectory,
      'risk_delta': level == null ? null : delta,
      'prediction_date': level == null ? null : '2026-09-20',
      'data_provenance': level == null ? null : 'synthetic',
      'open_interventions': open,
    };

Map<String, dynamic> trendRow(String week, {int attended = 4, int counted = 5, num? score = 62.5}) => {
      'week_start': week,
      'attendance_attended': attended,
      'attendance_counted': counted,
      'assignments_due': 2,
      'assignments_submitted': 1,
      'mean_score_pct': score,
      'engagement_events': 14,
      'quiz_attempts': 2,
    };

Map<String, dynamic> interventionRow({
  String id = 'i1',
  String studentId = 's1',
  String type = 'attendance_follow_up',
  String status = 'recommended',
  String source = 'model_rule',
  String? ruleId = 'attendance.below_requirement',
  String? outcome,
  String? declineReason,
}) =>
    {
      'id': id,
      'student_id': studentId,
      'intervention_type': type,
      'status': status,
      'source': source,
      'reason': 'Attendance in the last 14 days was 50%, below the 75% requirement.',
      'priority': 'high',
      'rule_id': ruleId,
      'created_at': '2026-09-21T06:00:00Z',
      'due_on': null,
      'outcome': outcome,
      'decline_reason': declineReason,
    };

Map<String, dynamic> registryRow({String status = 'development'}) => {
      'id': 'm1',
      'version': 'seed-demo-0',
      'model_name': 'seed-demo',
      'target': 'academic',
      'status': status,
      'data_provenance': 'synthetic',
      'feature_version': 'seed-demo-0',
      'training_timestamp': '2026-09-01T00:00:00Z',
      'institution_id': null,
    };

Map<String, dynamic> driftAlertRow() => {
      'id': 'al1',
      'model_registry_id': 'm1',
      'alert_type': 'prediction_drift',
      'subject': 'prediction',
      'statistic': 'psi',
      'value': 0.41,
      'threshold': 0.25,
      'severity': 'critical',
      'status': 'open',
      'created_at': '2026-09-22T00:00:00Z',
    };

Map<String, dynamic> snapshotRow() => {
      'model_registry_id': 'm1',
      'window_start': '2026-09-15',
      'window_end': '2026-09-21',
      'n_predictions': 3,
      'labels_available': 0,
    };
