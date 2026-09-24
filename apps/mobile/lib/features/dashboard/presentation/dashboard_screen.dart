import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/core/widgets/section_card.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/academics/domain/academic_models.dart';
import 'package:sews_mobile/features/assignments/domain/assignment_models.dart';
import 'package:sews_mobile/features/assignments/presentation/assignments_screen.dart';
import 'package:sews_mobile/features/attendance/domain/attendance_models.dart';
import 'package:sews_mobile/features/recommendations/presentation/recommended_actions_view.dart';
import 'package:sews_mobile/features/risk/presentation/risk_widgets.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref
      ..invalidate(studentRecordProvider)
      ..invalidate(riskOverviewProvider)
      ..invalidate(recommendedActionsProvider)
      ..invalidate(academicOverviewProvider)
      ..invalidate(attendanceSummaryProvider)
      ..invalidate(assignmentOverviewProvider)
      ..invalidate(notificationsProvider);
    try {
      await Future.wait<Object?>([
        ref.read(riskOverviewProvider.future),
        ref.read(academicOverviewProvider.future),
        ref.read(attendanceSummaryProvider.future),
        ref.read(assignmentOverviewProvider.future),
      ]);
    } on Object {
      // Each section shows its own error and retry button.
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final record = ref.watch(studentRecordProvider).value;
    return Scaffold(
      appBar: AppBar(title: const Text('Home'), actions: const [ShellActions()]),
      body: RefreshIndicator(
        onRefresh: () => _refresh(ref),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (record != null) ...[
              Text('Hello, ${record.fullName.split(' ').first}',
                  style: Theme.of(context).textTheme.headlineSmall),
              Text([
                if (record.programmeName != null) record.programmeName!,
                'Semester ${record.currentSemester}',
              ].join(' · ')),
              const SizedBox(height: 16),
            ],
            RiskSummaryCard(onExplain: () => context.push(Routes.risk)),
            const SizedBox(height: 12),
            const SectionCard(title: 'Recommended action', child: RecommendedActionsView(maxItems: 2)),
            const SizedBox(height: 12),
            SectionCard(
              title: 'Check in',
              child: Row(
                children: [
                  const Expanded(child: Text('Tell your mentor if something is getting in the way of your studies.')),
                  const SizedBox(width: 8),
                  OutlinedButton(onPressed: () => context.push(Routes.checkin), child: const Text('Check in')),
                ],
              ),
            ),
            const SizedBox(height: 12),
            SectionCard(
              title: 'Academic summary',
              action: TextButton(onPressed: () => context.go(Routes.academics), child: const Text('View')),
              child: AsyncValueView<AcademicOverview>(
                value: ref.watch(academicOverviewProvider),
                onRetry: () => ref.invalidate(academicOverviewProvider),
                compact: true,
                isEmpty: (o) => o.isEmpty,
                emptyMessage: 'No academic records yet.',
                data: (o) => _AcademicSummary(overview: o),
              ),
            ),
            const SizedBox(height: 12),
            SectionCard(
              title: 'Attendance',
              action: TextButton(onPressed: () => context.go(Routes.attendance), child: const Text('View')),
              child: AsyncValueView<AttendanceSummary?>(
                value: ref.watch(attendanceSummaryProvider),
                onRetry: () => ref.invalidate(attendanceSummaryProvider),
                compact: true,
                isEmpty: (s) => s == null || s.isEmpty,
                emptyMessage: 'No attendance has been recorded yet.',
                data: (s) => _AttendanceSummaryView(summary: s!),
              ),
            ),
            const SizedBox(height: 12),
            SectionCard(
              title: 'Assignments',
              action: TextButton(onPressed: () => context.go(Routes.assignments), child: const Text('View')),
              child: AsyncValueView<AssignmentOverview>(
                value: ref.watch(assignmentOverviewProvider),
                onRetry: () => ref.invalidate(assignmentOverviewProvider),
                compact: true,
                isEmpty: (o) => o.items.isEmpty,
                emptyMessage: 'No assignments yet.',
                data: (o) => _AssignmentSummary(overview: o, now: ref.read(clockProvider)()),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(value, style: Theme.of(context).textTheme.titleLarge),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
}

class _AcademicSummary extends StatelessWidget {
  const _AcademicSummary({required this.overview});

  final AcademicOverview overview;

  @override
  Widget build(BuildContext context) {
    final latest = overview.latestPublished;
    final current = overview.courses.where((c) => c.status == EnrolmentStatus.enrolled).length;
    return Row(
      children: [
        _Metric(label: 'CGPA', value: latest?.cgpa == null ? '—' : formatNumber(latest!.cgpa!)),
        _Metric(
          label: latest == null ? 'Latest SGPA' : 'SGPA, semester ${latest.semester}',
          value: latest?.sgpa == null ? '—' : formatNumber(latest!.sgpa!),
        ),
        _Metric(label: 'Current courses', value: '$current'),
      ],
    );
  }
}

class _AttendanceSummaryView extends StatelessWidget {
  const _AttendanceSummaryView({required this.summary});

  final AttendanceSummary summary;

  @override
  Widget build(BuildContext context) {
    final overall = summary.overall.rate;
    final recent = summary.trend.recent.rate;
    final previous = summary.trend.previous.rate;
    return Row(
      children: [
        _Metric(label: 'Overall (${summary.academicYear})', value: overall == null ? '—' : formatPercent(overall)),
        _Metric(label: 'Last ${summary.trend.windowDays} days', value: recent == null ? '—' : formatPercent(recent)),
        _Metric(
          label: 'Previous ${summary.trend.windowDays} days',
          value: previous == null ? '—' : formatPercent(previous),
        ),
      ],
    );
  }
}

class _AssignmentSummary extends StatelessWidget {
  const _AssignmentSummary({required this.overview, required this.now});

  final AssignmentOverview overview;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final counts = overview.countsAt(now);
    final next = overview.items.where((i) => i.stateAt(now) == AssignmentState.pending).firstOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _Metric(label: 'Due soon', value: '${counts[AssignmentState.pending]}'),
            _Metric(label: 'Overdue', value: '${counts[AssignmentState.overdue]}'),
            _Metric(label: 'Missing', value: '${counts[AssignmentState.missing]}'),
            _Metric(
              label: 'Submitted',
              value: '${counts[AssignmentState.submitted]! + counts[AssignmentState.late]!}',
            ),
          ],
        ),
        if (next != null) ...[
          const SizedBox(height: 12),
          Text('Next: ${next.assignment.title} (${next.assignment.courseCode}), due '
              '${formatDateTime(next.assignment.dueAt)}'),
        ],
        if (counts[AssignmentState.overdue]! > 0) ...[
          const SizedBox(height: 8),
          const AssignmentStateChip(state: AssignmentState.overdue),
        ],
      ],
    );
  }
}
