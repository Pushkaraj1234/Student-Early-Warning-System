import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/assignments/domain/assignment_models.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class AssignmentsRepository {
  AssignmentsRepository(this._client);

  final SupabaseClient _client;

  /// Assignments are visible (RLS) only for courses the student is enrolled in; the
  /// student's own submissions are filtered explicitly and by RLS.
  Future<(List<Assignment>, List<Submission>)> fetch(String studentId) => guard(() async {
        final results = await Future.wait([
          _client.from('assignments').select(Assignment.columns).order('due_at', ascending: true),
          _client.from('assignment_submissions').select(Submission.columns).eq('student_id', studentId),
        ]);
        return (
          Json.rows(results[0]).map(Assignment.fromJson).toList(),
          Json.rows(results[1]).map(Submission.fromJson).toList(),
        );
      });
}
