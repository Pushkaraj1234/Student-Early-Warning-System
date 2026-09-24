import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sews_mobile/core/routing/redirect.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/profile/domain/profile.dart';

import '../helpers/fixtures.dart';

AsyncValue<Profile?> _profile({bool onboarded = true, String role = 'student'}) =>
    AsyncValue.data(Profile.fromJson(profileRow(onboarded: onboarded, role: role)));

String? _go(AuthStatus auth, String location, [AsyncValue<Profile?> profile = const AsyncValue.data(null)]) =>
    resolveRedirect(auth: auth, profile: profile, location: location);

void main() {
  test('while the session is being restored, the splash screen is shown', () {
    expect(_go(AuthStatus.unknown, Routes.home), Routes.splash);
    expect(_go(AuthStatus.unknown, Routes.splash), isNull);
  });

  test('signed-out users can only reach public screens', () {
    expect(_go(AuthStatus.signedOut, Routes.home), Routes.login);
    expect(_go(AuthStatus.signedOut, Routes.risk), Routes.login);
    expect(_go(AuthStatus.signedOut, Routes.splash), Routes.login);
    for (final route in Routes.public) {
      expect(_go(AuthStatus.signedOut, route), isNull, reason: route);
    }
  });

  test('password recovery always leads to the reset screen', () {
    expect(_go(AuthStatus.passwordRecovery, Routes.home, _profile()), Routes.resetPassword);
    expect(_go(AuthStatus.passwordRecovery, Routes.resetPassword, _profile()), isNull);
  });

  test('signed-in users wait on the splash screen while the profile loads or fails', () {
    expect(_go(AuthStatus.signedIn, Routes.home, const AsyncValue.loading()), Routes.splash);
    expect(_go(AuthStatus.signedIn, Routes.home, AsyncValue.error(Exception('x'), StackTrace.empty)), Routes.splash);
    expect(_go(AuthStatus.signedIn, Routes.home, const AsyncValue.data(null)), Routes.splash);
  });

  test('students who have not onboarded are sent to onboarding', () {
    expect(_go(AuthStatus.signedIn, Routes.home, _profile(onboarded: false)), Routes.onboarding);
    expect(_go(AuthStatus.signedIn, Routes.onboarding, _profile(onboarded: false)), isNull);
  });

  test('each staff role lands on its own home; faculty has no screens yet', () {
    expect(_go(AuthStatus.signedIn, Routes.home, _profile(role: 'mentor')), Routes.mentorHome);
    expect(_go(AuthStatus.signedIn, Routes.home, _profile(role: 'admin')), Routes.adminHome);
    expect(_go(AuthStatus.signedIn, Routes.home, _profile(role: 'faculty')), Routes.unsupportedRole);
  });

  test('staff do not need student onboarding', () {
    expect(_go(AuthStatus.signedIn, Routes.onboarding, _profile(role: 'mentor', onboarded: false)), Routes.mentorHome);
    expect(_go(AuthStatus.signedIn, Routes.mentorHome, _profile(role: 'mentor', onboarded: false)), isNull);
  });

  test("roles cannot open each other's screens (RLS still guards the data)", () {
    expect(_go(AuthStatus.signedIn, Routes.mentorHome, _profile()), Routes.home);
    expect(_go(AuthStatus.signedIn, Routes.mentorStudent('s1'), _profile()), Routes.home);
    expect(_go(AuthStatus.signedIn, Routes.adminHome, _profile()), Routes.home);
    expect(_go(AuthStatus.signedIn, Routes.home, _profile(role: 'admin')), Routes.adminHome);
    expect(_go(AuthStatus.signedIn, Routes.mentorHome, _profile(role: 'admin')), Routes.adminHome);
    expect(_go(AuthStatus.signedIn, Routes.checkin, _profile(role: 'mentor')), Routes.mentorHome);
    expect(_go(AuthStatus.signedIn, Routes.mentorStudent('s1'), _profile(role: 'mentor')), isNull);
    for (final shared in [Routes.notifications, Routes.profile]) {
      expect(_go(AuthStatus.signedIn, shared, _profile(role: 'mentor')), isNull);
    }
  });

  test('an unsupported app version is sent to the update screen; unknown versions are not blocked', () {
    String? go(AsyncValue<bool> supported) => resolveRedirect(
          auth: AuthStatus.signedIn,
          profile: AsyncData(Profile.fromJson(profileRow())),
          location: Routes.home,
          versionSupported: supported,
        );
    expect(go(const AsyncData(false)), Routes.updateRequired);
    expect(go(const AsyncData(true)), isNull);
    expect(go(const AsyncLoading()), isNull);
    expect(go(AsyncError(Exception('offline'), StackTrace.empty)), isNull);
  });

  test('onboarded students go to the dashboard and can use app screens', () {
    expect(_go(AuthStatus.signedIn, Routes.login, _profile()), Routes.home);
    expect(_go(AuthStatus.signedIn, Routes.splash, _profile()), Routes.home);
    expect(_go(AuthStatus.signedIn, Routes.onboarding, _profile()), Routes.home);
    for (final route in [Routes.home, Routes.risk, Routes.academics, Routes.attendance, Routes.assignments,
      Routes.notifications, Routes.profile, Routes.checkin]) {
      expect(_go(AuthStatus.signedIn, route, _profile()), isNull, reason: route);
    }
  });
}
