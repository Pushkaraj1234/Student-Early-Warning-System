import 'package:sews_mobile/core/data/json.dart';

enum SubmissionStatus { submitted, late, missing, excused }

/// What the student sees. pending = not submitted, not yet due; overdue = not submitted,
/// due date passed and no submission recorded yet.
enum AssignmentState { pending, overdue, submitted, late, missing, excused }

class Assignment {
  const Assignment({
    required this.id,
    required this.courseCode,
    required this.courseTitle,
    required this.title,
    required this.maxScore,
    required this.dueAt,
  });

  factory Assignment.fromJson(Map<String, dynamic> json) {
    final course = Json.object(json, 'courses');
    final maxScore = Json.number(json, 'max_score');
    if (maxScore <= 0) throw const FormatException('max_score must be positive');
    return Assignment(
      id: Json.string(json, 'id'),
      courseCode: Json.string(course, 'code'),
      courseTitle: Json.string(course, 'title'),
      title: Json.string(json, 'title'),
      maxScore: maxScore,
      dueAt: Json.dateTime(json, 'due_at'),
    );
  }

  static const String columns = 'id, title, max_score, due_at, courses(code, title)';

  final String id;
  final String courseCode;
  final String courseTitle;
  final String title;
  final num maxScore;
  final DateTime dueAt;
}

class Submission {
  const Submission({required this.assignmentId, required this.status, this.submittedAt, this.score});

  factory Submission.fromJson(Map<String, dynamic> json) => Submission(
        assignmentId: Json.string(json, 'assignment_id'),
        status: Json.enumValue(json, 'status', {for (final s in SubmissionStatus.values) s.name: s}),
        submittedAt: Json.dateTimeOrNull(json, 'submitted_at'),
        score: Json.numberOrNull(json, 'score'),
      );

  static const String columns = 'assignment_id, status, submitted_at, score';

  final String assignmentId;
  final SubmissionStatus status;
  final DateTime? submittedAt;
  final num? score;
}

class AssignmentItem {
  const AssignmentItem({required this.assignment, this.submission});

  final Assignment assignment;
  final Submission? submission;

  AssignmentState stateAt(DateTime now) {
    final s = submission;
    if (s != null) {
      return switch (s.status) {
        SubmissionStatus.submitted => AssignmentState.submitted,
        SubmissionStatus.late => AssignmentState.late,
        SubmissionStatus.missing => AssignmentState.missing,
        SubmissionStatus.excused => AssignmentState.excused,
      };
    }
    return assignment.dueAt.isAfter(now) ? AssignmentState.pending : AssignmentState.overdue;
  }
}

class AssignmentOverview {
  const AssignmentOverview(this.items);

  /// Upcoming work first (soonest due), then past work (most recent first).
  factory AssignmentOverview.build(List<Assignment> assignments, List<Submission> submissions, DateTime now) {
    final byAssignment = {for (final s in submissions) s.assignmentId: s};
    final items = [
      for (final a in assignments) AssignmentItem(assignment: a, submission: byAssignment[a.id]),
    ];
    final upcoming = items.where((i) => i.assignment.dueAt.isAfter(now)).toList()
      ..sort((a, b) => a.assignment.dueAt.compareTo(b.assignment.dueAt));
    final past = items.where((i) => !i.assignment.dueAt.isAfter(now)).toList()
      ..sort((a, b) => b.assignment.dueAt.compareTo(a.assignment.dueAt));
    return AssignmentOverview([...upcoming, ...past]);
  }

  final List<AssignmentItem> items;

  Map<AssignmentState, int> countsAt(DateTime now) {
    final counts = {for (final s in AssignmentState.values) s: 0};
    for (final item in items) {
      final state = item.stateAt(now);
      counts[state] = counts[state]! + 1;
    }
    return counts;
  }
}
