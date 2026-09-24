import 'package:sews_mobile/core/data/json.dart';

/// Risk levels decided server-side by the model's stored thresholds. The app never
/// computes a level from a probability.
enum RiskLevel {
  stable('Stable'),
  watch('Watch'),
  elevated('Elevated'),
  high('High');

  const RiskLevel(this.label);

  final String label;
}

enum DataProvenance { benchmark, synthetic, institutional }

/// Change since the previous prediction of the same model and target, classified by the
/// database (thresholds in docs/ml/risk-trajectory.md). Students see plain, non-alarming
/// wording; staff see the exact classification.
enum Trajectory {
  insufficientHistory('insufficient_history', 'Not enough history yet', 'Not enough history'),
  improving('improving', 'Improving', 'Improving'),
  stable('stable', 'Steady', 'Stable'),
  increasing('increasing', 'Worth a look', 'Increasing'),
  rapidlyIncreasing('rapidly_increasing', 'Worth a look soon', 'Rapidly increasing');

  const Trajectory(this.dbValue, this.studentLabel, this.staffLabel);

  final String dbValue;
  final String studentLabel;
  final String staffLabel;

  bool get isRising => this == increasing || this == rapidlyIncreasing;

  static Trajectory parse(Map<String, dynamic> json, String key) =>
      Json.enumValue(json, key, {for (final t in Trajectory.values) t.dbValue: t});
}

enum FactorDirection {
  increasesRisk('increases_risk'),
  decreasesRisk('decreases_risk');

  const FactorDirection(this.dbValue);

  final String dbValue;
}

class RiskPrediction {
  const RiskPrediction({
    required this.id,
    required this.predictionDate,
    required this.level,
    required this.modelVersion,
    required this.provenance,
    required this.createdAt,
    this.trajectory = Trajectory.insufficientHistory,
  });

  factory RiskPrediction.fromJson(Map<String, dynamic> json) {
    final probability = Json.number(json, 'risk_probability');
    if (probability < 0 || probability > 1) throw const FormatException('risk_probability out of range');
    return RiskPrediction(
      id: Json.string(json, 'id'),
      predictionDate: Json.date(json, 'prediction_date'),
      level: Json.enumValue(json, 'risk_level', {for (final l in RiskLevel.values) l.name: l}),
      modelVersion: Json.string(json, 'model_version'),
      provenance: Json.enumValue(json, 'data_provenance', {for (final p in DataProvenance.values) p.name: p}),
      createdAt: Json.dateTime(json, 'created_at'),
      trajectory: Trajectory.parse(json, 'trajectory'),
    );
  }

  /// risk_probability is read only to validate the row; students are shown the level,
  /// not a raw probability (docs/ml/ml-strategy.md §6).
  static const String columns =
      'id, prediction_date, risk_probability, risk_level, model_version, data_provenance, created_at, trajectory';

  final String id;
  final DateTime predictionDate;
  final RiskLevel level;
  final String modelVersion;
  final DataProvenance provenance;
  final DateTime createdAt;
  final Trajectory trajectory;
}

class RiskFactor {
  const RiskFactor({
    required this.rank,
    required this.feature,
    required this.contribution,
    required this.direction,
    this.featureValue,
  });

  factory RiskFactor.fromJson(Map<String, dynamic> json) {
    final rank = Json.integer(json, 'rank');
    final contribution = Json.number(json, 'contribution');
    final direction = Json.enumValue(
      json,
      'direction',
      {for (final d in FactorDirection.values) d.dbValue: d},
    );
    final consistent = direction == FactorDirection.increasesRisk ? contribution >= 0 : contribution <= 0;
    if (rank < 1 || !consistent) throw const FormatException('Inconsistent risk factor');
    return RiskFactor(
      rank: rank,
      feature: Json.string(json, 'feature'),
      featureValue: Json.numberOrNull(json, 'feature_value'),
      contribution: contribution,
      direction: direction,
    );
  }

  static const String columns = 'rank, feature, feature_value, contribution, direction';

  final int rank;
  final String feature;
  final num? featureValue;
  final num contribution;
  final FactorDirection direction;
}

class RiskOverview {
  const RiskOverview({required this.history, required this.latestFactors});

  /// Newest first.
  final List<RiskPrediction> history;
  final List<RiskFactor> latestFactors;

  RiskPrediction? get latest => history.isEmpty ? null : history.first;

  bool get hasPrediction => history.isNotEmpty;

  /// Oldest to newest, for trend display. Needs at least two predictions.
  List<RiskPrediction> get trend => history.reversed.toList();
}
