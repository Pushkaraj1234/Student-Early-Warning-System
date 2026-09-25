import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:sews_mobile/app.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';

import '../helpers/fake_backend.dart';
import '../helpers/fixtures.dart';
import '../helpers/v2_fixtures.dart';

class _FixedAuthController extends AuthController {
  _FixedAuthController(this._snapshot);

  final AuthSnapshot _snapshot;

  @override
  AuthSnapshot build() => _snapshot;
}

const _signedIn = AuthSnapshot(AuthStatus.signedIn, userId: testUserId, email: testEmail);

Map<String, dynamic> _json(http.Request r) => jsonDecode(r.body) as Map<String, dynamic>;

Map<String, dynamic> _alertRow() => {
      'id': 'n1',
      'notification_type': 'risk_change',
      'title': 'Risk estimate increased',
      'body': 'A student in your caseload has a rising risk estimate.',
      'read_at': null,
      'created_at': '2026-09-22T00:00:00Z',
    };

FakeBackend _common(String role) => FakeBackend()
  ..onGet(rest('profiles'), [profileRow(role: role)])
  ..onGet(rest('notifications'), <Object>[])
  ..on('POST', rpcPath('get_platform_versions'), (_) => jsonResponse(platformVersionRows()));

FakeBackend _mentorBackend({List<Map<String, dynamic>>? interventions}) => _common('mentor')
  ..onGet(rest('notifications'), [_alertRow()])
  ..on('POST', rpcPath('get_mentor_caseload'), (_) => jsonResponse([
        caseloadRow(),
        caseloadRow(studentId: 's2', name: 'Synthetic Student Alpha', level: null, open: 0),
      ]))
  ..onGet(rest('interventions'), interventions ?? [interventionRow()])
  ..onGet(rest('risk_predictions'), [
    predictionRow(trajectory: 'rapidly_increasing'),
    predictionRow(id: 'p0', level: 'watch', date: '2026-09-06', trajectory: 'insufficient_history'),
  ])
  ..onGet(rest('risk_factors'), [factorRow(1, 'attendance_rate_last_14d', 0.5, 0.61)])
  ..on('POST', rpcPath('get_student_weekly_trends'), (_) => jsonResponse([trendRow('2026-09-14')]));

FakeBackend _studentBackend({List<Map<String, dynamic>> actions = const []}) => _common('student')
  ..onGet(rest('students'), [studentRow()])
  ..onGet(rest('risk_predictions'), <Object>[])
  ..onGet(rest('student_courses'), <Object>[])
  ..onGet(rest('academic_records'), <Object>[])
  ..onGet(rest('assignments'), <Object>[])
  ..onGet(rest('assignment_submissions'), <Object>[])
  ..on('POST', rpcPath('get_my_recommended_actions'), (_) => jsonResponse(actions));

Future<void> _pump(WidgetTester tester, FakeBackend backend) async {
  // A tall surface keeps every dashboard section built (the lists are lazy).
  tester.view
    ..physicalSize = const Size(1200, 2600)
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  // The client is not disposed: SupabaseClient.dispose() never completes inside widget tests
  // (see app_flow_test.dart); Realtime is switched off so no socket is opened.
  await tester.pumpWidget(ProviderScope(
    retry: (_, _) => null,
    overrides: [
      supabaseClientProvider.overrideWithValue(backend.client),
      authControllerProvider.overrideWith(() => _FixedAuthController(_signedIn)),
      realtimeEnabledProvider.overrideWithValue(false),
    ],
    child: const SewsApp(),
  ));
  await tester.pumpAndSettle();
}

