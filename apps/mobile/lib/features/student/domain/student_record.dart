import 'package:sews_mobile/core/data/json.dart';

/// The student's own institutional record from `public.students`.
class StudentRecord {
  const StudentRecord({
    required this.id,
    required this.rollNumber,
    required this.fullName,
    required this.institutionalEmail,
    required this.admissionYear,
    required this.currentSemester,
    required this.status,
    this.programmeName,
    this.programmeCode,
  });

  factory StudentRecord.fromJson(Map<String, dynamic> json) {
    final programme = Json.objectOrNull(json, 'programmes');
    return StudentRecord(
      id: Json.string(json, 'id'),
      rollNumber: Json.string(json, 'roll_number'),
      fullName: Json.string(json, 'full_name'),
      institutionalEmail: Json.string(json, 'institutional_email'),
      admissionYear: Json.integer(json, 'admission_year'),
      currentSemester: Json.integer(json, 'current_semester'),
      status: Json.string(json, 'status'),
      programmeName: programme == null ? null : Json.string(programme, 'name'),
      programmeCode: programme == null ? null : Json.string(programme, 'code'),
    );
  }

  static const String columns = 'id, roll_number, full_name, institutional_email, admission_year, '
      'current_semester, status, programmes(code, name)';

  final String id;
  final String rollNumber;
  final String fullName;
  final String institutionalEmail;
  final int admissionYear;
  final int currentSemester;
  final String status;
  final String? programmeName;
  final String? programmeCode;
}
