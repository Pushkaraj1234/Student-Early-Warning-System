/// The version of this app build. Must match `version:` in pubspec.yaml (checked by a test).
/// The database publishes the minimum supported app version through
/// `public.get_platform_versions()`; older builds are asked to update.
const String appVersion = '2.0.0';

/// Parses `MAJOR.MINOR.PATCH` (build metadata after `+` is ignored). Returns null if invalid.
List<int>? parseVersion(String value) {
  final core = value.split('+').first.trim();
  final parts = core.split('.');
  if (parts.length != 3) return null;
  final numbers = parts.map(int.tryParse).toList();
  if (numbers.any((n) => n == null || n < 0)) return null;
  return numbers.cast<int>();
}

/// True when [current] >= [minimum]. An unparseable minimum never blocks the user.
bool isVersionSupported(String current, String minimum) {
  final cur = parseVersion(current);
  final min = parseVersion(minimum);
  if (cur == null) return false;
  if (min == null) return true;
  for (var i = 0; i < 3; i++) {
    if (cur[i] != min[i]) return cur[i] > min[i];
  }
  return true;
}
