import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/domain/auth_validators.dart';
import 'package:sews_mobile/features/auth/presentation/auth_widgets.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  bool _busy = false;
  bool _sent = false;
  AppFailure? _failure;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy || !(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await ref.read(authRepositoryProvider).sendPasswordReset(_email.text);
      if (mounted) setState(() => _sent = true);
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AuthScaffold(
        title: 'Reset password',
        showBack: true,
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_sent)
                // Deliberately does not reveal whether an account exists for the email.
                const MessageBanner(
                  message: 'If an account exists for that email, we have sent a link to reset your password. '
                      'Open it on this device.',
                  tone: BannerTone.info,
                )
              else ...[
                const Text("Enter your email and we'll send you a link to choose a new password."),
                const SizedBox(height: 16),
                if (_failure != null) ...[MessageBanner(message: _failure!.message), const SizedBox(height: 16)],
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  validator: AuthValidators.email,
                  onFieldSubmitted: (_) => _submit(),
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                const SizedBox(height: 24),
                BusyButton(label: 'Send reset link', busy: _busy, onPressed: _submit),
              ],
              TextButton(onPressed: () => context.go(Routes.login), child: const Text('Back to sign in')),
            ],
          ),
        ),
      );
}

/// Shown after the user opens a password-recovery link (Supabase emits a
/// passwordRecovery event and the router brings the user here).
class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key});

  @override
  ConsumerState<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  AppFailure? _failure;

  @override
  void dispose() {
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy || !(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await ref.read(authRepositoryProvider).updatePassword(_password.text);
      ref.read(authControllerProvider.notifier).completePasswordRecovery();
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AuthScaffold(
        title: 'Choose a new password',
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_failure != null) ...[MessageBanner(message: _failure!.message), const SizedBox(height: 16)],
              PasswordField(
                controller: _password,
                label: 'New password',
                validator: AuthValidators.newPassword,
                autofillHints: const [AutofillHints.newPassword],
                textInputAction: TextInputAction.next,
              ),
              const SizedBox(height: 16),
              PasswordField(
                controller: _confirm,
                label: 'Confirm new password',
                validator: (v) => AuthValidators.confirmPassword(v, _password.text),
                autofillHints: const [AutofillHints.newPassword],
                onSubmitted: _submit,
              ),
              const SizedBox(height: 24),
              BusyButton(label: 'Save password', busy: _busy, onPressed: _submit),
              TextButton(
                onPressed: _busy ? null : () => ref.read(authRepositoryProvider).signOut(),
                child: const Text('Cancel and sign out'),
              ),
            ],
          ),
        ),
      );
}
