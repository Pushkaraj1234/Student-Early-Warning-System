import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/academics/domain/academic_models.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class AcademicsRepository {
  AcademicsRepository(this._client);

  final SupabaseClient _client;

  Future<AcademicOverview> fetchOverview(String studentId) => guard(() async {
        final results = await Future.wait([
          _client.from('student_courses').select(CourseResult.columns).eq('student_id', studentId),
          _client.from('academic_records').select(SemesterRecord.columns).eq('student_id', studentId),
        ]);
        return AcademicOverview(
          courses: Json.rows(results[0]).map(CourseResult.fromJson).toList(),
          records: Json.rows(results[1]).map(SemesterRecord.fromJson).toList(),
        );
      });
}
