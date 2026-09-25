import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/data/auth_repository.dart';
import 'package:sews_mobile/features/auth/domain/auth_validators.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../helpers/fake_backend.dart';
import '../helpers/fixtures.dart';

ProviderContainer _container(FakeBackend backend) => ProviderContainer.test(
      overrides: [supabaseClientProvider.overrideWithValue(backend.client)],
      retry: (_, _) => null,
    );

Future<void> _settle() => Future<void>.delayed(const Duration(milliseconds: 10));

Matcher _failure(FailureKind kind) => isA<AppFailure>().having((f) => f.kind, 'kind', kind);

void main() {
  group('validators', () {
    test('email', () {
      expect(AuthValidators.email(''), isNotNull);
      expect(AuthValidators.email('not-an-email'), isNotNull);
      expect(AuthValidators.email(' student@example.com '), isNull);
    });

    test('new password mirrors the server policy', () {
      expect(AuthValidators.newPassword('short1A'), isNotNull);
      expect(AuthValidators.newPassword('alllowercase1'), isNotNull);
      expect(AuthValidators.newPassword('NoDigitsHere'), isNotNull);
      expect(AuthValidators.newPassword('Valid1Password'), isNull);
    });

    test('confirmation and name', () {
      expect(AuthValidators.confirmPassword('a', 'b'), isNotNull);
      expect(AuthValidators.confirmPassword('a', 'a'), isNull);
      expect(AuthValidators.fullName('   '), isNotNull);
    });
  });

  group('AuthRepository + AuthController', () {
    late FakeBackend backend;

    setUp(() => backend = FakeBackend());
    tearDown(() => backend.client.dispose());

    test('sign in succeeds and the controller reports the signed-in user', () async {
      backend.on('POST', tokenPath, (_) => jsonResponse(sessionJson(testUserId, testEmail)));
      final container = _container(backend);
      container.listen(authControllerProvider, (_, _) {});
      await container.read(authRepositoryProvider).signIn(email: testEmail, password: 'Valid1Password');
      await _settle();
      final state = container.read(authControllerProvider);
      expect(state.status, AuthStatus.signedIn);
      expect(state.userId, testUserId);
      expect(container.read(currentUserIdProvider), testUserId);
    });

    test('wrong password, unconfirmed email and network failures map to user-facing failures', () async {
      final repo = AuthRepository(backend.client.auth);
      backend.on('POST', tokenPath, (_) => authError('invalid_credentials'));
      await expectLater(repo.signIn(email: testEmail, password: 'x'), throwsA(_failure(FailureKind.invalidCredentials)));
      backend.on('POST', tokenPath, (_) => authError('email_not_confirmed'));
      await expectLater(repo.signIn(email: testEmail, password: 'x'), throwsA(_failure(FailureKind.emailNotConfirmed)));
      backend.networkError = http.ClientException('offline');
      await expectLater(repo.signIn(email: testEmail, password: 'x'), throwsA(_failure(FailureKind.network)));
    });

    test('registration refused by the project email service gets a specific message', () async {
      for (final (code, kind) in [
        ('email_address_not_authorized', FailureKind.emailDeliveryUnavailable),
        ('email_address_invalid', FailureKind.emailNotAccepted),
        ('signup_disabled', FailureKind.signupsClosed),
      ]) {
        backend.on('POST', signupPath, (_) => authError(code));
        await expectLater(
          AuthRepository(backend.client.auth).signUp(fullName: 'Synthetic Beta', email: testEmail, password: 'Valid1Password'),
          throwsA(_failure(kind)),
          reason: code,
        );
      }
    });

    test('registration without a session requires email confirmation and never sends a role', () async {
      backend.on('POST', signupPath, (_) => jsonResponse(userJson(testUserId, testEmail, confirmed: false)));
      final result = await AuthRepository(backend.client.auth)
          .signUp(fullName: ' Synthetic Beta ', email: testEmail, password: 'Valid1Password');
      expect(result, SignUpResult.confirmationRequired);
      final body = jsonDecode(backend.requestsTo(signupPath).single.body) as Map<String, dynamic>;
      expect(body['data'], {'full_name': 'Synthetic Beta'});
      expect(jsonEncode(body), isNot(contains('role')));
      final redirect = backend.requestsTo(signupPath).single.url.queryParameters['redirect_to'];
      expect(redirect, 'io.sews.app://login-callback');
    });

    test('registration with an immediate session signs the user in', () async {
      backend.on('POST', signupPath, (_) => jsonResponse(sessionJson(testUserId, testEmail)));
      final result = await AuthRepository(backend.client.auth)
          .signUp(fullName: 'Beta', email: testEmail, password: 'Valid1Password');
      expect(result, SignUpResult.signedIn);
    });

    test('a persisted session is restored (session restoration)', () async {
      final container = _container(backend);
      container.listen(authControllerProvider, (_, _) {});
      expect(container.read(authControllerProvider).status, AuthStatus.unknown);
      await backend.client.auth.recoverSession(jsonEncode(sessionJson(testUserId, testEmail)));
      await _settle();
      expect(container.read(authControllerProvider).status, AuthStatus.signedIn);
      expect(backend.requests, isEmpty, reason: 'a valid stored session needs no network call');
    });

    test('logout signs out locally even when the server cannot be reached', () async {
      backend.on('POST', tokenPath, (_) => jsonResponse(sessionJson(testUserId, testEmail)));
      final container = _container(backend);
      container.listen(authControllerProvider, (_, _) {});
      final repo = container.read(authRepositoryProvider);
      await repo.signIn(email: testEmail, password: 'Valid1Password');
      await _settle();
      backend.networkError = http.ClientException('offline');
      await repo.signOut();
      await _settle();
      expect(container.read(authControllerProvider).status, AuthStatus.signedOut);
      expect(container.read(currentUserIdProvider), isNull);
      expect(backend.client.auth.currentSession, isNull);
    });
  });

  group('password recovery', () {
    test('stays in recovery mode until the new password is saved', () async {
      final backend = FakeBackend();
      addTearDown(backend.client.dispose);
      final events = StreamController<AuthState>();
      addTearDown(events.close);
      final container = ProviderContainer.test(overrides: [
        supabaseClientProvider.overrideWithValue(backend.client),
        authRepositoryProvider.overrideWithValue(_StreamAuthRepository(backend.client.auth, events.stream)),
      ]);
      container.listen(authControllerProvider, (_, _) {});
      final session = Session.fromJson(sessionJson(testUserId, testEmail))!;

      events.add(AuthState(AuthChangeEvent.passwordRecovery, session));
      await _settle();
      expect(container.read(authControllerProvider).status, AuthStatus.passwordRecovery);

      events.add(AuthState(AuthChangeEvent.tokenRefreshed, session));
      await _settle();
      expect(container.read(authControllerProvider).status, AuthStatus.passwordRecovery);

      container.read(authControllerProvider.notifier).completePasswordRecovery();
      expect(container.read(authControllerProvider).status, AuthStatus.signedIn);

      events.add(const AuthState(AuthChangeEvent.signedOut, null));
      await _settle();
      expect(container.read(authControllerProvider).status, AuthStatus.signedOut);
    });
  });
}

class _StreamAuthRepository extends AuthRepository {
  _StreamAuthRepository(super.auth, this._events);

  final Stream<AuthState> _events;

  @override
  Stream<AuthState> get authStateChanges => _events;
}
