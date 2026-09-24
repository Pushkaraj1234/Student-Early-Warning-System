import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sews_mobile/core/app_version.dart';
import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/onboarding/data/onboarding_repository.dart';
import 'package:sews_mobile/features/profile/data/profile_repository.dart';
import 'package:sews_mobile/features/profile/domain/profile.dart';
import 'package:sews_mobile/features/student/data/student_repository.dart';
import 'package:sews_mobile/features/student/domain/student_record.dart';

final profileRepositoryProvider = Provider<ProfileRepository>(
  (ref) => ProfileRepository(ref.watch(supabaseClientProvider)),
);

final studentRepositoryProvider = Provider<StudentRepository>(
  (ref) => StudentRepository(ref.watch(supabaseClientProvider)),
);

final onboardingRepositoryProvider = Provider<OnboardingRepository>(
  (ref) => OnboardingRepository(ref.watch(supabaseClientProvider)),
);

/// The signed-in user's profile from the database (null when signed out).
final profileProvider = FutureProvider<Profile?>((ref) async {
  final userId = ref.watch(currentUserIdProvider);
  if (userId == null) return null;
  return ref.watch(profileRepositoryProvider).fetchOwnProfile(userId);
});

/// The signed-in student's own record (null until onboarding links it).
final studentRecordProvider = FutureProvider<StudentRecord?>((ref) async {
  final userId = ref.watch(currentUserIdProvider);
  if (userId == null) return null;
  return ref.watch(studentRepositoryProvider).fetchOwnRecord(userId);
});

/// The linked student id; data screens depend on it. Fails with a clear error if the
/// account is not linked to a student record.
final currentStudentIdProvider = FutureProvider<String>((ref) async {
  final record = await ref.watch(studentRecordProvider.future);
  if (record == null) throw const AppFailure(FailureKind.noStudentRecord);
  return record.id;
});

/// Component versions published by the database (`public.get_platform_versions()`).
final platformVersionsProvider = FutureProvider<Map<String, String>>((ref) async {
  final userId = ref.watch(currentUserIdProvider);
  if (userId == null) return const {};
  final client = ref.watch(supabaseClientProvider);
  return guard(() async {
    final rows = Json.rows(await client.rpc<dynamic>('get_platform_versions'));
    return {for (final r in rows) Json.string(r, 'component'): Json.string(r, 'version')};
  });
});

/// False only when the database says this build is below the minimum supported version.
/// A failed or missing check does not block the user (the database still enforces RLS).
final appVersionSupportedProvider = FutureProvider<bool>((ref) async {
  final versions = await ref.watch(platformVersionsProvider.future);
  final minimum = versions['minimum_mobile_app'];
  return minimum == null || isVersionSupported(appVersion, minimum);
});
