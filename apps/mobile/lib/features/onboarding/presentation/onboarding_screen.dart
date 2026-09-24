import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/config/app_config.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/presentation/auth_widgets.dart';
import 'package:sews_mobile/features/student/domain/student_record.dart';

/// Privacy notice shown before first use.
/// NOTE: draft wording — the partner institution must review and approve it (and bump
/// AppConfig.privacyNoticeVersion) before the app is used with real student data.
const List<String> privacyNoticeV1 = [
  'SEWS uses information your institution already holds about you — your courses, marks, '
      'attendance, assignment submissions and learning-platform activity — to spot early signs '
      'that you might benefit from support.',
  'A statistical model produces an early-warning signal: Stable, Watch, Elevated or High. It is an '
      'estimate, not a prediction of your results, and it is never used on its own to make decisions about you.',
  'You, your assigned mentor and authorised staff at your institution can see your signal. '
      'Staff notes are not shown in this app.',
  'Your institution is responsible for this information. Contact them to ask about, correct or delete it.',
];

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  bool _busy = false;
  bool _accepted = false;
  AppFailure? _failure;

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await action();
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _claim() => _run(() async {
        await ref.read(onboardingRepositoryProvider).claimStudentRecord();
        ref.invalidate(studentRecordProvider);
      });

  Future<void> _finish() => _run(() async {
        await ref.read(onboardingRepositoryProvider).completeOnboarding(AppConfig.privacyNoticeVersion);
        // The router moves to the dashboard once the refreshed profile is onboarded.
        ref.invalidate(profileProvider);
      });

  @override
  Widget build(BuildContext context) {
    final record = ref.watch(studentRecordProvider);
    final email = ref.watch(authControllerProvider.select((s) => s.email));
    return AuthScaffold(
      title: 'Welcome to SEWS',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_failure != null) ...[MessageBanner(message: _failure!.message), const SizedBox(height: 16)],
          AsyncValueView<StudentRecord?>(
            value: record,
            onRetry: () => ref.invalidate(studentRecordProvider),
            data: (linked) => linked == null ? _linkStep(email) : _noticeStep(linked),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: _busy ? null : () => ref.read(authRepositoryProvider).signOut(),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
  }

  Widget _linkStep(String? email) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Step 1 of 2: Link your student record', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          Text(
            'We will look for the student record your institution holds for '
            '${email ?? 'your confirmed email address'}.',
          ),
          const SizedBox(height: 24),
          BusyButton(label: 'Find my student record', busy: _busy, onPressed: _claim),
        ],
      );

  Widget _noticeStep(StudentRecord linked) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Step 2 of 2: How SEWS uses your information', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text('Linked to ${linked.fullName} (${linked.rollNumber})'
              '${linked.programmeName == null ? '' : ', ${linked.programmeName}'}.'),
          const SizedBox(height: 16),
          for (final paragraph in privacyNoticeV1)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [const Text('•  '), Expanded(child: Text(paragraph))],
              ),
            ),
          CheckboxListTile(
            value: _accepted,
            onChanged: _busy ? null : (v) => setState(() => _accepted = v ?? false),
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: const Text('I have read and understood how my information is used.'),
          ),
          const SizedBox(height: 16),
          BusyButton(label: 'Continue', busy: _busy, onPressed: _accepted ? _finish : null),
        ],
      );
}
