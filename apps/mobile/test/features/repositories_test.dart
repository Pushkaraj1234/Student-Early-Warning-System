import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/academics/data/academics_repository.dart';
import 'package:sews_mobile/features/assignments/data/assignments_repository.dart';
import 'package:sews_mobile/features/attendance/data/attendance_repository.dart';
import 'package:sews_mobile/features/notifications/data/notifications_repository.dart';
import 'package:sews_mobile/features/onboarding/data/onboarding_repository.dart';
import 'package:sews_mobile/features/profile/data/profile_repository.dart';
import 'package:sews_mobile/features/recommendations/data/recommendations_repository.dart';
import 'package:sews_mobile/features/risk/data/risk_repository.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:sews_mobile/features/student/data/student_repository.dart';

import '../helpers/fake_backend.dart';
import '../helpers/fixtures.dart';

Matcher _failure(FailureKind kind) => isA<AppFailure>().having((f) => f.kind, 'kind', kind);

void main() {
  late FakeBackend backend;

  setUp(() => backend = FakeBackend());
  tearDown(() => backend.client.dispose());

  group('every student query is scoped to the signed-in student', () {
    test('academics', () async {
      backend
        ..onGet(rest('student_courses'), [courseResultRow()])
        ..onGet(rest('academic_records'), [semesterRow()]);
      final overview = await AcademicsRepository(backend.client).fetchOverview(testStudentId);
      expect(overview.courses.single.courseCode, 'SYN-sc1');
      expect(overview.latestPublished!.cgpa, 8.55);
      for (final path in [rest('student_courses'), rest('academic_records')]) {
        expect(backend.requestsTo(path).single.url.queryParameters['student_id'], 'eq.$testStudentId');
      }
    });

    test('risk: newest prediction with its stored factors only', () async {
      backend
        ..onGet(rest('risk_predictions'), [predictionRow(), predictionRow(id: 'p0', level: 'watch', date: '2026-09-06')])
        ..onGet(rest('risk_factors'), [factorRow(1, 'attendance_rate_last_14d', 0.52, 0.61)]);
      final overview = await RiskRepository(backend.client).fetchOverview(testStudentId);
      expect(overview.latest!.level, RiskLevel.high);
      expect(overview.trend.map((p) => p.level), [RiskLevel.watch, RiskLevel.high]);
      expect(overview.latestFactors.single.feature, 'attendance_rate_last_14d');
      final predictionQuery = backend.requestsTo(rest('risk_predictions')).single.url.queryParameters;
      expect(predictionQuery['student_id'], 'eq.$testStudentId');
      expect(predictionQuery['target'], 'eq.academic');  // other targets are separate models
      expect(predictionQuery['order'], 'prediction_date.desc.nullslast,created_at.desc.nullslast');
      final factorQuery = backend.requestsTo(rest('risk_factors')).single.url.queryParameters;
      expect(factorQuery['prediction_id'], 'eq.p1');
      expect(factorQuery['order'], 'rank.asc.nullslast'); // most influential first; postgrest defaults to desc
    });

    test('risk: no predictions means no factor request (prediction unavailable)', () async {
      backend.onGet(rest('risk_predictions'), <Object>[]);
      final overview = await RiskRepository(backend.client).fetchOverview(testStudentId);
      expect(overview.hasPrediction, isFalse);
      expect(backend.requestsTo(rest('risk_factors')), isEmpty);
    });

    test('assignments and submissions', () async {
      backend
        ..onGet(rest('assignments'), [assignmentRow('as1', '2026-09-10T18:00:00Z')])
        ..onGet(rest('assignment_submissions'), [submissionRow('as1', 'submitted', score: 15)]);
      final (assignments, submissions) = await AssignmentsRepository(backend.client).fetch(testStudentId);
      expect(assignments.single.title, 'Assignment as1');
      expect(submissions.single.score, 15);
      expect(backend.requestsTo(rest('assignment_submissions')).single.url.queryParameters['student_id'],
          'eq.$testStudentId');
    });

    test('attendance: current academic year only, fetched page by page', () async {
      backend
        ..onGet(rest('student_courses'), [enrolmentRow('old', '2025-26'), enrolmentRow('cur', '2026-27')])
        ..on('GET', rest('attendance_records'), (request) {
          final offset = int.parse(request.url.queryParameters['offset'] ?? '0');
          return jsonResponse(offset == 0
              ? [attendanceRow('cur', '2026-09-01', 'present'), attendanceRow('cur', '2026-09-02', 'absent')]
              : [attendanceRow('cur', '2026-09-03', 'late')]);
        });
      final data = await AttendanceRepository(backend.client, pageSize: 2).fetchCurrentYear(testStudentId);
      expect(data.academicYear, '2026-27');
      expect(data.courses.single.studentCourseId, 'cur');
      expect(data.records, hasLength(3));
      final pages = backend.requestsTo(rest('attendance_records')).toList();
      expect(pages, hasLength(2));
      expect(pages.first.url.queryParameters['student_course_id'], 'in.("cur")');
      expect(pages.first.url.queryParameters['student_id'], 'eq.$testStudentId');
    });

    test('attendance: no enrolments', () async {
      backend.onGet(rest('student_courses'), <Object>[]);
      final data = await AttendanceRepository(backend.client).fetchCurrentYear(testStudentId);
      expect(data.academicYear, isNull);
      expect(backend.requestsTo(rest('attendance_records')), isEmpty);
    });
  });

  group('profile, student record, onboarding, recommendations', () {
    test('profile and linked record', () async {
      backend
        ..onGet(rest('profiles'), [profileRow()])
        ..onGet(rest('students'), <Object>[]);
      expect((await ProfileRepository(backend.client).fetchOwnProfile(testUserId))!.isOnboarded, isTrue);
      expect(await StudentRepository(backend.client).fetchOwnRecord(testUserId), isNull);
      expect(backend.requestsTo(rest('profiles')).single.url.queryParameters['id'], 'eq.$testUserId');
      expect(backend.requestsTo(rest('students')).single.url.queryParameters['user_id'], 'eq.$testUserId');
    });

    test('claiming a record uses the server-side function; mismatches are reported clearly', () async {
      backend.on('POST', rpcPath('claim_student_record'), (_) => jsonResponse(testStudentId));
      expect(await OnboardingRepository(backend.client).claimStudentRecord(), testStudentId);
      backend.on('POST', rpcPath('claim_student_record'),
          (_) => postgrestError('P0001', 'sews:no_matching_student_record'));
      await expectLater(
          OnboardingRepository(backend.client).claimStudentRecord(), throwsA(_failure(FailureKind.noStudentRecord)));
    });

    test('complete onboarding sends only the notice version', () async {
      backend.on('POST', rpcPath('complete_onboarding'), (_) => jsonResponse(null));
      await OnboardingRepository(backend.client).completeOnboarding('v1');
      final body = jsonDecode(backend.requestsTo(rpcPath('complete_onboarding')).single.body);
      expect(body, {'p_privacy_notice_version': 'v1'});
    });

    test('recommended actions come from the student-safe function', () async {
      backend.on('POST', rpcPath('get_my_recommended_actions'), (_) => jsonResponse([actionRow()]));
      final actions = await RecommendationsRepository(backend.client).fetchOpenActions();
      expect(actions.single.status.label, 'Offered to you');
    });
  });

  group('notifications', () {
    test('mark as read updates only read_at of that notification', () async {
      backend.on('PATCH', rest('notifications'), (_) => jsonResponse([{'id': 'n1'}]));
      await NotificationsRepository(backend.client).markRead('n1', now: DateTime.utc(2026, 9, 24, 10));
      final request = backend.requestsTo(rest('notifications')).single;
      expect(request.url.queryParameters['id'], 'eq.n1');
      expect(jsonDecode(request.body), {'read_at': '2026-09-24T10:00:00.000Z'});
    });

    test('a notification the user cannot update is reported, not ignored', () async {
      backend.on('PATCH', rest('notifications'), (_) => jsonResponse(<Object>[]));
      await expectLater(
          NotificationsRepository(backend.client).markRead('someone-else'), throwsA(_failure(FailureKind.forbidden)));
    });
  });

  group('failures', () {
    test('network failure', () async {
      backend.networkError = http.ClientException('offline');
      await expectLater(RiskRepository(backend.client).fetchOverview(testStudentId), throwsA(_failure(FailureKind.network)));
    });

    test('permission denied', () async {
      backend.on('GET', rest('academic_records'), (_) => postgrestError('42501', 'permission denied', status: 403));
      backend.onGet(rest('student_courses'), <Object>[]);
      await expectLater(
          AcademicsRepository(backend.client).fetchOverview(testStudentId), throwsA(_failure(FailureKind.forbidden)));
    });

    test('invalid data from the server', () async {
      backend.onGet(rest('risk_predictions'), [predictionRow(level: 'critical')]);
      await expectLater(
          RiskRepository(backend.client).fetchOverview(testStudentId), throwsA(_failure(FailureKind.invalidData)));
      backend.onGet(rest('notifications'), {'not': 'a list'});
      await expectLater(
          NotificationsRepository(backend.client).fetchRecent(testUserId), throwsA(_failure(FailureKind.invalidData)));
    });
  });
}
