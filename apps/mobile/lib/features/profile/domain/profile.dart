import 'package:sews_mobile/core/data/json.dart';

enum ProfileRole { student, mentor, faculty, admin }

/// The signed-in user's row from `public.profiles`. The role comes from the database —
/// never from the client or token metadata.
class Profile {
  const Profile({
    required this.id,
    required this.role,
    this.fullName,
    this.institutionId,
    this.onboardingCompletedAt,
    this.privacyNoticeVersion,
  });

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        id: Json.string(json, 'id'),
        role: Json.enumValue(json, 'role', {for (final r in ProfileRole.values) r.name: r}),
        fullName: Json.stringOrNull(json, 'full_name'),
        institutionId: Json.stringOrNull(json, 'institution_id'),
        onboardingCompletedAt: Json.dateTimeOrNull(json, 'onboarding_completed_at'),
        privacyNoticeVersion: Json.stringOrNull(json, 'privacy_notice_version'),
      );

  static const String columns =
      'id, role, full_name, institution_id, onboarding_completed_at, privacy_notice_version';

  final String id;
  final ProfileRole role;
  final String? fullName;
  final String? institutionId;
  final DateTime? onboardingCompletedAt;
  final String? privacyNoticeVersion;

  bool get isOnboarded => onboardingCompletedAt != null;
}
