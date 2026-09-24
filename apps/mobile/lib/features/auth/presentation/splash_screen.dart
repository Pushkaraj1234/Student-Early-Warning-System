import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';

/// Shown while the saved session is restored and the profile is loaded. Also shows the
/// profile error (with retry) and the "account not set up" state.
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final profile = ref.watch(profileProvider);
    final signedIn = auth.status == AuthStatus.signedIn;

    Widget body;
    if (signedIn && profile.hasError && !profile.isLoading) {
      body = ErrorView(error: profile.error!, onRetry: () => ref.invalidate(profileProvider));
    } else if (signedIn && profile.hasValue && !profile.isLoading && profile.value == null) {
      body = const EmptyView(
        message: 'Your account is not fully set up yet. Please sign out and sign in again, '
            'or contact your institution if this continues.',
        icon: Icons.manage_accounts_outlined,
      );
    } else {
      body = const Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.school, size: 56),
          SizedBox(height: 16),
          Text('SEWS'),
          SizedBox(height: 24),
          LoadingView(compact: true),
        ],
      );
    }

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Expanded(child: Center(child: body)),
            if (signedIn && !profile.isLoading && (profile.hasError || profile.value == null))
              Padding(
                padding: const EdgeInsets.all(16),
                child: TextButton(
                  onPressed: () => ref.read(authRepositoryProvider).signOut(),
                  child: const Text('Sign out'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class UnsupportedRoleScreen extends ConsumerWidget {
  const UnsupportedRoleScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const EmptyView(
                    message: 'This app has screens for students, mentors and administrators. Faculty features are not available yet.',
                    icon: Icons.badge_outlined,
                  ),
                  TextButton(
                    onPressed: () => ref.read(authRepositoryProvider).signOut(),
                    child: const Text('Sign out'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
