import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/auth/data/auth_repository.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

enum AuthStatus { unknown, signedOut, signedIn, passwordRecovery }

class AuthSnapshot {
  const AuthSnapshot(this.status, {this.userId, this.email});

  const AuthSnapshot.unknown() : this(AuthStatus.unknown);

  final AuthStatus status;
  final String? userId;
  final String? email;

  @override
  bool operator ==(Object other) =>
      other is AuthSnapshot && other.status == status && other.userId == userId && other.email == email;

  @override
  int get hashCode => Object.hash(status, userId, email);
}

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.watch(supabaseClientProvider).auth),
);

/// Tracks the signed-in state from Supabase Auth events. Supabase restores a persisted
/// session at startup and replays it as an event, which is what restores the session
/// after an app restart. A password-recovery link keeps the app in recovery mode until
/// the new password has been saved or the user signs out.
class AuthController extends Notifier<AuthSnapshot> {
  StreamSubscription<AuthState>? _subscription;
  bool _recovering = false;

  @override
  AuthSnapshot build() {
    final repository = ref.watch(authRepositoryProvider);
    _subscription = repository.authStateChanges.listen(
      _onAuthState,
      // Refresh failures surface later as a signed-out event or a failed request.
      onError: (Object _) {},
    );
    ref.onDispose(() => _subscription?.cancel());
    return const AuthSnapshot.unknown();
  }

  void _onAuthState(AuthState event) {
    final user = event.session?.user;
    if (event.event == AuthChangeEvent.passwordRecovery) _recovering = true;
    if (event.event == AuthChangeEvent.signedOut || user == null) {
      _recovering = false;
      state = const AuthSnapshot(AuthStatus.signedOut);
      return;
    }
    state = AuthSnapshot(
      _recovering ? AuthStatus.passwordRecovery : AuthStatus.signedIn,
      userId: user.id,
      email: user.email,
    );
  }

  /// Called after the new password has been saved.
  void completePasswordRecovery() {
    if (!_recovering) return;
    _recovering = false;
    if (state.userId != null) {
      state = AuthSnapshot(AuthStatus.signedIn, userId: state.userId, email: state.email);
    }
  }
}

final authControllerProvider = NotifierProvider<AuthController, AuthSnapshot>(AuthController.new);

/// The signed-in user's id, or null. Data providers watch this so that all cached
/// data is discarded when the user signs out or a different user signs in.
final currentUserIdProvider = Provider<String?>(
  (ref) => ref.watch(
    authControllerProvider.select((s) => s.status == AuthStatus.signedIn ? s.userId : null),
  ),
);
