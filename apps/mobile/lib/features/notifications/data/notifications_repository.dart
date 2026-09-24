import 'package:sews_mobile/core/data/json.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/notifications/domain/app_notification.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class NotificationsRepository {
  NotificationsRepository(this._client, {this.limit = 50});

  final SupabaseClient _client;
  final int limit;

  /// The signed-in user's notifications (RLS: recipient only), newest first.
  Future<List<AppNotification>> fetchRecent(String userId) => guard(() async {
        final rows = Json.rows(
          await _client
              .from('notifications')
              .select(AppNotification.columns)
              .eq('recipient_id', userId)
              .order('created_at', ascending: false)
              .limit(limit),
        );
        return rows.map(AppNotification.fromJson).toList();
      });

  /// Marks one notification as read. Only `read_at` is writable; RLS limits the update
  /// to the recipient, so a notification that is not the caller's is never modified.
  Future<void> markRead(String notificationId, {DateTime? now}) => guard(() async {
        final updated = Json.rows(
          await _client
              .from('notifications')
              .update({'read_at': (now ?? DateTime.now()).toUtc().toIso8601String()})
              .eq('id', notificationId)
              .select('id'),
        );
        if (updated.length != 1) throw const AppFailure(FailureKind.forbidden);
      });
}
