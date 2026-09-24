import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/profile/domain/profile.dart';

/// Navigation rules as a pure function (unit-tested).
///
/// This decides which SCREEN to show. It is not a security boundary: every data request
/// is authorised by Row Level Security in the database, using the role stored in
/// `public.profiles` — never a role held by the client.
String? resolveRedirect({
  required AuthStatus auth,
  required AsyncValue<Profile?> profile,
  required String location,
  AsyncValue<bool> versionSupported = const AsyncData(true),
}) {
  String? goTo(String target) => location == target ? null : target;

  switch (auth) {
    case AuthStatus.unknown:
      return goTo(Routes.splash);
    case AuthStatus.passwordRecovery:
      return goTo(Routes.resetPassword);
    case AuthStatus.signedOut:
      return Routes.public.contains(location) ? null : Routes.login;
    case AuthStatus.signedIn:
      break;
  }

  // Signed in: the profile decides where the user may go. The splash screen shows the
  // loading, error and "missing profile" states.
  if (profile.isLoading || profile.hasError) return goTo(Routes.splash);
  final current = profile.value;
  if (current == null) return goTo(Routes.splash);

  // Only a KNOWN unsupported version blocks; a failed or pending check never locks users out.
  if (versionSupported.value == false) return goTo(Routes.updateRequired);

  final home = homeFor(current.role);
  if (home == null) return goTo(Routes.unsupportedRole);
  // Onboarding (claiming a student record, privacy notice) applies to students only.
  if (current.role == ProfileRole.student && !current.isOnboarded) return goTo(Routes.onboarding);
  if (Routes.gateways.contains(location)) return home;
  if (!isAllowedFor(current.role, location)) return home;
  return null;
}

/// Home screen per role; null = no screens for this role in this app version.
String? homeFor(ProfileRole role) => switch (role) {
      ProfileRole.student => Routes.home,
      ProfileRole.mentor => Routes.mentorHome,
      ProfileRole.admin => Routes.adminHome,
      ProfileRole.faculty => null,
    };

/// Which screens a role may open. Screen routing only; RLS enforces data access.
bool isAllowedFor(ProfileRole role, String location) {
  if (Routes.shared.contains(location)) return true;
  bool under(String prefix) => location == prefix || location.startsWith('$prefix/');
  return switch (role) {
    ProfileRole.student =>
      !under(Routes.mentorHome) && !under(Routes.adminHome),
    ProfileRole.mentor => under(Routes.mentorHome),
    ProfileRole.admin => under(Routes.adminHome),
    ProfileRole.faculty => false,
  };
}
