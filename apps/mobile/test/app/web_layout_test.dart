import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sews_mobile/app.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/layout/breakpoints.dart';
import 'package:sews_mobile/core/routing/app_router.dart';
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

/// An onboarded student with no academic data: enough to render the main sections.
FakeBackend _studentBackend() => FakeBackend()
  ..onGet(rest('profiles'), [profileRow()])
  ..onGet(rest('students'), [studentRow()])
  ..onGet(rest('risk_predictions'), <Object>[])
  ..onGet(rest('student_courses'), <Object>[])
  ..onGet(rest('academic_records'), <Object>[])
  ..onGet(rest('assignments'), <Object>[])
  ..onGet(rest('assignment_submissions'), <Object>[])
  ..onGet(rest('notifications'), <Object>[])
  ..on('POST', rpcPath('get_my_recommended_actions'), (_) => jsonResponse(<Object>[]))
  ..on('POST', rpcPath('get_platform_versions'), (_) => jsonResponse(platformVersionRows()));

Future<void> _pump(WidgetTester tester, Size window) async {
  tester.view
    ..physicalSize = window
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  // The client is not disposed: SupabaseClient.dispose() never completes inside widget tests
  // (see app_flow_test.dart); Realtime is switched off so no socket is opened.
  await tester.pumpWidget(ProviderScope(
    retry: (_, _) => null,
    overrides: [
      supabaseClientProvider.overrideWithValue(_studentBackend().client),
      authControllerProvider.overrideWith(() => _FixedAuthController(_signedIn)),
      realtimeEnabledProvider.overrideWithValue(false),
    ],
    child: const SewsApp(),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('phones use the bottom navigation bar', (tester) async {
    await _pump(tester, const Size(400, 800));
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
  });

  testWidgets('wider windows use a side rail that switches sections', (tester) async {
    await _pump(tester, const Size(1000, 800));
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    final rail = find.byType(NavigationRail);
    await tester.tap(find.descendant(of: rail, matching: find.text('Attendance')));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppBar, 'Attendance'), findsOneWidget);
    await tester.tap(find.descendant(of: rail, matching: find.text('Home')));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppBar, 'Home'), findsOneWidget);
  });

  testWidgets('a desktop browser window shows the app centred at the maximum width', (tester) async {
    await _pump(tester, const Size(1600, 900));
    final page = find.byType(Scaffold).first;
    expect(tester.getSize(page).width, Breakpoints.maxFrameWidth);
    expect(tester.getTopLeft(page).dx, (1600 - Breakpoints.maxFrameWidth) / 2);
    expect(find.byType(NavigationRail), findsOneWidget);
  });

  testWidgets('an unknown address shows a not-found page with a way back', (tester) async {
    await _pump(tester, const Size(1000, 800));
    final container = ProviderScope.containerOf(tester.element(find.byType(SewsApp)));
    container.read(routerProvider).go('/no-such-page');
    await tester.pumpAndSettle();
    expect(find.text('This page does not exist.'), findsOneWidget);
    await tester.tap(find.text('Go to SEWS'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppBar, 'Home'), findsOneWidget);
  });
}
