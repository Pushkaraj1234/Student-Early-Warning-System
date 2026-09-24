/// Client-side form validation for a better experience. The server (Supabase Auth
/// password policy and database constraints) remains authoritative.
abstract final class AuthValidators {
  static final RegExp _email = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

  static String? email(String? value) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) return 'Enter your email address.';
    if (v.length > 254 || !_email.hasMatch(v)) return 'Enter a valid email address.';
    return null;
  }

  /// Mirrors the project policy: at least 8 characters with lower- and upper-case
  /// letters and a digit (supabase/config.toml `password_requirements`).
  static String? newPassword(String? value) {
    final v = value ?? '';
    if (v.length < 8) return 'Use at least 8 characters.';
    if (v.length > 72) return 'Use at most 72 characters.';
    if (!RegExp('[a-z]').hasMatch(v) || !RegExp('[A-Z]').hasMatch(v) || !RegExp(r'\d').hasMatch(v)) {
      return 'Include upper- and lower-case letters and a number.';
    }
    return null;
  }

  static String? existingPassword(String? value) =>
      (value == null || value.isEmpty) ? 'Enter your password.' : null;

  static String? confirmPassword(String? value, String original) =>
      value == original ? null : 'The passwords do not match.';

  static String? fullName(String? value) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) return 'Enter your name.';
    if (v.length > 120) return 'Use at most 120 characters.';
    return null;
  }
}
