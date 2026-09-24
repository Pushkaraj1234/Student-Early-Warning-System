import 'package:sews_mobile/core/data/json.dart';

enum NotificationType {
  riskUpdate('risk_update'),
  intervention('intervention'),
  assignmentDue('assignment_due'),
  attendanceAlert('attendance_alert'),
  system('system'),
  newIntervention('new_intervention'),
  riskChange('risk_change'),
  mentorMessage('mentor_message'),
  academicSignal('academic_signal'),
  studentCheckin('student_checkin');

  const NotificationType(this.dbValue);

  final String dbValue;
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    required this.createdAt,
    this.readAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) => AppNotification(
        id: Json.string(json, 'id'),
        type: Json.enumValue(json, 'notification_type', {for (final t in NotificationType.values) t.dbValue: t}),
        title: Json.string(json, 'title'),
        body: Json.string(json, 'body'),
        readAt: Json.dateTimeOrNull(json, 'read_at'),
        createdAt: Json.dateTime(json, 'created_at'),
      );

  static const String columns = 'id, notification_type, title, body, read_at, created_at';

  final String id;
  final NotificationType type;
  final String title;
  final String body;
  final DateTime? readAt;
  final DateTime createdAt;

  bool get isRead => readAt != null;

  /// Staff alert types shown in the mentor dashboard's "recent alerts".
  bool get isStaffAlert => const {
        NotificationType.riskChange,
        NotificationType.academicSignal,
        NotificationType.studentCheckin,
      }.contains(type);
}
