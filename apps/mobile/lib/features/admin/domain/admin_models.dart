import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';

enum ModelStatus {
  development('development', 'Development'),
  validated('validated', 'Validated'),
  staging('staging', 'Staging'),
  production('production', 'Production'),
  retired('retired', 'Retired');

  const ModelStatus(this.dbValue, this.label);

  final String dbValue;
  final String label;

  /// Only production models may score students outside development databases.
  bool get mayScoreLiveStudents => this == production;
}

/// A row of `public.model_registry` (RLS: admins of the model's institution; global models).
class RegisteredModel {
  const RegisteredModel({
    required this.id,
    required this.version,
    required this.modelName,
    required this.target,
    required this.status,
    required this.provenance,
    required this.featureVersion,
    required this.trainingTimestamp,
    this.institutionId,
  });

  factory RegisteredModel.fromJson(Map<String, dynamic> json) => RegisteredModel(
        id: Json.string(json, 'id'),
        version: Json.string(json, 'version'),
        modelName: Json.string(json, 'model_name'),
        target: Json.string(json, 'target'),
        status: Json.enumValue(json, 'status', {for (final s in ModelStatus.values) s.dbValue: s}),
        provenance: Json.enumValue(json, 'data_provenance', {for (final p in DataProvenance.values) p.name: p}),
        featureVersion: Json.string(json, 'feature_version'),
        trainingTimestamp: Json.dateTime(json, 'training_timestamp'),
        institutionId: Json.stringOrNull(json, 'institution_id'),
      );

  static const String columns =
      'id, version, model_name, target, status, data_provenance, feature_version, training_timestamp, institution_id';

  final String id;
  final String version;
  final String modelName;
  final String target;
  final ModelStatus status;
  final DataProvenance provenance;
  final String featureVersion;
  final DateTime trainingTimestamp;
  final String? institutionId;
}

enum AlertSeverity { warning, critical }

/// A row of `public.drift_alerts`: aggregate statistics only, never student data.
class DriftAlert {
  const DriftAlert({
    required this.id,
    required this.modelRegistryId,
    required this.alertType,
    required this.subject,
    required this.statistic,
    required this.value,
    required this.threshold,
    required this.severity,
    required this.status,
    required this.createdAt,
  });

  factory DriftAlert.fromJson(Map<String, dynamic> json) => DriftAlert(
        id: Json.string(json, 'id'),
        modelRegistryId: Json.string(json, 'model_registry_id'),
        alertType: Json.string(json, 'alert_type'),
        subject: Json.string(json, 'subject'),
        statistic: Json.string(json, 'statistic'),
        value: Json.number(json, 'value'),
        threshold: Json.number(json, 'threshold'),
        severity: Json.enumValue(json, 'severity', {for (final s in AlertSeverity.values) s.name: s}),
        status: Json.string(json, 'status'),
        createdAt: Json.dateTime(json, 'created_at'),
      );

  static const String columns =
      'id, model_registry_id, alert_type, subject, statistic, value, threshold, severity, status, created_at';

  final String id;
  final String modelRegistryId;
  final String alertType;
  final String subject;
  final String statistic;
  final num value;
  final num threshold;
  final AlertSeverity severity;
  final String status;
  final DateTime createdAt;

  bool get isOpen => status == 'open';
}

/// A row of `public.model_monitoring_snapshots` (counts only are shown in the app).
class MonitoringSnapshot {
  const MonitoringSnapshot({
    required this.modelRegistryId,
    required this.windowStart,
    required this.windowEnd,
    required this.predictions,
    required this.labelsAvailable,
  });

  factory MonitoringSnapshot.fromJson(Map<String, dynamic> json) {
    final predictions = Json.integer(json, 'n_predictions');
    final labels = Json.integer(json, 'labels_available');
    if (predictions < 0 || labels < 0) throw const FormatException('Negative monitoring counts');
    return MonitoringSnapshot(
      modelRegistryId: Json.string(json, 'model_registry_id'),
      windowStart: Json.date(json, 'window_start'),
      windowEnd: Json.date(json, 'window_end'),
      predictions: predictions,
      labelsAvailable: labels,
    );
  }

  static const String columns = 'model_registry_id, window_start, window_end, n_predictions, labels_available';

  final String modelRegistryId;
  final DateTime windowStart;
  final DateTime windowEnd;
  final int predictions;
  final int labelsAvailable;
}

class AdminOverview {
  const AdminOverview({required this.models, required this.openAlerts, required this.snapshots});

  final List<RegisteredModel> models;
  final List<DriftAlert> openAlerts;
  final List<MonitoringSnapshot> snapshots;
}