void main() {
  group('mentor', () {
    testWidgets('dashboard shows distribution, rising risk, alerts and intervention status', (tester) async {
      await _pump(tester, _mentorBackend());
      expect(find.text('My students'), findsOneWidget);
      expect(find.text('High: 1'), findsOneWidget);
      expect(find.text('No signal yet: 1'), findsOneWidget);
      expect(find.text('Rising risk'), findsOneWidget);
      expect(find.text('Risk estimate increased'), findsOneWidget);
      expect(find.text('Suggested — needs review: 1'), findsOneWidget);
      // Beta appears under "Rising risk" and in the full list; Alpha only in the full list.
      expect(find.text('Synthetic Student Beta'), findsNWidgets(2));
      expect(find.text('Synthetic Student Alpha'), findsOneWidget);
    });

    testWidgets('student detail shows trajectory, trends, factors and lets the mentor offer a suggestion',
        (tester) async {
      final backend = _mentorBackend()
        ..on('POST', rpcPath('approve_recommendation'), (_) => jsonResponse(null));
      await _pump(tester, backend);
      await tester.tap(find.text('Synthetic Student Beta').first);
      await tester.pumpAndSettle();

      expect(find.text('Trajectory: Rapidly increasing'), findsOneWidget);
      expect(find.text('Week of'), findsOneWidget);
      expect(find.textContaining('Attendance in the last 14 days'), findsWidgets);
      expect(find.textContaining('associations, not causes'), findsOneWidget);
      expect(find.textContaining('Demonstration signal'), findsOneWidget); // synthetic provenance is disclosed

      await tester.tap(find.text('Review & offer'));
      await tester.pumpAndSettle();
      expect(_json(backend.requestsTo(rpcPath('approve_recommendation')).single), {'p_intervention_id': 'i1'});
      expect(find.text('Offered to the student.'), findsOneWidget);
    });

    testWidgets('completing an accepted intervention records the chosen outcome', (tester) async {
      final backend =
          _mentorBackend(interventions: [interventionRow(status: 'accepted', source: 'mentor', ruleId: null)])
            ..on('POST', rpcPath('complete_intervention'), (_) => jsonResponse(null));
      await _pump(tester, backend);
      await tester.tap(find.text('Synthetic Student Beta').first);
      await tester.pumpAndSettle();
      expect(find.text('Review & offer'), findsNothing); // only valid actions are offered
      await tester.tap(find.text('Complete'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Improved'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      expect(_json(backend.requestsTo(rpcPath('complete_intervention')).single),
          {'p_intervention_id': 'i1', 'p_outcome': 'improved'});
    });

    testWidgets('a student outside the caseload cannot be opened', (tester) async {
      await _pump(tester, _mentorBackend());
      // push() completes only when the route is popped, so it is deliberately not awaited.
      unawaited(GoRouter.of(tester.element(find.text('My students'))).push('/mentor/students/not-my-student'));
      await tester.pumpAndSettle();
      expect(find.text("You don't have access to this information."), findsOneWidget);
    });
  });

  group('student', () {
    testWidgets('accepting an offer answers through the database function', (tester) async {
      final backend = _studentBackend(actions: [actionRow()])
        ..on('POST', rpcPath('respond_to_intervention'), (_) => jsonResponse(null));
      await _pump(tester, backend);
      expect(find.textContaining('Offered to you'), findsOneWidget);
      await tester.tap(find.text('Accept'));
      await tester.pumpAndSettle();
      expect(_json(backend.requestsTo(rpcPath('respond_to_intervention')).single),
          {'p_intervention_id': 'a1', 'p_accept': true, 'p_decline_reason': null});
      expect(find.text('Accepted. Your mentor will follow up.'), findsOneWidget);
    });

    testWidgets('declining asks for a reason and sends it', (tester) async {
      final backend = _studentBackend(actions: [actionRow()])
        ..on('POST', rpcPath('respond_to_intervention'), (_) => jsonResponse(null));
      await _pump(tester, backend);
      await tester.tap(find.text('Not now'));
      await tester.pumpAndSettle();
      await tester.tap(find.text("I'm already getting support"));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Decline'));
      await tester.pumpAndSettle();
      expect(_json(backend.requestsTo(rpcPath('respond_to_intervention')).single)['p_decline_reason'],
          'already_receiving_support');
    });

    testWidgets('accepted actions have no answer buttons', (tester) async {
      await _pump(tester, _studentBackend(actions: [actionRow(status: 'accepted')]));
      expect(find.text('Accept'), findsNothing);
      expect(find.text('Not now'), findsNothing);
    });

    testWidgets('check-in validates, then saves only what the student chose', (tester) async {
      final backend = _studentBackend()..on('POST', rest('student_checkins'), (_) => jsonResponse(null, status: 201));
      await _pump(tester, backend);
      await tester.tap(find.widgetWithText(OutlinedButton, 'Check in'));
      await tester.pumpAndSettle();
      expect(find.textContaining('not a health or mental-health assessment'), findsOneWidget);

      await tester.tap(find.text('Send check-in'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Choose at least one option'), findsOneWidget);
      expect(backend.requestsTo(rest('student_checkins')), isEmpty);

      await tester.tap(find.text('Managing my time'));
      await tester.tap(find.text('I would like my mentor to contact me'));
      await tester.pump();
      await tester.tap(find.text('Send check-in'));
      await tester.pumpAndSettle();
      expect(jsonDecode(backend.requestsTo(rest('student_checkins')).single.body), {
        'student_id': testStudentId,
        'support_needs': ['time_management'],
        'wants_contact': true,
        'comment': null,
      });
      expect(find.text('Thanks. Your check-in was sent to your mentor.'), findsOneWidget);
    });
  });

  group('admin', () {
    testWidgets('monitoring view lists models and lets an admin acknowledge an alert', (tester) async {
      final backend = _common('admin')
        ..onGet(rest('model_registry'), [registryRow()])
        ..onGet(rest('drift_alerts'), [driftAlertRow()])
        ..onGet(rest('model_monitoring_snapshots'), [snapshotRow()])
        ..on('POST', rpcPath('acknowledge_drift_alert'), (_) => jsonResponse(null));
      await _pump(tester, backend);
      expect(find.text('Model monitoring'), findsOneWidget);
      expect(find.text('seed-demo-0'), findsOneWidget);
      expect(find.text('Development'), findsOneWidget);
      expect(find.text('Open drift alerts (1)'), findsOneWidget);
      await tester.tap(find.text('Acknowledge'));
      await tester.pumpAndSettle();
      expect(_json(backend.requestsTo(rpcPath('acknowledge_drift_alert')).single), {'p_alert_id': 'al1'});
    });
  });
}
