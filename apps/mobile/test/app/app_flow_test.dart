import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sews_mobile/app.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';

import '../helpers/fake_backend.dart';
import '../helpers/fixtures.dart';

class _FixedAuthController extends AuthController {
  _FixedAuthController(this._snapshot);

  final AuthSnapshot _snapshot;

  @override
  AuthSnapshot build() => _snapshot;
}

const _signedIn = AuthSnapshot(AuthStatus.signedIn, userId: testUserId, email: testEmail);

/// Backend with an onboarded student and NO academic/risk data (empty database state).
FakeBackend _emptyStudentBackend({bool onboarded = true, String role = 'student'}) => FakeBackend()
  ..onGet(rest('profiles'), [profileRow(onboarded: onboarded, role: role)])
  ..onGet(rest('students'), [studentRow()])
  ..onGet(rest('risk_predictions'), <Object>[])
  ..onGet(rest('student_courses'), <Object>[])
  ..onGet(rest('academic_records'), <Object>[])
  ..onGet(rest('assignments'), <Object>[])
  ..onGet(rest('assignment_submissions'), <Object>[])
  ..onGet(rest('notifications'), <Object>[])
  ..on('POST', rpcPath('get_my_recommended_actions'), (_) => jsonResponse(<Object>[]))
  ..on('POST', rpcPath('get_platform_versions'), (_) => jsonResponse(platformVersionRows()));

Future<void> _pumpApp(WidgetTester tester, FakeBackend backend, AuthSnapshot auth) async {
  // The client is deliberately not disposed here: SupabaseClient.dispose() never completes
  // inside a widget test (verified, even under runAsync). The fake client holds no sockets or
  // timers (autoRefreshToken is off, Realtime never connects), so nothing leaks between tests.
  await tester.pumpWidget(ProviderScope(
    retry: (_, _) => null,
    overrides: [
      supabaseClientProvider.overrideWithValue(backend.client),
      authControllerProvider.overrideWith(() => _FixedAuthController(auth)),
      realtimeEnabledProvider.overrideWithValue(false),
    ],
    child: const SewsApp(),
  ));
  await tester.pumpAndSettle();
}

void main() {
  group('navigation', () {
    testWidgets('signed-out users see sign-in and can move to registration and back', (tester) async {
      await _pumpApp(tester, FakeBackend(), const AuthSnapshot(AuthStatus.signedOut));
      expect(find.widgetWithText(AppBar, 'Sign in'), findsOneWidget);
      await tester.tap(find.text('Create an account'));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Create account'), findsOneWidget);
      await tester.ensureVisible(find.text('I already have an account'));
      await tester.tap(find.text('I already have an account'));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Sign in'), findsOneWidget);
    });

    testWidgets('forgot-password screen is reachable while signed out', (tester) async {
      await _pumpApp(tester, FakeBackend(), const AuthSnapshot(AuthStatus.signedOut));
      await tester.tap(find.text('Forgot password?'));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Reset password'), findsOneWidget);
    });

    testWidgets('a student who has not onboarded is taken to onboarding', (tester) async {
      await _pumpApp(tester, _emptyStudentBackend(onboarded: false), _signedIn);
      expect(find.text('Welcome to SEWS'), findsOneWidget);
    });

    testWidgets('faculty accounts are told their screens are not available yet', (tester) async {
      await _pumpApp(tester, _emptyStudentBackend(role: 'faculty'), _signedIn);
      expect(find.textContaining('Faculty features are not available yet'), findsOneWidget);
    });

    testWidgets('an outdated app build is asked to update', (tester) async {
      final backend = _emptyStudentBackend()
        ..on('POST', rpcPath('get_platform_versions'), (_) => jsonResponse(platformVersionRows(minimumApp: '9.0.0')));
      await _pumpApp(tester, backend, _signedIn);
      expect(find.textContaining('no longer supported'), findsOneWidget);
    });

    testWidgets('onboarded students land on the dashboard and can switch tabs', (tester) async {
      await _pumpApp(tester, _emptyStudentBackend(), _signedIn);
      expect(find.widgetWithText(AppBar, 'Home'), findsOneWidget);
      expect(find.text('Hello, Synthetic'), findsOneWidget);
      await tester.tap(find.text('Academics').last);
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Academics'), findsOneWidget);
      await tester.tap(find.text('Attendance').last);
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Attendance'), findsOneWidget);
      await tester.tap(find.text('Assignments').last);
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Assignments'), findsOneWidget);
    });
  });

  group('empty and error states', () {
    testWidgets('empty database: every dashboard section shows an empty state', (tester) async {
      await _pumpApp(tester, _emptyStudentBackend(), _signedIn);
      expect(find.text('No early-warning signal is available yet.'), findsOneWidget);
      expect(find.text('No recommended actions right now.'), findsOneWidget);
      expect(find.text('No academic records yet.'), findsOneWidget);
      await tester.scrollUntilVisible(find.text('No assignments yet.'), 200);
      expect(find.text('No attendance has been recorded yet.'), findsOneWidget);
      expect(find.text('No assignments yet.'), findsOneWidget);
    });

    testWidgets('network failure shows a friendly error with retry, then recovers', (tester) async {
      final backend = _emptyStudentBackend()
        ..on('GET', rest('risk_predictions'), (_) => throw http.ClientException('socket closed: 10.1.2.3'));
      await _pumpApp(tester, backend, _signedIn);
      expect(find.textContaining('You appear to be offline'), findsOneWidget);
      expect(find.textContaining('socket closed'), findsNothing);
      expect(find.textContaining('10.1.2.3'), findsNothing);

      backend.onGet(rest('risk_predictions'), <Object>[]);
      await tester.tap(find.widgetWithText(OutlinedButton, 'Retry').first);
      await tester.pumpAndSettle();
      expect(find.textContaining('You appear to be offline'), findsNothing);
      expect(find.text('No early-warning signal is available yet.'), findsOneWidget);
    });

    testWidgets('invalid data shows a data error, never the parser message', (tester) async {
      final backend = _emptyStudentBackend()..onGet(rest('risk_predictions'), [predictionRow(level: 'critical')]);
      await _pumpApp(tester, backend, _signedIn);
      expect(find.textContaining('could not read'), findsOneWidget);
      expect(find.textContaining('risk_level'), findsNothing);
    });

    testWidgets('a profile load failure keeps the user on splash with retry and sign-out', (tester) async {
      final backend = FakeBackend()
        ..on('GET', rest('profiles'), (_) => postgrestError('XX000', 'internal detail', status: 500));
      await _pumpApp(tester, backend, _signedIn);
      expect(find.textContaining('The server could not complete the request'), findsOneWidget);
      expect(find.text('Sign out'), findsOneWidget);
      expect(find.textContaining('internal detail'), findsNothing);
    });
  });
}
