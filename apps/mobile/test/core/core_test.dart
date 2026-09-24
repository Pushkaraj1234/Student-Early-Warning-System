import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sews_mobile/core/config/app_config.dart';
import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

String _jwt(Map<String, Object> payload) {
  String enc(Map<String, Object> m) => base64Url.encode(utf8.encode(jsonEncode(m))).replaceAll('=', '');
  return '${enc({'alg': 'HS256'})}.${enc(payload)}.sig';
}

void main() {
  group('AppConfig', () {
    test('accepts an https URL with a publishable key', () {
      final config = AppConfig.validate(url: 'https://x.supabase.co', key: 'sb_publishable_abc');
      expect(config.supabaseUrl, 'https://x.supabase.co');
    });

    test('accepts a legacy anon JWT key', () {
      expect(() => AppConfig.validate(url: 'https://x.supabase.co', key: _jwt({'role': 'anon'})), returnsNormally);
    });

    test('rejects missing values', () {
      expect(() => AppConfig.validate(url: '', key: 'k'), throwsA(isA<ConfigException>()));
      expect(() => AppConfig.validate(url: 'https://x.supabase.co', key: ' '), throwsA(isA<ConfigException>()));
    });

    test('rejects insecure remote URLs but allows local development hosts', () {
      expect(() => AppConfig.validate(url: 'http://x.supabase.co', key: 'k'), throwsA(isA<ConfigException>()));
      expect(() => AppConfig.validate(url: 'http://10.0.2.2:54321', key: 'k'), returnsNormally);
    });

    test('rejects secret and service-role keys', () {
      expect(() => AppConfig.validate(url: 'https://x.supabase.co', key: 'sb_secret_abc'),
          throwsA(isA<ConfigException>()));
      expect(() => AppConfig.validate(url: 'https://x.supabase.co', key: _jwt({'role': 'service_role'})),
          throwsA(isA<ConfigException>()));
    });
  });

  group('AppFailure mapping', () {
    test('network errors', () {
      expect(AppFailure.from(const SocketException('down')).kind, FailureKind.network);
      expect(AppFailure.from(http.ClientException('down')).kind, FailureKind.network);
      expect(AppFailure.from(AuthRetryableFetchException()).kind, FailureKind.network);
    });

    test('auth errors', () {
      expect(AppFailure.from(const AuthApiException('x', code: 'invalid_credentials')).kind,
          FailureKind.invalidCredentials);
      expect(AppFailure.from(const AuthApiException('x', code: 'email_not_confirmed')).kind,
          FailureKind.emailNotConfirmed);
      expect(AppFailure.from(AuthWeakPasswordException(message: 'x', statusCode: '422', reasons: const [])).kind,
          FailureKind.weakPassword);
      expect(AppFailure.from(const AuthApiException('x', code: 'over_email_send_rate_limit')).kind,
          FailureKind.rateLimited);
    });

    test('database errors', () {
      expect(AppFailure.from(const PostgrestException(message: 'sews:no_matching_student_record', code: 'P0001')).kind,
          FailureKind.noStudentRecord);
      expect(AppFailure.from(const PostgrestException(message: 'permission denied', code: '42501')).kind,
          FailureKind.forbidden);
      expect(AppFailure.from(const PostgrestException(message: 'JWT expired', code: 'PGRST301')).kind,
          FailureKind.unauthenticated);
      expect(AppFailure.from(const PostgrestException(message: 'boom', code: 'XX000')).kind, FailureKind.server);
    });

    test('invalid data and unknown errors', () {
      expect(AppFailure.from(const FormatException('bad')).kind, FailureKind.invalidData);
      expect(AppFailure.from(StateError('x')).kind, FailureKind.unknown);
    });

    test('user messages never contain raw exception text', () {
      const secret = 'relation "private.secret_table" does not exist';
      for (final error in <Object>[
        const PostgrestException(message: secret, code: 'XX000'),
        Exception(secret),
        const FormatException(secret),
      ]) {
        expect(userMessageFor(error), isNot(contains('secret_table')));
      }
    });
  });

  group('Json readers', () {
    test('reject missing and mistyped fields', () {
      expect(() => Json.string({'a': 1}, 'a'), throwsFormatException);
      expect(() => Json.number({'a': 'x'}, 'a'), throwsFormatException);
      expect(() => Json.number({'a': double.nan}, 'a'), throwsFormatException);
      expect(() => Json.date({'d': '2026-02-30'}, 'd'), throwsFormatException);
      expect(() => Json.rows({'not': 'a list'}), throwsFormatException);
      expect(Json.date({'d': '2026-02-28'}, 'd'), DateTime(2026, 2, 28));
    });
  });

  group('formatting', () {
    test('percent, numbers and scores', () {
      expect(formatPercent(0.724), '72%');
      expect(formatNumber(8.50), '8.5');
      expect(formatNumber(15.0), '15');
      expect(formatScore(15, 20), '15 / 20');
    });
  });
}
