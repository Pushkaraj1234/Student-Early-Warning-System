import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/core/widgets/section_card.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/mentor/domain/mentor_models.dart';
import 'package:sews_mobile/features/notifications/domain/app_notification.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:sews_mobile/features/risk/presentation/risk_widgets.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';

/// Mentor home: caseload overview, rising risk, recent alerts and intervention status.
class MentorDashboardScreen extends ConsumerWidget {
  const MentorDashboardScreen({super.key});

  void _refresh(WidgetRef ref) => ref
    ..invalidate(caseloadProvider)
    ..invalidate(mentorInterventionsProvider)
    ..invalidate(notificationsProvider);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(notificationsRealtimeProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('My students'), actions: const [ShellActions()]),
      body: RefreshIndicator(
        onRefresh: () async => _refresh(ref),
        child: AsyncValueView<List<CaseloadEntry>>(
          value: ref.watch(caseloadProvider),
          onRetry: () => _refresh(ref),
          isEmpty: (c) => c.isEmpty,
          emptyMessage: 'No students are assigned to you yet.',
          emptyIcon: Icons.groups_outlined,
          data: (caseload) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              SectionCard(title: 'Risk distribution', child: RiskDistributionView(distribution: RiskDistribution(caseload))),
              const SizedBox(height: 12),
              SectionCard(title: 'Rising risk', child: _RisingRisk(caseload: caseload)),
              const SizedBox(height: 12),
              const SectionCard(title: 'Recent alerts', child: _RecentAlerts()),
              const SizedBox(height: 12),
              const SectionCard(title: 'Intervention status', child: _InterventionStatus()),
              const SizedBox(height: 12),
              SectionCard(
                title: 'All students (${caseload.length})',
                child: Column(children: [for (final e in caseload) CaseloadTile(entry: e)]),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class RiskDistributionView extends StatelessWidget {
  const RiskDistributionView({super.key, required this.distribution});

  final RiskDistribution distribution;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final level in RiskLevel.values.reversed)
            Chip(
              avatar: Icon(riskIcon(level), color: riskColor(level), size: 18),
              label: Text('${level.label}: ${distribution.counts[level]}'),
            ),
          Chip(label: Text('No signal yet: ${distribution.noPrediction}')),
        ],
      );
}

class _RisingRisk extends StatelessWidget {
  const _RisingRisk({required this.caseload});

  final List<CaseloadEntry> caseload;

  @override
  Widget build(BuildContext context) {
    final rising = caseload.where((e) => e.isRising).toList()
      ..sort((a, b) => (b.riskDelta ?? 0).compareTo(a.riskDelta ?? 0));
    if (rising.isEmpty) {
      return const EmptyView(message: 'No student has a rising risk estimate.', icon: Icons.trending_flat, compact: true);
    }
    return Column(children: [for (final e in rising) CaseloadTile(entry: e)]);
  }
}

class _RecentAlerts extends ConsumerWidget {
  const _RecentAlerts();

  @override
  Widget build(BuildContext context, WidgetRef ref) => AsyncValueView<List<AppNotification>>(
        value: ref.watch(notificationsProvider),
        onRetry: () => ref.invalidate(notificationsProvider),
        compact: true,
        isEmpty: (items) => !items.any((n) => n.isStaffAlert),
        emptyMessage: 'No recent alerts.',
        emptyIcon: Icons.notifications_none,
        data: (items) => Column(
          children: [
            for (final n in items.where((n) => n.isStaffAlert).take(5))
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(n.isRead ? Icons.notifications_none : Icons.notifications_active),
                title: Text(n.title),
                subtitle: Text('${n.body}\n${formatDateTime(n.createdAt)}'),
                isThreeLine: true,
              ),
          ],
        ),
      );
}

class _InterventionStatus extends ConsumerWidget {
  const _InterventionStatus();

  @override
  Widget build(BuildContext context, WidgetRef ref) => AsyncValueView<List<StaffIntervention>>(
        value: ref.watch(mentorInterventionsProvider),
        onRetry: () => ref.invalidate(mentorInterventionsProvider),
        compact: true,
        isEmpty: (items) => items.isEmpty,
        emptyMessage: 'No interventions yet.',
        emptyIcon: Icons.task_alt,
        data: (items) => Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final status in InterventionStatus.values)
              if (items.any((i) => i.status == status))
                Chip(label: Text('${status.label}: ${items.where((i) => i.status == status).length}')),
          ],
        ),
      );
}

class CaseloadTile extends StatelessWidget {
  const CaseloadTile({super.key, required this.entry});

  final CaseloadEntry entry;

  @override
  Widget build(BuildContext context) {
    final level = entry.level;
    final details = [
      entry.rollNumber,
      'Semester ${entry.currentSemester}',
      if (entry.trajectory != null) entry.trajectory!.staffLabel,
      if (entry.openInterventions > 0) '${entry.openInterventions} open',
    ].join(' · ');
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(entry.fullName),
      subtitle: Text(details),
      trailing: level == null ? const Text('No signal') : RiskLevelBadge(level: level),
      onTap: () => context.push(Routes.mentorStudent(entry.studentId)),
    );
  }
}
