import 'package:sews_mobile/core/data/json.dart';

/// Intervention types from the database's controlled vocabulary, with plain-language
/// names. These describe the action type only; they are not model explanations.
enum InterventionType {
  mentorMeeting('mentor_meeting', 'Meet your mentor', 'A conversation with your mentor has been suggested.'),
  academicCounselling('academic_counselling', 'Academic counselling',
      'A session with an academic counsellor has been suggested.'),
  attendanceFollowUp('attendance_follow_up', 'Attendance follow-up',
      'A follow-up about your attendance has been suggested.'),
  assignmentSupport('assignment_support', 'Assignment support',
      'Support with upcoming or missed assignments has been suggested.'),
  peerTutoring('peer_tutoring', 'Peer tutoring', 'Study sessions with a peer tutor have been suggested.'),
  wellbeingReferral('wellbeing_referral', 'Wellbeing support',
      'A conversation with the student wellbeing service has been suggested.'),
  studyPlanning('study_planning', 'Study planning', 'Help with planning your study time has been suggested.'),
  academicTutoring('academic_tutoring', 'Academic tutoring', 'Tutoring for your courses has been suggested.'),
  financialSupportReferral('financial_support_referral', 'Financial support information',
      "Information about the institution's financial support options has been suggested.");

  const InterventionType(this.dbValue, this.title, this.description);

  final String dbValue;
  final String title;
  final String description;
}

/// Statuses a STUDENT can see. Rule suggestions ('recommended') stay hidden until a
/// mentor reviews them, so the student list only ever contains offers and accepted actions.
enum ActionStatus {
  pending('pending', 'Offered to you'),
  accepted('accepted', 'Accepted');

  const ActionStatus(this.dbValue, this.label);

  final String dbValue;
  final String label;
}

/// Reasons a student may give when declining (the database's controlled list).
enum DeclineReason {
  notNeeded('not_needed', "I don't need this right now"),
  alreadyReceivingSupport('already_receiving_support', "I'm already getting support"),
  notConvenient('not_convenient', "The timing doesn't work for me"),
  other('other', 'Another reason');

  const DeclineReason(this.dbValue, this.label);

  final String dbValue;
  final String label;
}

/// Row returned by `public.get_my_recommended_actions()` — a student-safe projection
/// without staff notes or staff identifiers.
class RecommendedAction {
  const RecommendedAction({
    required this.id,
    required this.type,
    required this.status,
    required this.createdAt,
    this.dueOn,
  });

  factory RecommendedAction.fromJson(Map<String, dynamic> json) => RecommendedAction(
        id: Json.string(json, 'id'),
        type: Json.enumValue(json, 'intervention_type', {for (final t in InterventionType.values) t.dbValue: t}),
        status: Json.enumValue(json, 'status', {for (final s in ActionStatus.values) s.dbValue: s}),
        dueOn: Json.dateOrNull(json, 'due_on'),
        createdAt: Json.dateTime(json, 'created_at'),
      );

  final String id;
  final InterventionType type;
  final ActionStatus status;
  final DateTime? dueOn;
  final DateTime createdAt;

  /// Only offers wait for the student's answer.
  bool get awaitsResponse => status == ActionStatus.pending;
}
