import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/profile/domain/profile.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ProfileRepository {
  ProfileRepository(this._client);

  final SupabaseClient _client;

  /// The caller's own profile (RLS: a user can read only their own profile row).
  Future<Profile?> fetchOwnProfile(String userId) => guard(() async {
        final row = await _client.from('profiles').select(Profile.columns).eq('id', userId).maybeSingle();
        return row == null ? null : Profile.fromJson(row);
      });

  /// Only `full_name` is writable by the user; the database rejects any other column.
  Future<void> updateFullName(String userId, String fullName) => guard(() async {
        await _client.from('profiles').update({'full_name': fullName.trim()}).eq('id', userId);
      });
}
