import 'package:sews_mobile/core/data/json.dart';

enum AttendanceStatus { present, absent, late, excused }

class EnrolledCourse {
  const EnrolledCourse({
    required this.studentCourseId,
    required this.courseId,
    required this.code,
    required this.title,
    required this.academicYear,
  });

  factory EnrolledCourse.fromJson(Map<String, dynamic> json) {
    final course = Json.object(json, 'courses');
    return EnrolledCourse(
      studentCourseId: Json.string(json, 'id'),
      courseId: Json.string(json, 'course_id'),
      code: Json.string(course, 'code'),
      title: Json.string(course, 'title'),
      academicYear: Json.string(json, 'academic_year'),
    );
  }

  static const String columns = 'id, course_id, academic_year, courses(code, title)';

  final String studentCourseId;
  final String courseId;
  final String code;
  final String title;
  final String academicYear;
}

class AttendanceRecord {
  const AttendanceRecord({required this.studentCourseId, required this.date, required this.status});

  factory AttendanceRecord.fromJson(Map<String, dynamic> json) => AttendanceRecord(
        studentCourseId: Json.string(json, 'student_course_id'),
        date: Json.date(json, 'attendance_date'),
        status: Json.enumValue(json, 'status', {for (final s in AttendanceStatus.values) s.name: s}),
      );

  static const String columns = 'student_course_id, attendance_date, status';

  final String studentCourseId;
  final DateTime date;
  final AttendanceStatus status;
}

/// Attendance rate: (present + late) / (sessions - excused). Excused sessions are left
/// out of the denominator. [rate] is null when no countable session exists.
class AttendanceRate {
  const AttendanceRate({required this.attended, required this.counted, required this.excused});

  factory AttendanceRate.of(Iterable<AttendanceRecord> records) {
    var attended = 0;
    var counted = 0;
    var excused = 0;
    for (final r in records) {
      switch (r.status) {
        case AttendanceStatus.present:
        case AttendanceStatus.late:
          attended++;
          counted++;
        case AttendanceStatus.absent:
          counted++;
        case AttendanceStatus.excused:
          excused++;
      }
    }
    return AttendanceRate(attended: attended, counted: counted, excused: excused);
  }

  final int attended;
  final int counted;
  final int excused;

  double? get rate => counted == 0 ? null : attended / counted;
}

class CourseAttendance {
  const CourseAttendance({required this.course, required this.rate});

  final EnrolledCourse course;
  final AttendanceRate rate;
}

/// The last [windowDays] days compared with the [windowDays] days before them.
class AttendanceTrend {
  const AttendanceTrend({required this.windowDays, required this.recent, required this.previous});

  final int windowDays;
  final AttendanceRate recent;
  final AttendanceRate previous;
}

class AttendanceSummary {
  const AttendanceSummary({
    required this.academicYear,
    required this.overall,
    required this.perCourse,
    required this.trend,
    required this.lastRecordedOn,
  });

  /// Computes the summary from actual records only. [today] is injected for testing.
  factory AttendanceSummary.compute({
    required String academicYear,
    required List<EnrolledCourse> courses,
    required List<AttendanceRecord> records,
    required DateTime today,
    int windowDays = 14,
  }) {
    final day = DateTime(today.year, today.month, today.day);
    final recentStart = day.subtract(Duration(days: windowDays - 1));
    final previousStart = recentStart.subtract(Duration(days: windowDays));
    bool inRange(DateTime d, DateTime from, DateTime toExclusive) => !d.isBefore(from) && d.isBefore(toExclusive);
    final tomorrow = day.add(const Duration(days: 1));
    return AttendanceSummary(
      academicYear: academicYear,
      overall: AttendanceRate.of(records),
      perCourse: [
        for (final course in courses)
          CourseAttendance(
            course: course,
            rate: AttendanceRate.of(records.where((r) => r.studentCourseId == course.studentCourseId)),
          ),
      ]..sort((a, b) => a.course.code.compareTo(b.course.code)),
      trend: AttendanceTrend(
        windowDays: windowDays,
        recent: AttendanceRate.of(records.where((r) => inRange(r.date, recentStart, tomorrow))),
        previous: AttendanceRate.of(records.where((r) => inRange(r.date, previousStart, recentStart))),
      ),
      lastRecordedOn: records.isEmpty ? null : records.map((r) => r.date).reduce((a, b) => a.isAfter(b) ? a : b),
    );
  }

  final String academicYear;
  final AttendanceRate overall;
  final List<CourseAttendance> perCourse;
  final AttendanceTrend trend;
  final DateTime? lastRecordedOn;

  bool get isEmpty => overall.counted == 0 && overall.excused == 0;
}
