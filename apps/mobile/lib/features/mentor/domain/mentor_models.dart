import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';

/// One mentee from `public.get_mentor_caseload()` (RLS/`is_mentor_of` decides who appears).
/// Risk fields are null when the student has no academic prediction yet.
class CaseloadEntry {
  const CaseloadEntry({
    required this.studentId,
    required this.fullName,
    required this.rollNumber,
    required this.currentSemester,
    required this.openInterventions,
    this.level,
    this.probability,
    this.trajectory,
    this.riskDelta,
    this.predictionDate,
    this.provenance,
  });

  factory CaseloadEntry.fromJson(Map<String, dynamic> json) {
    final hasPrediction = json['risk_level'] != null;
    final probability = Json.numberOrNull(json, 'risk_probability');
    if (probability != null && (probability < 0 || probability > 1)) {
      throw const FormatException('risk_probability out of range');
    }
    return CaseloadEntry(
      studentId: Json.string(json, 'student_id'),
      fullName: Json.string(json, 'full_name'),
      rollNumber: Json.string(json, 'roll_number'),
      currentSemester: Json.integer(json, 'current_semester'),
      openInterventions: Json.integer(json, 'open_interventions'),
      level: hasPrediction ? Json.enumValue(json, 'risk_level', {for (final l in RiskLevel.values) l.name: l}) : null,
      probability: probability,
      trajectory: hasPrediction ? Trajectory.parse(json, 'trajectory') : null,
      riskDelta: Json.numberOrNull(json, 'risk_delta'),
      predictionDate: Json.dateOrNull(json, 'prediction_date'),
      provenance: hasPrediction
          ? Json.enumValue(json, 'data_provenance', {for (final p in DataProvenance.values) p.name: p})
          : null,
    );
  }

  final String studentId;
  final String fullName;
  final String rollNumber;
  final int currentSemester;
  final int openInterventions;
  final RiskLevel? level;
  final num? probability;
  final Trajectory? trajectory;
  final num? riskDelta;
  final DateTime? predictionDate;
  final DataProvenance? provenance;

  bool get isRising => trajectory?.isRising ?? false;
}

/// Counts per risk level (plus students without a prediction) across a caseload.
class RiskDistribution {
  RiskDistribution(List<CaseloadEntry> caseload)
      : counts = {for (final l in RiskLevel.values) l: caseload.where((e) => e.level == l).length},
        noPrediction = caseload.where((e) => e.level == null).length,
        total = caseload.length;

  final Map<RiskLevel, int> counts;
  final int noPrediction;
  final int total;
}

/// One week from `public.get_student_weekly_trends()`; counts are raw, rates are derived here.
class WeeklyTrend {
  const WeeklyTrend({
    required this.weekStart,
    required this.attendanceAttended,
    required this.attendanceCounted,
    required this.assignmentsDue,
    required this.assignmentsSubmitted,
    required this.engagementEvents,
    required this.quizAttempts,
    this.meanScorePct,
  });

  factory WeeklyTrend.fromJson(Map<String, dynamic> json) {
    final attended = Json.integer(json, 'attendance_attended');
    final counted = Json.integer(json, 'attendance_counted');
    final due = Json.integer(json, 'assignments_due');
    final submitted = Json.integer(json, 'assignments_submitted');
    if (attended < 0 || counted < attended || due < 0 || submitted < 0) {
      throw const FormatException('Inconsistent weekly trend');
    }
    return WeeklyTrend(
      weekStart: Json.date(json, 'week_start'),
      attendanceAttended: attended,
      attendanceCounted: counted,
      assignmentsDue: due,
      assignmentsSubmitted: submitted,
      meanScorePct: Json.numberOrNull(json, 'mean_score_pct'),
      engagementEvents: Json.integer(json, 'engagement_events'),
      quizAttempts: Json.integer(json, 'quiz_attempts'),
    );
  }

  final DateTime weekStart;
  final int attendanceAttended;
  final int attendanceCounted;
  final int assignmentsDue;
  final int assignmentsSubmitted;
  final num? meanScorePct;
  final int engagementEvents;
  final int quizAttempts;

