import 'dart:async';
import 'dart:developer' as developer;

import 'package:http/http.dart' as http;
import 'package:sews_mobile/core/errors/platform_network_error.dart'
    if (dart.library.io) 'package:sews_mobile/core/errors/platform_network_error_io.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

enum FailureKind {
  network,
  unauthenticated,
  forbidden,
  invalidData,
  invalidCredentials,
  emailNotConfirmed,
  weakPassword,
  rateLimited,
  emailInUse,
  emailNotAccepted,
  emailDeliveryUnavailable,
  signupsClosed,
  samePassword,
  noStudentRecord,
  notStudent,
  conflict,
  duplicate,
  invalidInput,
  studentNotLinked,
  server,
  unknown,
}

/// The only error type the UI ever sees. [message] is written for students and never
/// contains exception text, SQL, stack traces or personal data.
class AppFailure implements Exception {
  const AppFailure(this.kind);

  final FailureKind kind;

  String get message => switch (kind) {
        FailureKind.network =>
          'You appear to be offline or the server is unreachable. Check your connection and try again.',
        FailureKind.unauthenticated => 'Your session has expired. Please sign in again.',
        FailureKind.forbidden => "You don't have access to this information.",
        FailureKind.invalidData =>
          'We received information we could not read. Please try again later.',
        FailureKind.invalidCredentials => 'The email or password is incorrect.',
        FailureKind.emailNotConfirmed =>
          'Please confirm your email address first. Check your inbox for the confirmation link.',
        FailureKind.weakPassword =>
          'Choose a stronger password: at least 8 characters with upper- and lower-case letters and a number.',
        FailureKind.rateLimited => 'Too many attempts. Please wait a few minutes and try again.',
        FailureKind.emailInUse => 'An account with this email already exists. Try signing in instead.',
        FailureKind.emailNotAccepted =>
          'This email address is not accepted. Check it for typos and use your institutional email address.',
        FailureKind.emailDeliveryUnavailable =>
          "We can't send a confirmation email to this address yet. Please contact your institution's SEWS administrator.",
        FailureKind.signupsClosed => 'New registrations are closed. Please contact your institution.',
        FailureKind.samePassword => 'Choose a new password that is different from your current one.',
        FailureKind.noStudentRecord =>
          "We couldn't find a student record for your email address. Please contact your institution.",
        FailureKind.notStudent => 'This app is for students. Staff accounts are not supported yet.',
        FailureKind.conflict => 'This was already updated by someone else. Refresh and try again.',
        FailureKind.duplicate => 'An open action of this type already exists for this student.',
        FailureKind.invalidInput => 'Some of the information entered is not valid. Check it and try again.',
        FailureKind.studentNotLinked => 'This student has not activated their app account yet.',
        FailureKind.server => 'The server could not complete the request. Please try again later.',
        FailureKind.unknown => 'Something went wrong. Please try again.',
      };

  /// Maps any error thrown by Supabase, the network stack or parsing code.
  static AppFailure from(Object error) {
    final failure = _map(error);
    // Diagnostics only: the error type and failure kind, never the message payload.
    developer.log('AppFailure(${failure.kind.name}) from ${error.runtimeType}', name: 'sews');
    return failure;
  }

  static AppFailure _map(Object error) {
    if (error is AppFailure) return error;
    if (isPlatformNetworkError(error) ||
        error is http.ClientException ||
        error is TimeoutException ||
        error is AuthRetryableFetchException) {
      return const AppFailure(FailureKind.network);
    }
    if (error is AuthWeakPasswordException) return const AppFailure(FailureKind.weakPassword);
    if (error is AuthException) return _fromAuth(error);
    if (error is PostgrestException) return _fromPostgrest(error);
    if (error is FormatException || error is TypeError) return const AppFailure(FailureKind.invalidData);
    return const AppFailure(FailureKind.unknown);
  }

  static AppFailure _fromAuth(AuthException error) {
    switch (error.code) {
      case 'invalid_credentials':
        return const AppFailure(FailureKind.invalidCredentials);
      case 'email_not_confirmed':
        return const AppFailure(FailureKind.emailNotConfirmed);
      case 'weak_password':
        return const AppFailure(FailureKind.weakPassword);
      case 'over_email_send_rate_limit':
      case 'over_request_rate_limit':
        return const AppFailure(FailureKind.rateLimited);
      case 'user_already_exists':
      case 'email_exists':
        return const AppFailure(FailureKind.emailInUse);
      // The codes below are listed in Supabase's Auth error-code documentation
      // (supabase.com/docs/guides/auth/debugging/error-codes).
      case 'email_address_invalid':
        return const AppFailure(FailureKind.emailNotAccepted);
      case 'email_address_not_authorized':
        return const AppFailure(FailureKind.emailDeliveryUnavailable);
      case 'signup_disabled':
      case 'email_provider_disabled':
        return const AppFailure(FailureKind.signupsClosed);
      case 'same_password':
        return const AppFailure(FailureKind.samePassword);
      case 'validation_failed':
        return const AppFailure(FailureKind.invalidInput);
      case 'session_not_found':
      case 'session_expired':
      case 'refresh_token_not_found':
        return const AppFailure(FailureKind.unauthenticated);
    }
    if (error is AuthSessionMissingException || error.statusCode == '401') {
      return const AppFailure(FailureKind.unauthenticated);
    }
    if (error.statusCode == '429') return const AppFailure(FailureKind.rateLimited);
    return const AppFailure(FailureKind.unknown);
  }

  static AppFailure _fromPostgrest(PostgrestException error) {
    switch (error.message) {
      case 'sews:no_matching_student_record':
        return const AppFailure(FailureKind.noStudentRecord);
      case 'sews:email_not_confirmed':
        return const AppFailure(FailureKind.emailNotConfirmed);
      case 'sews:not_a_student':
        return const AppFailure(FailureKind.notStudent);
      case 'sews:not_authenticated':
        return const AppFailure(FailureKind.unauthenticated);
      case 'sews:rate_limited':
        return const AppFailure(FailureKind.rateLimited);
      case 'sews:forbidden':
        return const AppFailure(FailureKind.forbidden);
      case 'sews:invalid_intervention_transition':
        return const AppFailure(FailureKind.conflict);
      case 'sews:duplicate_intervention':
        return const AppFailure(FailureKind.duplicate);
      case 'sews:student_not_linked':
        return const AppFailure(FailureKind.studentNotLinked);
      case 'sews:invalid_argument':
      case 'sews:invalid_reason':
      case 'sews:invalid_priority':
      case 'sews:invalid_assignee':
      case 'sews:invalid_outcome':
      case 'sews:invalid_message':
      case 'sews:invalid_decline_reason':
      case 'sews:invalid_response':
        return const AppFailure(FailureKind.invalidInput);
    }
    final code = error.code ?? '';
    if (code == '42501') return const AppFailure(FailureKind.forbidden);
    if (code == 'PGRST301' || code == 'PGRST302' || code == '401') {
      return const AppFailure(FailureKind.unauthenticated);
    }
    return const AppFailure(FailureKind.server);
  }

  @override
  String toString() => 'AppFailure(${kind.name})';
}

/// Runs [body] and converts every error into an [AppFailure].
Future<T> guard<T>(Future<T> Function() body) async {
  try {
    return await body();
  } catch (error) {
    throw AppFailure.from(error);
  }
}

/// User-facing text for any error (AppFailure or not).
String userMessageFor(Object error) => AppFailure.from(error).message;
