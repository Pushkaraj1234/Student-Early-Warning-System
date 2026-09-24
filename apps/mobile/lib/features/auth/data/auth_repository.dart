import 'package:sews_mobile/core/config/app_config.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

enum SignUpResult { signedIn, confirmationRequired }

/// Thin wrapper over Supabase Auth. Every method converts errors into [AppFailure].
///
/// Note: the full name is sent as sign-up metadata only for the display name. Roles are
/// never sent — the database assigns every new account the 'student' role.
class AuthRepository {
  AuthRepository(this._auth);

  final GoTrueClient _auth;

  Session? get currentSession => _auth.currentSession;

  Stream<AuthState> get authStateChanges => _auth.onAuthStateChange;

  Future<void> signIn({required String email, required String password}) => guard(() async {
        await _auth.signInWithPassword(email: email.trim(), password: password);
      });

  Future<SignUpResult> signUp({
    required String fullName,
    required String email,
    required String password,
  }) =>
      guard(() async {
        final response = await _auth.signUp(
          email: email.trim(),
          password: password,
          emailRedirectTo: AppConfig.authRedirectUrl,
          data: {'full_name': fullName.trim()},
        );
        return response.session == null ? SignUpResult.confirmationRequired : SignUpResult.signedIn;
      });

  Future<void> resendConfirmation(String email) => guard(() async {
        await _auth.resend(type: OtpType.signup, email: email.trim(), emailRedirectTo: AppConfig.authRedirectUrl);
      });

  Future<void> sendPasswordReset(String email) =>
      guard(() => _auth.resetPasswordForEmail(email.trim(), redirectTo: AppConfig.authRedirectUrl));

  Future<void> updatePassword(String password) => guard(() async {
        await _auth.updateUser(UserAttributes(password: password));
      });

  /// Signs out on this device. Never throws: gotrue removes the local session and emits
  /// `signedOut` BEFORE calling the server, so the user is always signed out locally. A
  /// failed server call only means the refresh token could not be revoked remotely; it
  /// still expires on its own.
  Future<void> signOut() async {
    try {
      await _auth.signOut();
    } catch (error) {
      AppFailure.from(error); // logged for diagnostics only
    }
  }
}
