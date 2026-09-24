import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class RecommendationsRepository {
  RecommendationsRepository(this._client);

  final SupabaseClient _client;

  /// Open actions for the signed-in student (newest first), from the database function
  /// that never exposes staff notes.
  Future<List<RecommendedAction>> fetchOpenActions() => guard(() async {
        final rows = Json.rows(await _client.rpc<dynamic>('get_my_recommended_actions'));
        return rows.map(RecommendedAction.fromJson).toList();
      });

  /// The student's answer to an offer. The database checks that the action belongs to the
  /// caller and is still an open offer; nothing else can be changed from here.
  Future<void> respond(String actionId, {required bool accept, DeclineReason? reason}) => guard(() async {
        if (!accept && reason == null) throw const FormatException('A decline needs a reason');
        await _client.rpc<dynamic>('respond_to_intervention', params: {
          'p_intervention_id': actionId,
          'p_accept': accept,
          'p_decline_reason': accept ? null : reason!.dbValue,
        });
      });
}
