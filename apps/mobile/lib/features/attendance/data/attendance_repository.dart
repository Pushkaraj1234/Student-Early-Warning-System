import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/attendance/domain/attendance_models.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Result of loading the current academic year's attendance. [summary] is null when the
/// student has no enrolments.
class AttendanceData {
  const AttendanceData({required this.courses, required this.records, required this.academicYear});

  final List<EnrolledCourse> courses;
  final List<AttendanceRecord> records;
  final String? academicYear;
}

class AttendanceRepository {
  AttendanceRepository(this._client, {this.pageSize = 1000});

  final SupabaseClient _client;

  /// PostgREST caps rows per response, so records are fetched page by page.
  final int pageSize;

  Future<AttendanceData> fetchCurrentYear(String studentId) => guard(() async {
        final enrolments = Json.rows(
          await _client.from('student_courses').select(EnrolledCourse.columns).eq('student_id', studentId),
        ).map(EnrolledCourse.fromJson).toList();
        if (enrolments.isEmpty) {
          return const AttendanceData(courses: [], records: [], academicYear: null);
        }
        final year = enrolments.map((e) => e.academicYear).reduce((a, b) => a.compareTo(b) >= 0 ? a : b);
        final current = enrolments.where((e) => e.academicYear == year).toList();
        final ids = current.map((e) => e.studentCourseId).toList();

        final records = <AttendanceRecord>[];
        for (var offset = 0;; offset += pageSize) {
          final page = Json.rows(
            await _client
                .from('attendance_records')
                .select(AttendanceRecord.columns)
                .eq('student_id', studentId)
                .inFilter('student_course_id', ids)
                .order('attendance_date', ascending: true)
                .order('id', ascending: true)
                .range(offset, offset + pageSize - 1),
          ).map(AttendanceRecord.fromJson);
          records.addAll(page);
          if (page.length < pageSize) break;
        }
        return AttendanceData(courses: current, records: records, academicYear: year);
      });
}
