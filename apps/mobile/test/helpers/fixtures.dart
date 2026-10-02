/// Synthetic rows shaped like the PostgREST responses for the SEWS schema.
library;

const String testUserId = '22222222-2222-4222-8222-222222222222';
const String testStudentId = '11111111-1111-4111-8111-111111111111';
const String testEmail = 'student.beta@synthetic.example.com';

Map<String, dynamic> profileRow({bool onboarded = true, String role = 'student'}) => {
      'id': testUserId,
      'role': role,
      'full_name': 'Synthetic Student Beta',
      'institution_id': 'a0000000-0000-4000-8000-000000000001',
      'onboarding_completed_at': onboarded ? '2026-09-10T10:00:00Z' : null,
      'privacy_notice_version': onboarded ? 'v1' : null,
    };

Map<String, dynamic> studentRow() => {
      'id': testStudentId,
      'roll_number': 'SYN2025002',
      'full_name': 'Synthetic Student Beta',
      'institutional_email': testEmail,
      'admission_year': 2025,
      'current_semester': 3,
      'status': 'active',
      'programmes': {'code': 'BTECH-CS', 'name': 'B.Tech Computing (synthetic)'},
    };

Map<String, dynamic> predictionRow({
  String id = 'p1',
  String level = 'high',
  String date = '2026-09-20',
  String provenance = 'synthetic',
  num probability = 0.74,
  String trajectory = 'stable',
}) =>
    {
      'id': id,
      'prediction_date': date,
      'risk_probability': probability,
      'risk_level': level,
      'model_version': 'seed-demo-0',
      'data_provenance': provenance,
      'created_at': '${date}T06:00:00Z',
      'trajectory': trajectory,
    };

Map<String, dynamic> factorRow(int rank, String feature, num? value, num contribution) => {
      'rank': rank,
      'feature': feature,
      'feature_value': value,
      'contribution': contribution,
      'direction': contribution >= 0 ? 'increases_risk' : 'decreases_risk',
    };

Map<String, dynamic> courseResultRow({
  String id = 'sc1',
  String year = '2025-26',
  int semester = 2,
  String status = 'completed',
  num? marks = 84,
  String? grade = 'A+',
}) =>
    {
      'id': id,
      'course_id': 'c-$id',
      'academic_year': year,
      'semester': semester,
      'status': status,
      'marks': marks,
      'grade': grade,
      'grade_points': grade == null ? null : 9,
      'result_published_at': grade == null ? null : '2026-06-01T00:00:00Z',
      'courses': {'code': 'SYN-$id', 'title': 'Course $id', 'credits': 4},
    };

Map<String, dynamic> semesterRow({String year = '2025-26', int semester = 2, String status = 'pass'}) => {
      'academic_year': year,
      'semester': semester,
      'sgpa': status == 'pending' ? null : 8.7,
      'cgpa': status == 'pending' ? null : 8.55,
      'credits_registered': 20,
      'credits_earned': 20,
      'result_status': status,
      'published_at': status == 'pending' ? null : '2026-06-01T00:00:00Z',
    };

Map<String, dynamic> enrolmentRow(String id, String year) => {
      'id': id,
      'course_id': 'course-$id',
      'academic_year': year,
      'courses': {'code': 'SYN-$id', 'title': 'Course $id'},
    };

Map<String, dynamic> attendanceRow(String studentCourseId, String date, String status) =>
    {'student_course_id': studentCourseId, 'attendance_date': date, 'status': status};

Map<String, dynamic> assignmentRow(String id, String dueAt) => {
      'id': id,
      'title': 'Assignment $id',
      'max_score': 20,
      'due_at': dueAt,
      'courses': {'code': 'SYN-CS201', 'title': 'Data Structures'},
    };

Map<String, dynamic> submissionRow(String assignmentId, String status, {num? score}) => {
      'assignment_id': assignmentId,
      'status': status,
      'submitted_at': status == 'submitted' || status == 'late' ? '2026-09-01T10:00:00Z' : null,
      'score': score,
    };

Map<String, dynamic> actionRow({String type = 'attendance_follow_up', String status = 'pending'}) => {
      'id': 'a1',
      'intervention_type': type,
      'status': status,
      'due_on': '2026-10-01',
      'prediction_id': 'p1',
      'created_at': '2026-09-20T06:00:00Z',
    };

Map<String, dynamic> notificationRow(String id, {bool read = false}) => {
      'id': id,
      'notification_type': 'risk_update',
      'title': 'Title $id',
      'body': 'Body $id',
      'read_at': read ? '2026-09-21T00:00:00Z' : null,
      'created_at': '2026-09-20T00:00:00Z',
    };

List<Map<String, dynamic>> platformVersionRows({String minimumApp = '2.0.0'}) => [
      {'component': 'database_schema', 'version': '4.1.0'},
      {'component': 'minimum_mobile_app', 'version': minimumApp},
      {'component': 'inference_api', 'version': '1.0.0'},
    ];
