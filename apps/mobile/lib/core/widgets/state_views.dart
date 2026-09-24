import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sews_mobile/core/errors/app_failure.dart';

class LoadingView extends StatelessWidget {
  const LoadingView({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: EdgeInsets.all(compact ? 16 : 32),
          child: const CircularProgressIndicator(semanticsLabel: 'Loading'),
        ),
      );
}

class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.message, this.icon = Icons.inbox_outlined, this.compact = false});

  final String message;
  final IconData icon;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: EdgeInsets.all(compact ? 16 : 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: compact ? 28 : 48, color: theme.colorScheme.outline),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center, style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}

class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.error, required this.onRetry, this.compact = false});

  final Object error;
  final VoidCallback onRetry;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: EdgeInsets.all(compact ? 16 : 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: compact ? 28 : 48, color: theme.colorScheme.error),
            const SizedBox(height: 12),
            Text(userMessageFor(error), textAlign: TextAlign.center, style: theme.textTheme.bodyMedium),
            const SizedBox(height: 12),
            OutlinedButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

/// Renders the four states every async screen must support: loading, error (with
/// retry), empty and data. Retrying shows the loading state again.
class AsyncValueView<T> extends StatelessWidget {
  const AsyncValueView({
    super.key,
    required this.value,
    required this.data,
    required this.onRetry,
    this.isEmpty,
    this.emptyMessage = 'Nothing to show yet.',
    this.emptyIcon = Icons.inbox_outlined,
    this.compact = false,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) data;
  final VoidCallback onRetry;
  final bool Function(T data)? isEmpty;
  final String emptyMessage;
  final IconData emptyIcon;
  final bool compact;

  @override
  Widget build(BuildContext context) => value.when(
        skipLoadingOnRefresh: false,
        loading: () => LoadingView(compact: compact),
        error: (error, _) => ErrorView(error: error, onRetry: onRetry, compact: compact),
        data: (result) {
          final empty = isEmpty;
          if (empty != null && empty(result)) {
            return EmptyView(message: emptyMessage, icon: emptyIcon, compact: compact);
          }
          return data(result);
        },
      );
}
