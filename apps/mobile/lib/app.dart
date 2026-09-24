import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/routing/app_router.dart';
import 'package:sews_mobile/core/theme/app_theme.dart';

class SewsApp extends ConsumerWidget {
  const SewsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialApp.router(
        title: 'SEWS',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        routerConfig: ref.watch(routerProvider),
      );
}

/// Shown instead of the app when build configuration is missing or unsafe.
class ConfigErrorApp extends StatelessWidget {
  const ConfigErrorApp({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        home: Scaffold(
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Center(child: Text('SEWS is not configured correctly.\n\n$message', textAlign: TextAlign.center)),
            ),
          ),
        ),
      );
}
