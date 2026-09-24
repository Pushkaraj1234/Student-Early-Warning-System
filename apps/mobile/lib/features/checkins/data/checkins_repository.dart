import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/checkins/domain/checkin.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class CheckinsRepository {
  CheckinsRepository(this._client);

  final SupabaseClient _client;

  /// Saves a check-in for the signed-in student. RLS only allows inserting the caller's own
  /// check-in; the server sets the timestamp and limits how many can be sent per day.
  Future<void> submit(String studentId, CheckinDraft draft) => guard(() async {
        if (draft.validationError != null) throw const AppFailure(FailureKind.invalidInput);
        await _client.from('student_checkins').insert(draft.toInsert(studentId));
      });
}
