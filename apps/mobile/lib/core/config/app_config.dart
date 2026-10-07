import 'dart:convert';

import 'package:flutter/foundation.dart';

/// Thrown when build-time configuration is missing or unsafe.
class ConfigException implements Exception {
  const ConfigException(this.message);

  final String message;

  @override
  String toString() => 'ConfigException: $message';
}

/// Build-time configuration supplied with `--dart-define-from-file`.
///
/// Only the project URL and the PUBLISHABLE (anon) key may ever be compiled into the
/// app. Both are safe for clients only because every table is protected by Row Level
/// Security. Secret / service-role keys are rejected outright.
class AppConfig {
  const AppConfig._({required this.supabaseUrl, required this.publishableKey});

  final String supabaseUrl;
  final String publishableKey;

  /// Deep link the mobile app receives email-confirmation and password-recovery links on.
  /// Must be listed in the Supabase project's allowed redirect URLs and in the platform manifests.
  static const String mobileAuthRedirectUrl = 'io.sews.app://login-callback';

  /// Where email-confirmation and password-recovery links return to on this platform.
  static String get authRedirectUrl => authRedirectUrlFor(isWeb: kIsWeb, page: Uri.base);

  /// On the web: the root of the site the app is served from (the app reads the auth code from
  /// the address on start-up); that URL must be in the project's allowed redirect URLs, otherwise
  /// Supabase falls back to its Site URL. Elsewhere: [mobileAuthRedirectUrl].
  static String authRedirectUrlFor({required bool isWeb, required Uri page}) =>
      isWeb ? '${page.origin}/' : mobileAuthRedirectUrl;

  /// Version of the privacy notice shown during onboarding.
  static const String privacyNoticeVersion = 'v1';

  static AppConfig fromEnvironment() => validate(
        url: const String.fromEnvironment('SUPABASE_URL'),
        key: const String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY'),
      );

  static AppConfig validate({required String url, required String key}) {
    final trimmedUrl = url.trim();
    final trimmedKey = key.trim();
    if (trimmedUrl.isEmpty || trimmedKey.isEmpty) {
      throw const ConfigException(
        'SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required. '
        'Run with --dart-define-from-file=config/dev.local.json.',
      );
    }
    final uri = Uri.tryParse(trimmedUrl);
    final isLocalDev = uri != null &&
        uri.scheme == 'http' &&
        const {'localhost', '127.0.0.1', '10.0.2.2'}.contains(uri.host);
    if (uri == null || uri.host.isEmpty || (uri.scheme != 'https' && !isLocalDev)) {
      throw const ConfigException('SUPABASE_URL must be an https URL.');
    }
    if (isSecretKey(trimmedKey)) {
      throw const ConfigException(
        'A secret or service-role key must never be used in the mobile app. '
        'Use the project\'s publishable (anon) key.',
      );
    }
    return AppConfig._(supabaseUrl: trimmedUrl, publishableKey: trimmedKey);
  }

  /// True for `sb_secret_…` keys and legacy JWT keys whose role is `service_role`.
  static bool isSecretKey(String key) {
    if (key.startsWith('sb_secret_')) return true;
    final parts = key.split('.');
    if (parts.length != 3) return false;
    try {
      final payload = utf8.decode(base64Url.decode(base64Url.normalize(parts[1])));
      final decoded = jsonDecode(payload);
      return decoded is Map<String, dynamic> && decoded['role'] == 'service_role';
    } on FormatException {
      return false;
    }
  }
}
