import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/domain/auth_validators.dart';
import 'package:sews_mobile/features/auth/presentation/auth_widgets.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  AppFailure? _failure;
  String? _info;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy || !(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _failure = null;
      _info = null;
    });
    try {
      await ref.read(authRepositoryProvider).signIn(email: _email.text, password: _password.text);
      // Navigation happens through the router once the signed-in event arrives.
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resendConfirmation() async {
    setState(() => _busy = true);
    try {
      await ref.read(authRepositoryProvider).resendConfirmation(_email.text);
      if (mounted) {
        setState(() {
          _failure = null;
          _info = 'We sent a new confirmation link to ${_email.text.trim()}.';
        });
      }
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AuthScaffold(
        title: 'Sign in',
        child: AutofillGroup(
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Student Early Warning & Support', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 24),
                if (_failure != null) ...[MessageBanner(message: _failure!.message), const SizedBox(height: 16)],
                if (_info != null) ...[
                  MessageBanner(message: _info!, tone: BannerTone.info),
                  const SizedBox(height: 16),
                ],
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  textInputAction: TextInputAction.next,
                  validator: AuthValidators.email,
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                const SizedBox(height: 16),
                PasswordField(
                  controller: _password,
                  label: 'Password',
                  validator: AuthValidators.existingPassword,
                  onSubmitted: _submit,
                ),
                const SizedBox(height: 24),
                BusyButton(label: 'Sign in', busy: _busy, onPressed: _submit),
                if (_failure?.kind == FailureKind.emailNotConfirmed)
                  TextButton(
                    onPressed: _busy ? null : _resendConfirmation,
                    child: const Text('Resend confirmation email'),
                  ),
                TextButton(
                  onPressed: () => context.push(Routes.forgotPassword),
                  child: const Text('Forgot password?'),
                ),
                const Divider(height: 32),
                OutlinedButton(
                  onPressed: () => context.go(Routes.register),
                  child: const Text('Create an account'),
                ),
              ],
            ),
          ),
        ),
      );
}
