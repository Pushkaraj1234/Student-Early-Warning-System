import 'package:sews_mobile/core/data/json.dart';

enum EnrolmentStatus { enrolled, completed, withdrawn }

enum ResultStatus { pending, pass, fail, withheld }

/// UGC CBCS letter grades accepted by the database.
const Set<String> ugcGrades = {'O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'Ab'};

/// One course enrolment (`student_courses` joined with `courses`).
class CourseResult {
  const CourseResult({
    required this.studentCourseId,
    required this.courseId,
    required this.courseCode,
    required this.courseTitle,
    required this.credits,
    required this.academicYear,
    required this.semester,
    required this.status,
    this.marks,
    this.grade,
    this.gradePoints,
    this.resultPublishedAt,
  });

  factory CourseResult.fromJson(Map<String, dynamic> json) {
    final course = Json.object(json, 'courses');
    final grade = Json.stringOrNull(json, 'grade');
    if (grade != null && !ugcGrades.contains(grade)) throw const FormatException('Unexpected grade');
    final marks = Json.numberOrNull(json, 'marks');
    if (marks != null && (marks < 0 || marks > 100)) throw const FormatException('marks out of range');
    return CourseResult(
      studentCourseId: Json.string(json, 'id'),
      courseId: Json.string(json, 'course_id'),
      courseCode: Json.string(course, 'code'),
      courseTitle: Json.string(course, 'title'),
      credits: Json.number(course, 'credits'),
      academicYear: Json.string(json, 'academic_year'),
      semester: Json.integer(json, 'semester'),
      status: Json.enumValue(json, 'status', {for (final s in EnrolmentStatus.values) s.name: s}),
      marks: marks,
      grade: grade,
      gradePoints: Json.integerOrNull(json, 'grade_points'),
      resultPublishedAt: Json.dateTimeOrNull(json, 'result_published_at'),
    );
  }

  static const String columns = 'id, course_id, academic_year, semester, status, marks, grade, grade_points, '
      'result_published_at, courses(code, title, credits)';

  final String studentCourseId;
  final String courseId;
  final String courseCode;
  final String courseTitle;
  final num credits;
  final String academicYear;
  final int semester;
  final EnrolmentStatus status;
  final num? marks;
  final String? grade;
  final int? gradePoints;
  final DateTime? resultPublishedAt;
}

/// Semester-level result (`academic_records`).
class SemesterRecord {
  const SemesterRecord({
    required this.academicYear,
    required this.semester,
    required this.creditsRegistered,
    required this.creditsEarned,
    required this.resultStatus,
    this.sgpa,
    this.cgpa,
    this.publishedAt,
  });

  factory SemesterRecord.fromJson(Map<String, dynamic> json) {
    final sgpa = Json.numberOrNull(json, 'sgpa');
    final cgpa = Json.numberOrNull(json, 'cgpa');
    for (final v in [sgpa, cgpa]) {
      if (v != null && (v < 0 || v > 10)) throw const FormatException('GPA out of range');
    }
    return SemesterRecord(
      academicYear: Json.string(json, 'academic_year'),
      semester: Json.integer(json, 'semester'),
      sgpa: sgpa,
      cgpa: cgpa,
      creditsRegistered: Json.number(json, 'credits_registered'),
      creditsEarned: Json.number(json, 'credits_earned'),
      resultStatus: Json.enumValue(json, 'result_status', {for (final s in ResultStatus.values) s.name: s}),
      publishedAt: Json.dateTimeOrNull(json, 'published_at'),
    );
  }

  static const String columns =
      'academic_year, semester, sgpa, cgpa, credits_registered, credits_earned, result_status, published_at';

  final String academicYear;
  final int semester;
  final num? sgpa;
  final num? cgpa;
  final num creditsRegistered;
  final num creditsEarned;
  final ResultStatus resultStatus;
  final DateTime? publishedAt;

  bool get isPublished => resultStatus == ResultStatus.pass || resultStatus == ResultStatus.fail;
}

class SemesterGroup {
  const SemesterGroup({required this.academicYear, required this.semester, required this.courses, this.record});

  final String academicYear;
  final int semester;
  final List<CourseResult> courses;
  final SemesterRecord? record;
}

class AcademicOverview {
  const AcademicOverview({required this.courses, required this.records});

  final List<CourseResult> courses;
  final List<SemesterRecord> records;

  bool get isEmpty => courses.isEmpty && records.isEmpty;

  /// Most recent semester with a published result (by academic year, then semester).
  SemesterRecord? get latestPublished {
    final published = records.where((r) => r.isPublished).toList()..sort(_bySemester);
    return published.isEmpty ? null : published.last;
  }

  /// Semesters newest first, each with its courses and (if any) its semester record.
  List<SemesterGroup> get semesters {
    final keys = <(String, int)>{
      for (final c in courses) (c.academicYear, c.semester),
      for (final r in records) (r.academicYear, r.semester),
    }.toList()
      ..sort((a, b) {
        final byYear = b.$1.compareTo(a.$1);
        return byYear != 0 ? byYear : b.$2.compareTo(a.$2);
      });
    return [
      for (final key in keys)
        SemesterGroup(
          academicYear: key.$1,
          semester: key.$2,
          courses: courses.where((c) => c.academicYear == key.$1 && c.semester == key.$2).toList()
            ..sort((a, b) => a.courseCode.compareTo(b.courseCode)),
          record: records.where((r) => r.academicYear == key.$1 && r.semester == key.$2).firstOrNull,
        ),
    ];
  }

  static int _bySemester(SemesterRecord a, SemesterRecord b) {
    final byYear = a.academicYear.compareTo(b.academicYear);
    return byYear != 0 ? byYear : a.semester.compareTo(b.semester);
  }
}
