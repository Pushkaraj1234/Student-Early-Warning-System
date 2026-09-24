import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/student/domain/student_record.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class StudentRepository {
  StudentRepository(this._client);

  final SupabaseClient _client;

  /// The student record linked to [userId], or null when none is linked yet.
  /// RLS only ever returns the caller's own record.
  Future<StudentRecord?> fetchOwnRecord(String userId) => guard(() async {
        final row =
            await _client.from('students').select(StudentRecord.columns).eq('user_id', userId).maybeSingle();
        return row == null ? null : StudentRecord.fromJson(row);
      });
}
