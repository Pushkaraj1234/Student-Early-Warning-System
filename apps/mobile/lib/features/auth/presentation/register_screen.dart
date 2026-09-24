import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/data/auth_repository.dart';
import 'package:sews_mobile/features/auth/domain/auth_validators.dart';
import 'package:sews_mobile/features/auth/presentation/auth_widgets.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  AppFailure? _failure;

  @override
  void dispose() {
    for (final c in [_name, _email, _password, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy || !(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      final result = await ref.read(authRepositoryProvider).signUp(
            fullName: _name.text,
            email: _email.text,
            password: _password.text,
          );
      if (!mounted) return;
      if (result == SignUpResult.confirmationRequired) {
        context.go(Routes.checkEmail, extra: _email.text.trim());
      }
      // SignUpResult.signedIn: the router moves on when the signed-in event arrives.
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AuthScaffold(
        title: 'Create account',
        child: AutofillGroup(
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Use the email address your institution has on record for you. '
                  "You'll confirm it before your student record is linked.",
                ),
                const SizedBox(height: 24),
                if (_failure != null) ...[MessageBanner(message: _failure!.message), const SizedBox(height: 16)],
                TextFormField(
                  controller: _name,
                  textCapitalization: TextCapitalization.words,
                  autofillHints: const [AutofillHints.name],
                  textInputAction: TextInputAction.next,
                  validator: AuthValidators.fullName,
                  decoration: const InputDecoration(labelText: 'Full name'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  textInputAction: TextInputAction.next,
                  validator: AuthValidators.email,
                  decoration: const InputDecoration(labelText: 'Institutional email'),
                ),
                const SizedBox(height: 16),
                PasswordField(
                  controller: _password,
                  label: 'Password',
                  validator: AuthValidators.newPassword,
                  autofillHints: const [AutofillHints.newPassword],
                  textInputAction: TextInputAction.next,
                ),
                const SizedBox(height: 16),
                PasswordField(
                  controller: _confirm,
                  label: 'Confirm password',
                  validator: (v) => AuthValidators.confirmPassword(v, _password.text),
                  autofillHints: const [AutofillHints.newPassword],
                  onSubmitted: _submit,
                ),
                const SizedBox(height: 8),
                Text(
                  'At least 8 characters, with upper- and lower-case letters and a number.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 24),
                BusyButton(label: 'Create account', busy: _busy, onPressed: _submit),
                TextButton(
                  onPressed: () => context.go(Routes.login),
                  child: const Text('I already have an account'),
                ),
              ],
            ),
          ),
        ),
      );
}
