/// Strict readers for JSON rows returned by Supabase. Any missing or mistyped field
/// throws a [FormatException] naming the field, which the app reports as invalid data
/// instead of crashing or silently showing wrong values.
abstract final class Json {
  static List<Map<String, dynamic>> rows(Object? response) {
    if (response is! List) throw const FormatException('Expected a list of rows');
    return [
      for (final row in response)
        if (row is Map<String, dynamic>) row else throw const FormatException('Expected an object row'),
    ];
  }

  static Map<String, dynamic> object(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is Map<String, dynamic>) return value;
    throw FormatException('Expected object for "$key"');
  }

  static Map<String, dynamic>? objectOrNull(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value == null) return null;
    if (value is Map<String, dynamic>) return value;
    throw FormatException('Expected object or null for "$key"');
  }

  static String string(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is String && value.isNotEmpty) return value;
    throw FormatException('Expected non-empty string for "$key"');
  }

  static String? stringOrNull(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value == null) return null;
    if (value is String) return value;
    throw FormatException('Expected string or null for "$key"');
  }

  static num number(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is num && value.isFinite) return value;
    throw FormatException('Expected finite number for "$key"');
  }

  static num? numberOrNull(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value == null) return null;
    if (value is num && value.isFinite) return value;
    throw FormatException('Expected finite number or null for "$key"');
  }

  static int integer(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is int) return value;
    throw FormatException('Expected integer for "$key"');
  }

  static int? integerOrNull(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value == null) return null;
    if (value is int) return value;
    throw FormatException('Expected integer or null for "$key"');
  }

  static DateTime dateTime(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is String) {
      final parsed = DateTime.tryParse(value);
      if (parsed != null) return parsed;
    }
    throw FormatException('Expected ISO-8601 timestamp for "$key"');
  }

  static DateTime? dateTimeOrNull(Map<String, dynamic> json, String key) =>
      json[key] == null ? null : dateTime(json, key);

  /// Parses a `YYYY-MM-DD` date column as a local calendar date.
  static DateTime date(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is String && RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) {
      final parts = value.split('-').map(int.parse).toList();
      final parsed = DateTime(parts[0], parts[1], parts[2]);
      if (parsed.year == parts[0] && parsed.month == parts[1] && parsed.day == parts[2]) return parsed;
    }
    throw FormatException('Expected YYYY-MM-DD date for "$key"');
  }

  static DateTime? dateOrNull(Map<String, dynamic> json, String key) => json[key] == null ? null : date(json, key);

  /// Parses a controlled-vocabulary value into an enum; unknown values are invalid data.
  static T enumValue<T extends Enum>(Map<String, dynamic> json, String key, Map<String, T> values) {
    final raw = string(json, key);
    final value = values[raw];
    if (value == null) throw FormatException('Unexpected value for "$key"');
    return value;
  }
}
