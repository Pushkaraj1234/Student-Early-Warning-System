import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/assignments/domain/assignment_models.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';

String assignmentStateLabel(AssignmentState state) => switch (state) {
      AssignmentState.pending => 'Not submitted yet',
      AssignmentState.overdue => 'Overdue',
      AssignmentState.submitted => 'Submitted',
      AssignmentState.late => 'Submitted late',
      AssignmentState.missing => 'Missing',
      AssignmentState.excused => 'Excused',
    };

class AssignmentStateChip extends StatelessWidget {
  const AssignmentStateChip({super.key, required this.state});

  final AssignmentState state;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final attention = state == AssignmentState.overdue || state == AssignmentState.missing;
    return Chip(
      visualDensity: VisualDensity.compact,
      avatar: Icon(attention ? Icons.warning_amber_outlined : Icons.info_outline, size: 16),
      label: Text(assignmentStateLabel(state)),
      backgroundColor: attention ? scheme.errorContainer : scheme.surfaceContainerHighest,
    );
  }
}

class AssignmentsScreen extends ConsumerWidget {
  const AssignmentsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('Assignments'), actions: const [ShellActions()]),
        body: AsyncValueView<AssignmentOverview>(
          value: ref.watch(assignmentOverviewProvider),
          onRetry: () => ref.invalidate(assignmentOverviewProvider),
          isEmpty: (o) => o.items.isEmpty,
          emptyMessage: 'No assignments have been set for your courses yet.',
          emptyIcon: Icons.assignment_outlined,
          data: (o) => RefreshIndicator(
            onRefresh: () async => ref.invalidate(assignmentOverviewProvider),
            child: AssignmentsContent(overview: o, now: ref.read(clockProvider)()),
          ),
        ),
      );
}

class AssignmentsContent extends StatelessWidget {
  const AssignmentsContent({super.key, required this.overview, required this.now});

  final AssignmentOverview overview;
  final DateTime now;

  @override
  Widget build(BuildContext context) => ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: overview.items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final item = overview.items[index];
          final a = item.assignment;
          final score = item.submission?.score;
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(a.title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text('${a.courseCode} · ${a.courseTitle}'),
                  Text('Due ${formatDateTime(a.dueAt)}'),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      AssignmentStateChip(state: item.stateAt(now)),
                      const Spacer(),
                      if (score != null) Text('Score ${formatScore(score, a.maxScore)}'),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      );
}
