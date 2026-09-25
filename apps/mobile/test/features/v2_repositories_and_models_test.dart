import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sews_mobile/core/app_version.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/admin/data/admin_repository.dart';
import 'package:sews_mobile/features/admin/domain/admin_models.dart';
import 'package:sews_mobile/features/checkins/data/checkins_repository.dart';
import 'package:sews_mobile/features/checkins/domain/checkin.dart';
import 'package:sews_mobile/features/mentor/data/mentor_repository.dart';
import 'package:sews_mobile/features/mentor/domain/mentor_models.dart';
import 'package:sews_mobile/features/recommendations/data/recommendations_repository.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';

import '../helpers/fake_backend.dart';
import '../helpers/fixtures.dart';
import '../helpers/v2_fixtures.dart';

Matcher _failure(FailureKind kind) => isA<AppFailure>().having((f) => f.kind, 'kind', kind);

Map<String, dynamic> _body(http.Request r) => jsonDecode(r.body) as Map<String, dynamic>;

void main() {
  late FakeBackend backend;

  setUp(() => backend = FakeBackend());
  tearDown(() => backend.client.dispose());

  group('app version', () {
    test('semantic comparison', () {
      expect(isVersionSupported('2.0.0', '2.0.0'), isTrue);
      expect(isVersionSupported('2.1.0', '2.0.9'), isTrue);
      expect(isVersionSupported('10.0.0', '9.9.9'), isTrue);
      expect(isVersionSupported('1.9.9', '2.0.0'), isFalse);
      expect(isVersionSupported('2.0.0+7', '2.0.1'), isFalse);
      expect(isVersionSupported('2.0.0', 'not-a-version'), isTrue); // a bad minimum never locks users out
      expect(isVersionSupported('garbage', '1.0.0'), isFalse);
    });

    test('appVersion matches the version in pubspec.yaml', () {
      final line = File('pubspec.yaml').readAsLinesSync().firstWhere((l) => l.startsWith('version:'));
      expect(line.substring('version:'.length).trim().split('+').first, appVersion);
    });
  });

  group('student: offers and check-ins', () {
    test('accepting calls the database function with only the action id and the answer', () async {
      backend.on('POST', rpcPath('respond_to_intervention'), (_) => jsonResponse(null));
      await RecommendationsRepository(backend.client).respond('a1', accept: true);
      expect(_body(backend.requestsTo(rpcPath('respond_to_intervention')).single),
          {'p_intervention_id': 'a1', 'p_accept': true, 'p_decline_reason': null});
    });

    test('declining sends the controlled reason; a decline without reason is refused locally', () async {
      backend.on('POST', rpcPath('respond_to_intervention'), (_) => jsonResponse(null));
      final repo = RecommendationsRepository(backend.client);
      await repo.respond('a1', accept: false, reason: DeclineReason.notConvenient);
      expect(_body(backend.requestsTo(rpcPath('respond_to_intervention')).single)['p_decline_reason'],
          'not_convenient');
      await expectLater(repo.respond('a1', accept: false), throwsA(_failure(FailureKind.invalidData)));
      expect(backend.requestsTo(rpcPath('respond_to_intervention')), hasLength(1));
    });

    test('responding to an action that is no longer open reports a conflict', () async {
      backend.on('POST', rpcPath('respond_to_intervention'),
          (_) => postgrestError('23514', 'sews:invalid_intervention_transition'));
      await expectLater(RecommendationsRepository(backend.client).respond('a1', accept: true),
          throwsA(_failure(FailureKind.conflict)));
    });

    test('only offered and accepted actions are valid for students', () {
      expect(RecommendedAction.fromJson(actionRow()).awaitsResponse, isTrue);
      expect(RecommendedAction.fromJson(actionRow(status: 'accepted')).awaitsResponse, isFalse);
      expect(() => RecommendedAction.fromJson(actionRow(status: 'recommended')), throwsFormatException);
      expect(RecommendedAction.fromJson(actionRow(type: 'financial_support_referral')).type,
          InterventionType.financialSupportReferral);
    });

    test('check-in drafts mirror the database rules', () {
      expect(CheckinDraft(needs: {}, wantsContact: false).validationError, isNotNull);
      expect(CheckinDraft(needs: {}, wantsContact: false, comment: '   ').validationError, isNotNull);
      expect(CheckinDraft(needs: {}, wantsContact: true).validationError, isNull);
      expect(CheckinDraft(needs: {}, wantsContact: false, comment: 'x' * 501).validationError, isNotNull);
      final draft = CheckinDraft(
        needs: {SupportNeed.financialDifficulty, SupportNeed.workload},
        wantsContact: true,
        comment: '  help with deadlines  ',
      );
      expect(draft.toInsert(testStudentId), {
        'student_id': testStudentId,
        'support_needs': ['workload', 'financial_difficulty'],
        'wants_contact': true,
        'comment': 'help with deadlines',
      });
    });

    test('check-in insert goes to student_checkins; the daily limit is reported clearly', () async {
      backend.on('POST', rest('student_checkins'), (_) => jsonResponse(null, status: 201));
      final repo = CheckinsRepository(backend.client);
      await repo.submit(testStudentId, CheckinDraft(needs: {SupportNeed.timeManagement}, wantsContact: false));
      final sent = jsonDecode(backend.requestsTo(rest('student_checkins')).single.body);
      expect(sent, containsPair('support_needs', ['time_management']));
      backend.on('POST', rest('student_checkins'), (_) => postgrestError('P0001', 'sews:rate_limited'));
      await expectLater(repo.submit(testStudentId, CheckinDraft(needs: {}, wantsContact: true)),
          throwsA(_failure(FailureKind.rateLimited)));
      await expectLater(repo.submit(testStudentId, CheckinDraft(needs: {}, wantsContact: false)),
          throwsA(_failure(FailureKind.invalidInput)));
    });
  });

  group('mentor', () {
    test('caseload parses students with and without a prediction', () async {
      backend.on('POST', rpcPath('get_mentor_caseload'), (_) => jsonResponse([caseloadRow(), caseloadRow(
        studentId: 's2', name: 'Synthetic Student Alpha', level: null)]));
      final caseload = await MentorRepository(backend.client).fetchCaseload();
      expect(caseload.first.level, RiskLevel.high);
      expect(caseload.first.trajectory, Trajectory.rapidlyIncreasing);
      expect(caseload.first.isRising, isTrue);
      expect(caseload.last.level, isNull);
      expect(caseload.last.trajectory, isNull);
      final distribution = RiskDistribution(caseload);
      expect(distribution.counts[RiskLevel.high], 1);
      expect(distribution.noPrediction, 1);
    });

    test('weekly trends: sorted oldest first, rates never invented', () async {
      backend.on('POST', rpcPath('get_student_weekly_trends'), (_) => jsonResponse([
            trendRow('2026-09-14', attended: 3, counted: 5),
            trendRow('2026-09-07', attended: 0, counted: 0),
          ]));
      final trends = await MentorRepository(backend.client).fetchTrends('s1');
      expect(_body(backend.requestsTo(rpcPath('get_student_weekly_trends')).single),
          {'p_student_id': 's1', 'p_weeks': 12});
      expect(trends.map((t) => t.weekStart.day), [7, 14]);
      expect(trends.first.attendanceRate, isNull);
      expect(trends.last.attendanceRate, closeTo(0.6, 1e-9));
      expect(() => WeeklyTrend.fromJson(trendRow('2026-09-14', attended: 6, counted: 5)), throwsFormatException);
    });

    test('interventions: parsed with decline reason and outcome; optional student filter', () async {
      backend.onGet(rest('interventions'), [
        interventionRow(status: 'declined', declineReason: 'already_receiving_support'),
        interventionRow(id: 'i2', status: 'completed', outcome: 'no_change'),
      ]);
      final items = await MentorRepository(backend.client).fetchInterventions(studentId: 's1');
      expect(items.first.declineReason, DeclineReason.alreadyReceivingSupport);
      expect(items.last.outcome, InterventionOutcome.noChange);
      expect(items.first.status.isOpen, isFalse);
      final query = backend.requestsTo(rest('interventions')).single.url.queryParameters;
      expect(query['student_id'], 'eq.s1');
      expect(query['select'], isNot(contains('notes')));
    });

    test('state changes go through database functions with exact parameters', () async {
      for (final fn in ['approve_recommendation', 'complete_intervention', 'cancel_intervention',
        'send_mentor_message']) {
        backend.on('POST', rpcPath(fn), (_) => jsonResponse(null));
      }
      backend.on('POST', rpcPath('create_intervention'), (_) => jsonResponse('new-id'));
      final repo = MentorRepository(backend.client);
      await repo.approve('i1');
      await repo.complete('i1', InterventionOutcome.improved);
      await repo.cancel('i1');
      await repo.sendMessage('s1', '  See you Monday.  ');
      final id = await repo.create(
        studentId: 's1',
        type: InterventionType.studyPlanning,
        reason: ' Missed two deadlines. ',
        priority: InterventionPriority.high,
        dueOn: DateTime(2026, 10, 3),
      );
      expect(id, 'new-id');
      expect(_body(backend.requestsTo(rpcPath('approve_recommendation')).single), {'p_intervention_id': 'i1'});
      expect(_body(backend.requestsTo(rpcPath('complete_intervention')).single),
          {'p_intervention_id': 'i1', 'p_outcome': 'improved'});
      expect(_body(backend.requestsTo(rpcPath('send_mentor_message')).single),
          {'p_student_id': 's1', 'p_body': 'See you Monday.'});
      expect(_body(backend.requestsTo(rpcPath('create_intervention')).single), {
        'p_student_id': 's1',
        'p_intervention_type': 'study_planning',
        'p_reason': 'Missed two deadlines.',
        'p_priority': 'high',
        'p_due_on': '2026-10-03',
      });
    });

    test('invalid input is refused before any request; server refusals map to clear failures', () async {
      final repo = MentorRepository(backend.client);
      await expectLater(
        repo.create(studentId: 's1', type: InterventionType.mentorMeeting, reason: 'ok', priority: InterventionPriority.low),
        throwsA(_failure(FailureKind.invalidInput)),
      );
      await expectLater(repo.sendMessage('s1', '   '), throwsA(_failure(FailureKind.invalidInput)));
      await expectLater(repo.sendMessage('s1', 'x' * 1001), throwsA(_failure(FailureKind.invalidInput)));
      expect(backend.requests, isEmpty);

      backend
        ..on('POST', rpcPath('create_intervention'), (_) => postgrestError('23505', 'sews:duplicate_intervention'))
        ..on('POST', rpcPath('send_mentor_message'), (_) => postgrestError('P0001', 'sews:student_not_linked'))
        ..on('POST', rpcPath('approve_recommendation'), (_) => postgrestError('42501', 'sews:forbidden', status: 403));
      await expectLater(
        repo.create(studentId: 's1', type: InterventionType.mentorMeeting, reason: 'Needs a chat.',
            priority: InterventionPriority.low),
        throwsA(_failure(FailureKind.duplicate)),
      );
      await expectLater(repo.sendMessage('s1', 'Hello'), throwsA(_failure(FailureKind.studentNotLinked)));
      await expectLater(repo.approve('i1'), throwsA(_failure(FailureKind.forbidden)));
    });
  });

  group('admin', () {
    test('overview reads registry, OPEN alerts and snapshots; acknowledge uses the function', () async {
      backend
        ..onGet(rest('model_registry'), [registryRow()])
        ..onGet(rest('drift_alerts'), [driftAlertRow()])
        ..onGet(rest('model_monitoring_snapshots'), [snapshotRow()])
        ..on('POST', rpcPath('acknowledge_drift_alert'), (_) => jsonResponse(null));
      final repo = AdminRepository(backend.client);
      final overview = await repo.fetchOverview();
      expect(overview.models.single.status, ModelStatus.development);
      expect(overview.models.single.status.mayScoreLiveStudents, isFalse);
      expect(overview.openAlerts.single.severity, AlertSeverity.critical);
      expect(overview.snapshots.single.predictions, 3);
      expect(backend.requestsTo(rest('drift_alerts')).single.url.queryParameters['status'], 'eq.open');
      await repo.acknowledge('al1');
      expect(_body(backend.requestsTo(rpcPath('acknowledge_drift_alert')).single), {'p_alert_id': 'al1'});
    });

    test('unknown model status is invalid data, never guessed', () {
      expect(() => RegisteredModel.fromJson({...registryRow(), 'status': 'live'}), throwsFormatException);
    });
  });
}
