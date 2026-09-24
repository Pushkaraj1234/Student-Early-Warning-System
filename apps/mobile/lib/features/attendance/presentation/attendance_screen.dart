import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/attendance/domain/attendance_models.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';

class AttendanceScreen extends ConsumerWidget {
  const AttendanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('Attendance'), actions: const [ShellActions()]),
        body: AsyncValueView<AttendanceSummary?>(
          value: ref.watch(attendanceSummaryProvider),
          onRetry: () => ref.invalidate(attendanceSummaryProvider),
          isEmpty: (s) => s == null || s.isEmpty,
          emptyMessage: 'No attendance has been recorded for your current courses yet.',
          emptyIcon: Icons.event_busy_outlined,
          data: (s) => RefreshIndicator(
            onRefresh: () async => ref.invalidate(attendanceSummaryProvider),
            child: AttendanceContent(summary: s!),
          ),
        ),
      );
}

String _rateText(AttendanceRate rate) => rate.rate == null
    ? 'No sessions counted'
    : '${formatPercent(rate.rate!)} (${rate.attended} of ${rate.counted} sessions)';

class AttendanceContent extends StatelessWidget {
  const AttendanceContent({super.key, required this.summary});

  final AttendanceSummary summary;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final last = summary.lastRecordedOn;
    final trend = summary.trend;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Overall attendance, ${summary.academicYear}', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  summary.overall.rate == null ? '—' : formatPercent(summary.overall.rate!),
                  style: theme.textTheme.displaySmall,
                ),
                Text(_rateText(summary.overall)),
                if (summary.overall.excused > 0)
                  Text('${summary.overall.excused} excused sessions are not counted.',
                      style: theme.textTheme.bodySmall),
                if (last != null) Text('Last recorded on ${formatDate(last)}', style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Recent trend', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Text('Last ${trend.windowDays} days: ${_rateText(trend.recent)}'),
                Text('Previous ${trend.windowDays} days: ${_rateText(trend.previous)}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text('By subject', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final item in summary.perCourse)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${item.course.code} · ${item.course.title}', style: theme.textTheme.titleSmall),
                  const SizedBox(height: 6),
                  if (item.rate.rate != null)
                    LinearProgressIndicator(value: item.rate.rate, semanticsLabel: '${item.course.code} attendance'),
                  const SizedBox(height: 6),
                  Text(_rateText(item.rate)),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
