import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/mentor/domain/mentor_models.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Mentor data access. Every query runs as the signed-in mentor: RLS and the database
/// functions decide which students and interventions are visible or changeable. State
/// changes go through RPCs only; the app never writes intervention status directly.
class MentorRepository {
  MentorRepository(this._client, {this.interventionLimit = 100});

  final SupabaseClient _client;
  final int interventionLimit;

  Future<List<CaseloadEntry>> fetchCaseload() => guard(() async {
        final rows = Json.rows(await _client.rpc<dynamic>('get_mentor_caseload'));
        return rows.map(CaseloadEntry.fromJson).toList();
      });

  /// Weekly trend rows, oldest first.
  Future<List<WeeklyTrend>> fetchTrends(String studentId, {int weeks = 12}) => guard(() async {
        final rows = Json.rows(
          await _client.rpc<dynamic>('get_student_weekly_trends', params: {'p_student_id': studentId, 'p_weeks': weeks}),
        );
        final trends = rows.map(WeeklyTrend.fromJson).toList()..sort((a, b) => a.weekStart.compareTo(b.weekStart));
        return trends;
      });

  /// Interventions visible to the mentor (all mentees, or one student), newest first.
  Future<List<StaffIntervention>> fetchInterventions({String? studentId}) => guard(() async {
        var query = _client.from('interventions').select(StaffIntervention.columns);
        if (studentId != null) query = query.eq('student_id', studentId);
        final rows = Json.rows(await query.order('created_at', ascending: false).limit(interventionLimit));
        return rows.map(StaffIntervention.fromJson).toList();
      });

  /// Reviews a rule suggestion and offers it to the student.
  Future<void> approve(String interventionId) => guard(
        () => _client.rpc<dynamic>('approve_recommendation', params: {'p_intervention_id': interventionId}),
      );

  Future<String> create({
    required String studentId,
    required InterventionType type,
    required String reason,
    required InterventionPriority priority,
    DateTime? dueOn,
  }) =>
      guard(() async {
        final trimmed = reason.trim();
        if (trimmed.length < 3 || trimmed.length > 500) throw const AppFailure(FailureKind.invalidInput);
        final id = await _client.rpc<dynamic>('create_intervention', params: {
          'p_student_id': studentId,
          'p_intervention_type': type.dbValue,
          'p_reason': trimmed,
          'p_priority': priority.dbValue,
          'p_due_on': dueOn == null ? null : _date(dueOn),
        });
        if (id is! String) throw const FormatException('create_intervention returned no id');
        return id;
      });

  Future<void> complete(String interventionId, InterventionOutcome outcome) => guard(
        () => _client.rpc<dynamic>(
          'complete_intervention',
          params: {'p_intervention_id': interventionId, 'p_outcome': outcome.dbValue},
        ),
      );

  Future<void> cancel(String interventionId) =>
      guard(() => _client.rpc<dynamic>('cancel_intervention', params: {'p_intervention_id': interventionId}));

  Future<void> sendMessage(String studentId, String body) => guard(() async {
        final trimmed = body.trim();
        if (trimmed.isEmpty || trimmed.length > 1000) throw const AppFailure(FailureKind.invalidInput);
        await _client.rpc<dynamic>('send_mentor_message', params: {'p_student_id': studentId, 'p_body': trimmed});
      });

  static String _date(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
