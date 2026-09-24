import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';

class RecommendedActionsView extends ConsumerWidget {
  const RecommendedActionsView({super.key, this.maxItems = 3});

  final int maxItems;

  @override
  Widget build(BuildContext context, WidgetRef ref) => AsyncValueView<List<RecommendedAction>>(
        value: ref.watch(recommendedActionsProvider),
        onRetry: () => ref.invalidate(recommendedActionsProvider),
        compact: true,
        isEmpty: (actions) => actions.isEmpty,
        emptyMessage: 'No recommended actions right now.',
        emptyIcon: Icons.task_alt,
        data: (actions) => Column(
          children: [for (final action in actions.take(maxItems)) RecommendedActionTile(action: action)],
        ),
      );
}

/// One action. Offers can be accepted or declined; the choice is the student's.
class RecommendedActionTile extends ConsumerStatefulWidget {
  const RecommendedActionTile({super.key, required this.action});

  final RecommendedAction action;

  @override
  ConsumerState<RecommendedActionTile> createState() => _RecommendedActionTileState();
}

class _RecommendedActionTileState extends ConsumerState<RecommendedActionTile> {
  bool _busy = false;

  Future<void> _respond({required bool accept}) async {
    DeclineReason? reason;
    if (!accept) {
      reason = await showDialog<DeclineReason>(context: context, builder: (_) => const _DeclineDialog());
      if (reason == null) return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(recommendationsRepositoryProvider).respond(widget.action.id, accept: accept, reason: reason);
      ref.invalidate(recommendedActionsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(accept ? 'Accepted. Your mentor will follow up.' : 'Thanks for letting us know.')),
        );
      }
    } on AppFailure catch (failure) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(failure.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final action = widget.action;
    final due = action.dueOn;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.support_agent_outlined),
          title: Text(action.type.title),
          subtitle: Text(
            '${action.type.description}\n${action.status.label}${due == null ? '' : ' · by ${formatDate(due)}'}',
          ),
          isThreeLine: true,
        ),
        if (action.awaitsResponse)
          Wrap(
            alignment: WrapAlignment.end,
            spacing: 8,
            children: [
              TextButton(onPressed: _busy ? null : () => _respond(accept: false), child: const Text('Not now')),
              FilledButton.tonal(onPressed: _busy ? null : () => _respond(accept: true), child: const Text('Accept')),
            ],
          ),
      ],
    );
  }
}

class _DeclineDialog extends StatefulWidget {
  const _DeclineDialog();

  @override
  State<_DeclineDialog> createState() => _DeclineDialogState();
}

class _DeclineDialogState extends State<_DeclineDialog> {
  DeclineReason? _reason;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Decline this offer?'),
        content: RadioGroup<DeclineReason>(
          groupValue: _reason,
          onChanged: (value) => setState(() => _reason = value),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Declining is fine. It helps your mentor to know why.'),
              for (final reason in DeclineReason.values)
                RadioListTile<DeclineReason>(contentPadding: EdgeInsets.zero, value: reason, title: Text(reason.label)),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          FilledButton(
            onPressed: _reason == null ? null : () => Navigator.of(context).pop(_reason),
            child: const Text('Decline'),
          ),
        ],
      );
}
