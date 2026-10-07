import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';

/// Shown for an address that matches no screen (e.g. a mistyped link in the browser).
class NotFoundScreen extends StatelessWidget {
  const NotFoundScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Page not found')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const EmptyView(message: 'This page does not exist.', icon: Icons.link_off),
              FilledButton(onPressed: () => context.go(Routes.splash), child: const Text('Go to SEWS')),
            ],
          ),
        ),
      );
}
