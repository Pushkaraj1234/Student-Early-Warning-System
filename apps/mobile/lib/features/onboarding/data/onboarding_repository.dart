import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class OnboardingRepository {
  OnboardingRepository(this._client);

  final SupabaseClient _client;

  /// Links the account to the institution's student record whose institutional email
  /// matches the account's CONFIRMED email. Matching happens entirely in the database
  /// (`public.claim_student_record`); the app cannot choose which record to link.
  Future<String> claimStudentRecord() => guard(() async {
        final result = await _client.rpc<dynamic>('claim_student_record');
        if (result is String && result.isNotEmpty) return result;
        throw const FormatException('claim_student_record returned no id');
      });

  Future<void> completeOnboarding(String privacyNoticeVersion) => guard(() async {
        await _client.rpc<dynamic>(
          'complete_onboarding',
          params: {'p_privacy_notice_version': privacyNoticeVersion},
        );
      });
}
