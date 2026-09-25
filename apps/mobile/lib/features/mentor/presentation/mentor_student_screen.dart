import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/section_card.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/mentor/domain/mentor_models.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:sews_mobile/features/risk/domain/feature_labels.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:sews_mobile/features/risk/presentation/risk_widgets.dart';

/// Caveat for staff: model factors are associations, and actions need their judgement.
const String staffModelCaveat =
    'Factors show how the model used each input for this estimate. They are associations, not causes. '
    'Review the student\'s situation before acting.';

class MentorStudentScreen extends ConsumerWidget {
  const MentorStudentScreen({super.key, required this.studentId});

  final String studentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(menteeDetailProvider(studentId));
    return Scaffold(
      appBar: AppBar(title: Text(detail.value?.entry.fullName ?? 'Student')),
      body: AsyncValueView<MenteeDetail>(
        value: detail,
        onRetry: () => ref.invalidate(menteeDetailProvider(studentId)),
        data: (d) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(menteeDetailProvider(studentId)),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _Header(detail: d),
              const SizedBox(height: 12),
              SectionCard(title: 'Weekly trends', child: WeeklyTrendsTable(trends: d.trends)),
              const SizedBox(height: 12),
              SectionCard(title: 'Model factors (latest estimate)', child: _Factors(risk: d.risk)),
              const SizedBox(height: 12),
              SectionCard(
                title: 'Interventions',
                action: IconButton(
                  tooltip: 'New intervention',
                  icon: const Icon(Icons.add),
                  onPressed: () => _createIntervention(context, ref),
                ),
                child: _Interventions(studentId: studentId, items: d.interventions),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () => _sendMessage(context, ref),
                icon: const Icon(Icons.message_outlined),
                label: const Text('Send a message'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _createIntervention(BuildContext context, WidgetRef ref) async {
    final created = await showDialog<bool>(
      context: context,
      builder: (_) => _NewInterventionDialog(studentId: studentId),
    );
    if (created == true) _refreshAll(ref, studentId);
  }

  Future<void> _sendMessage(BuildContext context, WidgetRef ref) async {
    final sent = await showDialog<bool>(context: context, builder: (_) => _MessageDialog(studentId: studentId));
    if (sent == true && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Message sent.')));
    }
  }
}

void _refreshAll(WidgetRef ref, String studentId) => ref
  ..invalidate(menteeDetailProvider(studentId))
  ..invalidate(caseloadProvider)
  ..invalidate(mentorInterventionsProvider);

class _Header extends StatelessWidget {
  const _Header({required this.detail});

  final MenteeDetail detail;

  @override
  Widget build(BuildContext context) {
    final e = detail.entry;
    final latest = detail.risk.latest;
    final theme = Theme.of(context);
    final delta = e.riskDelta;
    return SectionCard(
      title: '${e.rollNumber} · Semester ${e.currentSemester}',
      child: latest == null
          ? const EmptyView(message: 'No early-warning estimate yet.', icon: Icons.hourglass_empty, compact: true)
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    RiskLevelBadge(level: latest.level, large: true),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        [
                          if (e.probability != null) 'Estimate ${formatPercent(e.probability!.toDouble())}',
                          if (delta != null) 'change ${delta >= 0 ? '+' : ''}${formatPercent(delta.toDouble())}',
                          'updated ${formatDate(latest.predictionDate)}',
                        ].join(' · '),
                        style: theme.textTheme.bodySmall,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text('Trajectory: ${latest.trajectory.staffLabel}', style: theme.textTheme.titleSmall),
                const SizedBox(height: 8),
                RiskTrendRow(overview: detail.risk),
                if (latest.provenance != DataProvenance.institutional) ...[
                  const SizedBox(height: 8),
                  ProvenanceNotice(provenance: latest.provenance, forStaff: true),
                ],
              ],
            ),
    );
  }
}

/// Attendance, assignments, grades and LMS activity per week (oldest first, last 8 shown).
class WeeklyTrendsTable extends StatelessWidget {
  const WeeklyTrendsTable({super.key, required this.trends});

  final List<WeeklyTrend> trends;

  @override
  Widget build(BuildContext context) {
    if (trends.isEmpty) {
      return const EmptyView(message: 'No weekly data yet.', icon: Icons.show_chart, compact: true);
    }
    final recent = trends.length > 8 ? trends.sublist(trends.length - 8) : trends;
    String rate(WeeklyTrend t) => t.attendanceRate == null ? '—' : formatPercent(t.attendanceRate!);
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columnSpacing: 16,
        headingRowHeight: 36,
        dataRowMinHeight: 32,
        dataRowMaxHeight: 40,
        columns: const [
          DataColumn(label: Text('Week of')),
          DataColumn(label: Text('Attendance')),
          DataColumn(label: Text('Submitted')),
          DataColumn(label: Text('Mean score')),
          DataColumn(label: Text('LMS events')),
          DataColumn(label: Text('Quiz')),
        ],
        rows: [
          for (final t in recent)
            DataRow(cells: [
              DataCell(Text(formatDate(t.weekStart))),
              DataCell(Text(rate(t))),
              DataCell(Text(t.assignmentsDue == 0 ? '—' : '${t.assignmentsSubmitted}/${t.assignmentsDue}')),
              DataCell(Text(t.meanScorePct == null ? '—' : formatNumber(t.meanScorePct!, maxDecimals: 0))),
              DataCell(Text('${t.engagementEvents}')),
              DataCell(Text('${t.quizAttempts}')),
            ]),
        ],
      ),
    );
  }
}

