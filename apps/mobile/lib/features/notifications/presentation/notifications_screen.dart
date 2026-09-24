import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/notifications/domain/app_notification.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  Future<void> _open(BuildContext context, WidgetRef ref, AppNotification n) async {
    if (n.isRead) return;
    try {
      await ref.read(notificationsRepositoryProvider).markRead(n.id);
      ref.invalidate(notificationsProvider);
    } on AppFailure catch (failure) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(failure.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('Notifications')),
        body: AsyncValueView<List<AppNotification>>(
          value: ref.watch(notificationsProvider),
          onRetry: () => ref.invalidate(notificationsProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'You have no notifications.',
          emptyIcon: Icons.notifications_none,
          data: (items) => RefreshIndicator(
            onRefresh: () async => ref.invalidate(notificationsProvider),
            child: ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final n = items[index];
                return ListTile(
                  leading: Icon(n.isRead ? Icons.notifications_none : Icons.notifications_active),
                  title: Text(n.title, style: TextStyle(fontWeight: n.isRead ? FontWeight.normal : FontWeight.bold)),
                  subtitle: Text('${n.body}\n${formatDateTime(n.createdAt)}'),
                  isThreeLine: true,
                  onTap: () => _open(context, ref, n),
                );
              },
            ),
          ),
        ),
      );
}
