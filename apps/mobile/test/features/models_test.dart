import 'package:flutter_test/flutter_test.dart';
import 'package:sews_mobile/features/academics/domain/academic_models.dart';
import 'package:sews_mobile/features/assignments/domain/assignment_models.dart';
import 'package:sews_mobile/features/attendance/domain/attendance_models.dart';
import 'package:sews_mobile/features/notifications/domain/app_notification.dart';
import 'package:sews_mobile/features/profile/domain/profile.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:sews_mobile/features/risk/domain/feature_labels.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:sews_mobile/features/student/domain/student_record.dart';

import '../helpers/fixtures.dart';

void main() {
  group('risk parsing', () {
    test('valid prediction', () {
      final p = RiskPrediction.fromJson(predictionRow(level: 'watch', provenance: 'benchmark'));
      expect(p.level, RiskLevel.watch);
      expect(p.provenance, DataProvenance.benchmark);
      expect(p.predictionDate, DateTime(2026, 9, 20));
    });

    test('unknown level, out-of-range probability and missing fields are invalid data', () {
      expect(() => RiskPrediction.fromJson(predictionRow(level: 'critical')), throwsFormatException);
      expect(() => RiskPrediction.fromJson(predictionRow(probability: 1.5)), throwsFormatException);
      expect(() => RiskPrediction.fromJson(predictionRow()..remove('model_version')), throwsFormatException);
      expect(() => RiskPrediction.fromJson(predictionRow(provenance: 'real')), throwsFormatException);
    });

    test('factor direction must agree with the contribution sign', () {
      expect(RiskFactor.fromJson(factorRow(1, 'late_submission_rate', 0.3, 0.2)).direction,
          FactorDirection.increasesRisk);
      final inconsistent = factorRow(1, 'late_submission_rate', 0.3, 0.2)..['direction'] = 'decreases_risk';
      expect(() => RiskFactor.fromJson(inconsistent), throwsFormatException);
      expect(() => RiskFactor.fromJson(factorRow(0, 'x', 1, 1)), throwsFormatException);
    });

    test('feature labels format stored values and never guess unknown features', () {
      final attendance = RiskFactor.fromJson(factorRow(1, 'attendance_rate_last_14d', 0.52, 0.61));
      expect(labelFor(attendance.feature).label, 'Attendance in the last 14 days');
      expect(formatFactorValue(attendance), '52%');
      final unknown = RiskFactor.fromJson(factorRow(2, 'mystery_feature', 3.14159, 0.1));
      expect(labelFor(unknown.feature).label, 'mystery_feature');
      expect(formatFactorValue(RiskFactor.fromJson(factorRow(3, 'last_score', null, -0.1))), 'not available');
      expect(directionText(FactorDirection.decreasesRisk), 'Lowered the risk estimate');
    });
  });

  group('academics', () {
    test('parses course results and rejects grades outside the UGC scale', () {
      expect(CourseResult.fromJson(courseResultRow()).grade, 'A+');
      expect(() => CourseResult.fromJson(courseResultRow(grade: 'A++')), throwsFormatException);
      expect(() => CourseResult.fromJson(courseResultRow(marks: 101)), throwsFormatException);
    });

    test('latest published semester ignores pending results', () {
      final overview = AcademicOverview(courses: const [], records: [
        SemesterRecord.fromJson(semesterRow(semester: 1)),
        SemesterRecord.fromJson(semesterRow(semester: 2)),
        SemesterRecord.fromJson(semesterRow(year: '2026-27', semester: 3, status: 'pending')),
      ]);
      expect(overview.latestPublished!.semester, 2);
      expect(overview.semesters.first.semester, 3);
    });

    test('GPA outside 0-10 is invalid', () {
      expect(() => SemesterRecord.fromJson(semesterRow()..['sgpa'] = 11), throwsFormatException);
    });
  });

  group('attendance summary', () {
    final today = DateTime(2026, 9, 24);
    final courses = [
      EnrolledCourse.fromJson(enrolmentRow('a', '2026-27')),
      EnrolledCourse.fromJson(enrolmentRow('b', '2026-27')),
    ];

    test('late counts as attended; excused is excluded; trend windows are 14 days', () {
      final records = [
        AttendanceRecord.fromJson(attendanceRow('a', '2026-09-24', 'present')),
        AttendanceRecord.fromJson(attendanceRow('a', '2026-09-11', 'late')),
        AttendanceRecord.fromJson(attendanceRow('b', '2026-09-10', 'absent')), // previous window
        AttendanceRecord.fromJson(attendanceRow('b', '2026-08-28', 'present')), // first day of previous window
        AttendanceRecord.fromJson(attendanceRow('b', '2026-08-27', 'excused')), // outside both windows
      ];
      final s = AttendanceSummary.compute(academicYear: '2026-27', courses: courses, records: records, today: today);
      expect(s.overall.attended, 3);
      expect(s.overall.counted, 4);
      expect(s.overall.excused, 1);
      expect(s.overall.rate, 0.75);
      expect(s.trend.recent.counted, 2);
      expect(s.trend.recent.rate, 1.0);
      expect(s.trend.previous.counted, 2);
      expect(s.trend.previous.rate, 0.5);
      expect(s.perCourse.first.course.code, 'SYN-a');
      expect(s.lastRecordedOn, DateTime(2026, 9, 24));
    });

    test('no sessions means no rate rather than zero', () {
      final s = AttendanceSummary.compute(academicYear: '2026-27', courses: courses, records: const [], today: today);
      expect(s.overall.rate, isNull);
      expect(s.isEmpty, isTrue);
    });

    test('unknown attendance status is invalid data', () {
      expect(() => AttendanceRecord.fromJson(attendanceRow('a', '2026-09-24', 'sleeping')), throwsFormatException);
    });
  });

  group('assignments', () {
    final now = DateTime.utc(2026, 9, 24, 12);

    test('states and ordering', () {
      final assignments = [
        Assignment.fromJson(assignmentRow('past-sub', '2026-09-10T18:00:00Z')),
        Assignment.fromJson(assignmentRow('past-none', '2026-09-20T18:00:00Z')),
        Assignment.fromJson(assignmentRow('future', '2026-10-01T18:00:00Z')),
        Assignment.fromJson(assignmentRow('missing', '2026-09-15T18:00:00Z')),
      ];
      final submissions = [
        Submission.fromJson(submissionRow('past-sub', 'late', score: 9)),
        Submission.fromJson(submissionRow('missing', 'missing')),
      ];
      final overview = AssignmentOverview.build(assignments, submissions, now);
      expect(overview.items.map((i) => i.assignment.id), ['future', 'past-none', 'missing', 'past-sub']);
      expect(overview.items.map((i) => i.stateAt(now)), [
        AssignmentState.pending,
        AssignmentState.overdue,
        AssignmentState.missing,
        AssignmentState.late,
      ]);
      expect(overview.countsAt(now)[AssignmentState.overdue], 1);
    });
  });

  group('other models', () {
    test('profile, student record, recommended action and notification', () {
      expect(Profile.fromJson(profileRow()).isOnboarded, isTrue);
      expect(() => Profile.fromJson(profileRow(role: 'superuser')), throwsFormatException);
      expect(StudentRecord.fromJson(studentRow()).programmeName, 'B.Tech Computing (synthetic)');
      final action = RecommendedAction.fromJson(actionRow());
      expect(action.type, InterventionType.attendanceFollowUp);
      expect(() => RecommendedAction.fromJson(actionRow(type: 'detention')), throwsFormatException);
      expect(AppNotification.fromJson(notificationRow('n1')).isRead, isFalse);
    });
  });
}
