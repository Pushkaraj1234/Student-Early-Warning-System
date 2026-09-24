import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/admin/domain/admin_models.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Model-governance data for administrators. RLS limits every table to admins; the app
/// only reads, plus acknowledging a drift alert through its database function.
class AdminRepository {
  AdminRepository(this._client, {this.limit = 50});

  final SupabaseClient _client;
  final int limit;

  Future<AdminOverview> fetchOverview() => guard(() async {
        final models = Json.rows(
          await _client
              .from('model_registry')
              .select(RegisteredModel.columns)
              .order('training_timestamp', ascending: false)
              .limit(limit),
        ).map(RegisteredModel.fromJson).toList();
        final alerts = Json.rows(
          await _client
              .from('drift_alerts')
              .select(DriftAlert.columns)
              .eq('status', 'open')
              .order('created_at', ascending: false)
              .limit(limit),
        ).map(DriftAlert.fromJson).toList();
        final snapshots = Json.rows(
          await _client
              .from('model_monitoring_snapshots')
              .select(MonitoringSnapshot.columns)
              .order('window_end', ascending: false)
              .limit(limit),
        ).map(MonitoringSnapshot.fromJson).toList();
        return AdminOverview(models: models, openAlerts: alerts, snapshots: snapshots);
      });

  Future<void> acknowledge(String alertId) =>
      guard(() => _client.rpc<dynamic>('acknowledge_drift_alert', params: {'p_alert_id': alertId}));
}
