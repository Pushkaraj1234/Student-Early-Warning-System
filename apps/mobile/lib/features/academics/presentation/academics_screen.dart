import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/academics/domain/academic_models.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';

class AcademicsScreen extends ConsumerWidget {
  const AcademicsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('Academics'), actions: const [ShellActions()]),
        body: AsyncValueView<AcademicOverview>(
          value: ref.watch(academicOverviewProvider),
          onRetry: () => ref.invalidate(academicOverviewProvider),
          isEmpty: (o) => o.isEmpty,
          emptyMessage: 'No courses or results have been recorded for you yet.',
          emptyIcon: Icons.school_outlined,
          data: (o) => RefreshIndicator(
            onRefresh: () async => ref.invalidate(academicOverviewProvider),
            child: AcademicsContent(overview: o),
          ),
        ),
      );
}

class AcademicsContent extends StatelessWidget {
  const AcademicsContent({super.key, required this.overview});

  final AcademicOverview overview;

  @override
  Widget build(BuildContext context) {
    final latest = overview.latestPublished;
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: ListTile(
            title: const Text('CGPA'),
            subtitle: Text(latest == null
                ? 'No published semester results yet'
                : 'As of ${latest.academicYear}, semester ${latest.semester}'),
            trailing: Text(
              latest?.cgpa == null ? '—' : formatNumber(latest!.cgpa!),
              style: theme.textTheme.headlineSmall,
            ),
          ),
        ),
        const SizedBox(height: 12),
        for (final group in overview.semesters) ...[
          _SemesterCard(group: group),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class _SemesterCard extends StatelessWidget {
  const _SemesterCard({required this.group});

  final SemesterGroup group;

  static String _result(ResultStatus s) => switch (s) {
        ResultStatus.pass => 'Pass',
        ResultStatus.fail => 'Fail',
        ResultStatus.pending => 'Result pending',
        ResultStatus.withheld => 'Result withheld',
      };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final record = group.record;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${group.academicYear} · Semester ${group.semester}', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              record == null
                  ? 'Semester result not published'
                  : [
                      if (record.sgpa != null) 'SGPA ${formatNumber(record.sgpa!)}',
                      if (record.cgpa != null) 'CGPA ${formatNumber(record.cgpa!)}',
                      'Credits ${formatNumber(record.creditsEarned)}/${formatNumber(record.creditsRegistered)}',
                      _result(record.resultStatus),
                    ].join(' · '),
              style: theme.textTheme.bodySmall,
            ),
            const Divider(height: 24),
            if (group.courses.isEmpty) const Text('No course details recorded for this semester.'),
            for (final course in group.courses)
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('${course.courseCode} · ${course.courseTitle}'),
                subtitle: Text('${formatNumber(course.credits)} credits'
                    '${course.status == EnrolmentStatus.withdrawn ? ' · Withdrawn' : ''}'),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(course.grade ?? (course.status == EnrolmentStatus.enrolled ? 'In progress' : '—'),
                        style: theme.textTheme.titleMedium),
                    if (course.marks != null) Text('${formatNumber(course.marks!)} marks'),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
