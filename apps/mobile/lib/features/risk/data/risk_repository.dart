import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class RiskRepository {
  RiskRepository(this._client, {this.historyLimit = 8});

  final SupabaseClient _client;
  final int historyLimit;

  /// Latest ACADEMIC-risk predictions (newest first) and the stored factors of the newest one.
  /// Other targets (e.g. engagement) are separate models and never mixed into this history.
  /// Factors are exactly what the scoring job saved — nothing is generated in the app.
  Future<RiskOverview> fetchOverview(String studentId) => guard(() async {
        final history = Json.rows(
          await _client
              .from('risk_predictions')
              .select(RiskPrediction.columns)
              .eq('student_id', studentId)
              .eq('target', 'academic')
              .order('prediction_date', ascending: false)
              .order('created_at', ascending: false)
              .limit(historyLimit),
        ).map(RiskPrediction.fromJson).toList();
        if (history.isEmpty) return const RiskOverview(history: [], latestFactors: []);
        final factors = Json.rows(
          await _client
              .from('risk_factors')
              .select(RiskFactor.columns)
              .eq('prediction_id', history.first.id)
              .order('rank', ascending: true),
        ).map(RiskFactor.fromJson).toList();
        return RiskOverview(history: history, latestFactors: factors);
      });
}
