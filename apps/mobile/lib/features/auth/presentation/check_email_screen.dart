import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/presentation/auth_widgets.dart';

/// Email verification step after sign-up. Opening the confirmation link on this device
/// signs the user in through the app's deep link; otherwise they can sign in afterwards.
class CheckEmailScreen extends ConsumerStatefulWidget {
  const CheckEmailScreen({super.key, required this.email});

  final String? email;

  @override
  ConsumerState<CheckEmailScreen> createState() => _CheckEmailScreenState();
}

class _CheckEmailScreenState extends ConsumerState<CheckEmailScreen> {
  bool _busy = false;
  String? _message;
  BannerTone _tone = BannerTone.info;

  Future<void> _resend(String email) async {
    setState(() => _busy = true);
    try {
      await ref.read(authRepositoryProvider).resendConfirmation(email);
      if (mounted) {
        setState(() {
          _tone = BannerTone.info;
          _message = 'We sent a new confirmation link.';
        });
      }
    } on AppFailure catch (failure) {
      if (mounted) {
        setState(() {
          _tone = BannerTone.error;
          _message = failure.message;
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final email = widget.email;
    return AuthScaffold(
      title: 'Confirm your email',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(Icons.mark_email_unread_outlined, size: 56),
          const SizedBox(height: 16),
          Text(
            email == null
                ? 'We sent you a confirmation link. Open it to activate your account, then sign in.'
                : 'We sent a confirmation link to $email. Open it to activate your account, then sign in.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          if (_message != null) ...[MessageBanner(message: _message!, tone: _tone), const SizedBox(height: 16)],
          if (email != null)
            OutlinedButton(
              onPressed: _busy ? null : () => _resend(email),
              child: const Text('Resend confirmation email'),
            ),
          const SizedBox(height: 8),
          FilledButton(onPressed: () => context.go(Routes.login), child: const Text('Back to sign in')),
        ],
      ),
    );
  }
}
