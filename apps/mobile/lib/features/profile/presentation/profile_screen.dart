import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/student/domain/student_record.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  Future<void> _confirmSignOut(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text('You will need to sign in again to use SEWS on this device.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Sign out')),
        ],
      ),
    );
    if (confirmed ?? false) await ref.read(authRepositoryProvider).signOut();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final email = ref.watch(authControllerProvider.select((s) => s.email));
    final profile = ref.watch(profileProvider).value;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          AsyncValueView<StudentRecord?>(
            value: ref.watch(studentRecordProvider),
            onRetry: () => ref.invalidate(studentRecordProvider),
            isEmpty: (r) => r == null,
            emptyMessage: 'No student record is linked to this account.',
            data: (r) => Card(
              child: Column(
                children: [
                  ListTile(title: const Text('Name'), subtitle: Text(r!.fullName)),
                  ListTile(title: const Text('Roll number'), subtitle: Text(r.rollNumber)),
                  if (r.programmeName != null)
                    ListTile(title: const Text('Programme'), subtitle: Text(r.programmeName!)),
                  ListTile(title: const Text('Current semester'), subtitle: Text('${r.currentSemester}')),
                  ListTile(title: const Text('Institutional email'), subtitle: Text(r.institutionalEmail)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(title: const Text('Signed in as'), subtitle: Text(email ?? '—')),
                if (profile?.privacyNoticeVersion != null)
                  ListTile(
                    title: const Text('Privacy notice accepted'),
                    subtitle: Text('Version ${profile!.privacyNoticeVersion}'),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () => _confirmSignOut(context, ref),
            icon: const Icon(Icons.logout),
            label: const Text('Sign out'),
          ),
        ],
      ),
    );
  }
}