  /// Null when no sessions were recorded that week (never shown as 0%).
  double? get attendanceRate => attendanceCounted == 0 ? null : attendanceAttended / attendanceCounted;
}

enum InterventionStatus {
  recommended('recommended', 'Suggested — needs review'),
  pending('pending', 'Offered, awaiting student'),
  accepted('accepted', 'Accepted'),
  declined('declined', 'Declined by student'),
  completed('completed', 'Completed'),
  cancelled('cancelled', 'Cancelled');

  const InterventionStatus(this.dbValue, this.label);

  final String dbValue;
  final String label;

  bool get isOpen => this == recommended || this == pending || this == accepted;
}

enum InterventionPriority {
  low('low', 'Low'),
  medium('medium', 'Medium'),
  high('high', 'High');

  const InterventionPriority(this.dbValue, this.label);

  final String dbValue;
  final String label;
}

enum InterventionOutcome {
  improved('improved', 'Improved'),
  noChange('no_change', 'No change'),
  worsened('worsened', 'Worsened'),
  notAssessed('not_assessed', 'Not assessed');

  const InterventionOutcome(this.dbValue, this.label);

  final String dbValue;
  final String label;
}

enum InterventionSource {
  modelRule('model_rule', 'Rule suggestion'),
  mentor('mentor', 'Mentor'),
  admin('admin', 'Admin');

  const InterventionSource(this.dbValue, this.label);

  final String dbValue;
  final String label;
}

/// An intervention as staff see it (RLS: mentors see their mentees' interventions).
class StaffIntervention {
  const StaffIntervention({
    required this.id,
    required this.studentId,
    required this.type,
    required this.status,
    required this.source,
    required this.reason,
    required this.priority,
    required this.createdAt,
    this.ruleId,
    this.dueOn,
    this.outcome,
    this.declineReason,
  });

  factory StaffIntervention.fromJson(Map<String, dynamic> json) {
    final declineRaw = json['decline_reason'];
    final outcomeRaw = json['outcome'];
    return StaffIntervention(
      id: Json.string(json, 'id'),
      studentId: Json.string(json, 'student_id'),
      type: Json.enumValue(json, 'intervention_type', {for (final t in InterventionType.values) t.dbValue: t}),
      status: Json.enumValue(json, 'status', {for (final s in InterventionStatus.values) s.dbValue: s}),
      source: Json.enumValue(json, 'source', {for (final s in InterventionSource.values) s.dbValue: s}),
      reason: Json.string(json, 'reason'),
      priority: Json.enumValue(json, 'priority', {for (final p in InterventionPriority.values) p.dbValue: p}),
      ruleId: Json.stringOrNull(json, 'rule_id'),
      createdAt: Json.dateTime(json, 'created_at'),
      dueOn: Json.dateOrNull(json, 'due_on'),
      outcome: outcomeRaw == null
          ? null
          : Json.enumValue(json, 'outcome', {for (final o in InterventionOutcome.values) o.dbValue: o}),
      declineReason: declineRaw == null
          ? null
          : Json.enumValue(json, 'decline_reason', {for (final d in DeclineReason.values) d.dbValue: d}),
    );
  }

  static const String columns =
      'id, student_id, intervention_type, status, source, reason, priority, rule_id, created_at, due_on, '
      'outcome, decline_reason';

  final String id;
  final String studentId;
  final InterventionType type;
  final InterventionStatus status;
  final InterventionSource source;
  final String reason;
  final InterventionPriority priority;
  final String? ruleId;
  final DateTime createdAt;
  final DateTime? dueOn;
  final InterventionOutcome? outcome;
  final DeclineReason? declineReason;
}

/// Intervention types staff may create by hand. Wellbeing referral stays available to
/// staff (a human decision) but is never produced by the rule engine.
const List<InterventionType> staffCreatableTypes = InterventionType.values;

/// Detail of one mentee for the mentor's student screen.
class MenteeDetail {
  const MenteeDetail({
    required this.entry,
    required this.risk,
    required this.trends,
    required this.interventions,
  });

  final CaseloadEntry entry;
  final RiskOverview risk;
  final List<WeeklyTrend> trends;
  final List<StaffIntervention> interventions;
}
