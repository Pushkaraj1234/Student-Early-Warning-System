import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/layout/breakpoints.dart';
import 'package:sews_mobile/core/routing/routes.dart';

/// Navigation for the four main sections: a bottom bar on phones, a side rail on wider
/// windows (tablets, desktop browsers) — see [Breakpoints.navigationRail].
class HomeShell extends ConsumerWidget {
  const HomeShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  static const List<({IconData icon, String label})> _sections = [
    (icon: Icons.dashboard_outlined, label: 'Home'),
    (icon: Icons.school_outlined, label: 'Academics'),
    (icon: Icons.event_available_outlined, label: 'Attendance'),
    (icon: Icons.assignment_outlined, label: 'Assignments'),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(notificationsRealtimeProvider);
    return MediaQuery.sizeOf(context).width >= Breakpoints.navigationRail ? _withRail() : _withBottomBar();
  }

  void _select(int index) =>
      navigationShell.goBranch(index, initialLocation: index == navigationShell.currentIndex);

  Widget _withBottomBar() => Scaffold(
        body: navigationShell,
        bottomNavigationBar: NavigationBar(
          selectedIndex: navigationShell.currentIndex,
          onDestinationSelected: _select,
          destinations: [
            for (final s in _sections) NavigationDestination(icon: Icon(s.icon), label: s.label),
          ],
        ),
      );

  Widget _withRail() => Scaffold(
        body: Row(
          children: [
            SafeArea(
              right: false,
              child: NavigationRail(
                selectedIndex: navigationShell.currentIndex,
                onDestinationSelected: _select,
                labelType: NavigationRailLabelType.all,
                destinations: [
                  for (final s in _sections)
                    NavigationRailDestination(icon: Icon(s.icon), label: Text(s.label)),
                ],
              ),
            ),
            const VerticalDivider(width: 1),
            Expanded(child: navigationShell),
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