class _Factors extends StatelessWidget {
  const _Factors({required this.risk});

  final RiskOverview risk;

  @override
  Widget build(BuildContext context) {
    if (risk.latestFactors.isEmpty) {
      return const EmptyView(message: 'No factors were stored for this estimate.', compact: true);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final f in risk.latestFactors)
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            leading: Icon(f.direction == FactorDirection.increasesRisk ? Icons.arrow_upward : Icons.arrow_downward),
            title: Text('${f.rank}. ${labelFor(f.feature).label}'),
            subtitle: Text(
              'Value: ${formatFactorValue(f)} · contribution ${formatNumber(f.contribution, maxDecimals: 3)} · '
              '${directionText(f.direction)}',
            ),
          ),
        const SizedBox(height: 4),
        Text(staffModelCaveat, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _Interventions extends ConsumerWidget {
  const _Interventions({required this.studentId, required this.items});

  final String studentId;
  final List<StaffIntervention> items;

  Future<void> _run(BuildContext context, WidgetRef ref, Future<void> Function() action, String done) async {
    try {
      await action();
      _refreshAll(ref, studentId);
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
    } on AppFailure catch (failure) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(failure.message)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (items.isEmpty) return const EmptyView(message: 'No interventions yet.', icon: Icons.task_alt, compact: true);
    final repo = ref.read(mentorRepositoryProvider);
    return Column(
      children: [
        for (final i in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${i.type.title} · ${i.priority.label} priority'),
                  subtitle: Text([
                    i.status.label,
                    '${i.source.label}${i.ruleId == null ? '' : ' (${i.ruleId})'} · ${formatDate(i.createdAt)}',
                    i.reason,
                    if (i.declineReason != null) 'Student said: ${i.declineReason!.label}',
                    if (i.outcome != null) 'Outcome: ${i.outcome!.label}',
                  ].join('\n')),
                  isThreeLine: true,
                ),
                Wrap(
                  alignment: WrapAlignment.end,
                  spacing: 8,
                  children: [
                    if (i.status == InterventionStatus.recommended)
                      FilledButton.tonal(
                        onPressed: () => _run(context, ref, () => repo.approve(i.id), 'Offered to the student.'),
                        child: const Text('Review & offer'),
                      ),
                    if (i.status == InterventionStatus.accepted)
                      FilledButton.tonal(
                        onPressed: () async {
                          final outcome = await showDialog<InterventionOutcome>(
                            context: context,
                            builder: (_) => const _OutcomeDialog(),
                          );
                          if (outcome != null && context.mounted) {
                            await _run(context, ref, () => repo.complete(i.id, outcome), 'Marked as completed.');
                          }
                        },
                        child: const Text('Complete'),
                      ),
                    if (i.status.isOpen)
                      TextButton(
                        onPressed: () => _run(context, ref, () => repo.cancel(i.id), 'Cancelled.'),
                        child: Text(i.status == InterventionStatus.recommended ? 'Dismiss' : 'Cancel'),
                      ),
                  ],
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _OutcomeDialog extends StatefulWidget {
  const _OutcomeDialog();

  @override
  State<_OutcomeDialog> createState() => _OutcomeDialogState();
}

class _OutcomeDialogState extends State<_OutcomeDialog> {
  InterventionOutcome? _outcome;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Record the outcome'),
        content: RadioGroup<InterventionOutcome>(
          groupValue: _outcome,
          onChanged: (value) => setState(() => _outcome = value),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Your observation only. It is not proof that the intervention caused a change.'),
              for (final o in InterventionOutcome.values)
                RadioListTile<InterventionOutcome>(contentPadding: EdgeInsets.zero, value: o, title: Text(o.label)),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          FilledButton(
            onPressed: _outcome == null ? null : () => Navigator.of(context).pop(_outcome),
            child: const Text('Save'),
          ),
        ],
      );
}

class _NewInterventionDialog extends ConsumerStatefulWidget {
  const _NewInterventionDialog({required this.studentId});

  final String studentId;

  @override
  ConsumerState<_NewInterventionDialog> createState() => _NewInterventionDialogState();
}

class _NewInterventionDialogState extends ConsumerState<_NewInterventionDialog> {
  InterventionType _type = InterventionType.mentorMeeting;
  InterventionPriority _priority = InterventionPriority.medium;
  final TextEditingController _reason = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final reason = _reason.text.trim();
    if (reason.length < 3 || reason.length > 500) {
      setState(() => _error = 'Give a reason of 3 to 500 characters.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref.read(mentorRepositoryProvider).create(
            studentId: widget.studentId,
            type: _type,
            reason: reason,
            priority: _priority,
          );
      if (mounted) Navigator.of(context).pop(true);
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('New intervention'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              DropdownButtonFormField<InterventionType>(
                initialValue: _type,
                decoration: const InputDecoration(labelText: 'Type'),
                items: [
                  for (final t in staffCreatableTypes) DropdownMenuItem(value: t, child: Text(t.title)),
                ],
                onChanged: _saving ? null : (t) => setState(() => _type = t ?? _type),
              ),
              const SizedBox(height: 8),
              SegmentedButton<InterventionPriority>(
                segments: [
                  for (final p in InterventionPriority.values) ButtonSegment(value: p, label: Text(p.label)),
                ],
                selected: {_priority},
                onSelectionChanged: _saving ? null : (s) => setState(() => _priority = s.first),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _reason,
                enabled: !_saving,
                maxLength: 500,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Reason (visible to staff)'),
              ),
              const Text('The student is offered this action and decides whether to accept it.'),
              if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: _saving ? null : () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: _saving ? null : _save, child: const Text('Create')),
        ],
      );
}

class _MessageDialog extends ConsumerStatefulWidget {
  const _MessageDialog({required this.studentId});

  final String studentId;

  @override
  ConsumerState<_MessageDialog> createState() => _MessageDialogState();
}

class _MessageDialogState extends ConsumerState<_MessageDialog> {
  final TextEditingController _body = TextEditingController();
  bool _sending = false;
  String? _error;

  @override
  void dispose() {
    _body.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (_body.text.trim().isEmpty) {
      setState(() => _error = 'Write a message first.');
      return;
    }
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await ref.read(mentorRepositoryProvider).sendMessage(widget.studentId, _body.text);
      if (mounted) Navigator.of(context).pop(true);
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Message the student'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: _body, enabled: !_sending, maxLength: 1000, maxLines: 4),
            const Text('The phone notification only says "You have a new message in SEWS."'),
            if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ),
        actions: [
          TextButton(onPressed: _sending ? null : () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: _sending ? null : _send, child: const Text('Send')),
        ],
      );
}
