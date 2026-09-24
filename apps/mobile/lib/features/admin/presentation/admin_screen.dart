import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/section_card.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/admin/domain/admin_models.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';

/// Administrator view: registered models and their lifecycle status, open drift alerts
/// (aggregate statistics only) and recent monitoring windows.
class AdminScreen extends ConsumerWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(notificationsRealtimeProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Model monitoring'), actions: const [ShellActions()]),
      body: AsyncValueView<AdminOverview>(
        value: ref.watch(adminOverviewProvider),
        onRetry: () => ref.invalidate(adminOverviewProvider),
        isEmpty: (o) => o.models.isEmpty,
        emptyMessage: 'No models are registered yet.',
        emptyIcon: Icons.model_training,
        data: (o) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(adminOverviewProvider),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              SectionCard(
                title: 'Registered models',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Only models in Production may score students. Production requires institutional '
                      'training data, calibration evaluation and a recorded approval.',
                    ),
                    for (final m in o.models) _ModelTile(model: m),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: 'Open drift alerts (${o.openAlerts.length})',
                child: o.openAlerts.isEmpty
                    ? const EmptyView(message: 'No open alerts.', icon: Icons.check_circle_outline, compact: true)
                    : Column(children: [for (final a in o.openAlerts) _AlertTile(alert: a, models: o.models)]),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: 'Monitoring windows',
                child: o.snapshots.isEmpty
                    ? const EmptyView(message: 'No monitoring windows yet.', icon: Icons.timeline, compact: true)
                    : Column(
                        children: [
                          for (final s in o.snapshots.take(10))
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              dense: true,
                              title: Text('${formatDate(s.windowStart)} – ${formatDate(s.windowEnd)}'),
                              subtitle: Text(
                                '${_versionOf(o.models, s.modelRegistryId)} · ${s.predictions} predictions · '
                                '${s.labelsAvailable} outcomes known',
                              ),
                            ),
                        ],
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _versionOf(List<RegisteredModel> models, String id) =>
    models.where((m) => m.id == id).firstOrNull?.version ?? 'unknown model';

class _ModelTile extends StatelessWidget {
  const _ModelTile({required this.model});

  final RegisteredModel model;

  @override
  Widget build(BuildContext context) => ListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(model.version),
        subtitle: Text(
          '${model.target} · ${model.modelName} · ${model.featureVersion}\n'
          'Trained ${formatDate(model.trainingTimestamp)} on ${model.provenance.name} data'
          '${model.institutionId == null ? ' · all institutions' : ''}',
        ),
        isThreeLine: true,
        trailing: Chip(
          label: Text(model.status.label),
          avatar: Icon(
            model.status.mayScoreLiveStudents ? Icons.verified_outlined : Icons.science_outlined,
            size: 18,
          ),
        ),
      );
}

class _AlertTile extends ConsumerWidget {
  const _AlertTile({required this.alert, required this.models});

  final DriftAlert alert;
  final List<RegisteredModel> models;

  Future<void> _acknowledge(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(adminRepositoryProvider).acknowledge(alert.id);
      ref.invalidate(adminOverviewProvider);
    } on AppFailure catch (failure) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(failure.message)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final critical = alert.severity == AlertSeverity.critical;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(
        critical ? Icons.error_outline : Icons.warning_amber_outlined,
        color: critical ? Theme.of(context).colorScheme.error : null,
      ),
      title: Text('${alert.alertType.replaceAll('_', ' ')}: ${alert.subject}'),
      subtitle: Text(
        '${alert.statistic} ${formatNumber(alert.value, maxDecimals: 3)} '
        '(threshold ${formatNumber(alert.threshold, maxDecimals: 2)}) · ${_versionOf(models, alert.modelRegistryId)}'
        ' · ${formatDate(alert.createdAt)}',
      ),
      isThreeLine: true,
      trailing: TextButton(onPressed: () => _acknowledge(context, ref), child: const Text('Acknowledge')),
    );
  }
}

/// Shown when the database reports that this build is older than the minimum supported version.
class UpdateRequiredScreen extends ConsumerWidget {
  const UpdateRequiredScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        body: SafeArea(
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const EmptyView(
                  message: 'This version of SEWS is no longer supported. Please install the latest version to continue.',
                  icon: Icons.system_update,
                ),
                TextButton(
                  onPressed: () => ref.read(authRepositoryProvider).signOut(),
                  child: const Text('Sign out'),
                ),
              ],
            ),
          ),
        ),
      );
}
