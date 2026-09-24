import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/routing/routes.dart';

/// Bottom navigation for the four main sections.
class HomeShell extends ConsumerWidget {
  const HomeShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(notificationsRealtimeProvider);
    return _scaffold();
  }

  Widget _scaffold() => Scaffold(
        body: navigationShell,
        bottomNavigationBar: NavigationBar(
          selectedIndex: navigationShell.currentIndex,
          onDestinationSelected: (index) =>
              navigationShell.goBranch(index, initialLocation: index == navigationShell.currentIndex),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Home'),
            NavigationDestination(icon: Icon(Icons.school_outlined), label: 'Academics'),
            NavigationDestination(icon: Icon(Icons.event_available_outlined), label: 'Attendance'),
            NavigationDestination(icon: Icon(Icons.assignment_outlined), label: 'Assignments'),
          ],
        ),
      );
}

/// App bar actions shared by the main sections: notifications (with unread count) and profile.
class ShellActions extends ConsumerWidget {
  const ShellActions({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = ref.watch(unreadNotificationCountProvider);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          tooltip: unread == 0 ? 'Notifications' : 'Notifications, $unread unread',
          onPressed: () => context.push(Routes.notifications),
          icon: Badge(
            isLabelVisible: unread > 0,
            label: Text('$unread'),
            child: const Icon(Icons.notifications_outlined),
          ),
        ),
        IconButton(
          tooltip: 'Profile',
          onPressed: () => context.push(Routes.profile),
          icon: const Icon(Icons.account_circle_outlined),
        ),
      ],
    );
  }
}
