import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/academics/data/academics_repository.dart';
import 'package:sews_mobile/features/academics/domain/academic_models.dart';
import 'package:sews_mobile/features/admin/data/admin_repository.dart';
import 'package:sews_mobile/features/admin/domain/admin_models.dart';
import 'package:sews_mobile/features/assignments/data/assignments_repository.dart';
import 'package:sews_mobile/features/assignments/domain/assignment_models.dart';
import 'package:sews_mobile/features/attendance/data/attendance_repository.dart';
import 'package:sews_mobile/features/attendance/domain/attendance_models.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/checkins/data/checkins_repository.dart';
import 'package:sews_mobile/features/mentor/data/mentor_repository.dart';
import 'package:sews_mobile/features/mentor/domain/mentor_models.dart';
import 'package:sews_mobile/features/notifications/data/notifications_repository.dart';
import 'package:sews_mobile/features/notifications/domain/app_notification.dart';
import 'package:sews_mobile/features/recommendations/data/recommendations_repository.dart';
import 'package:sews_mobile/features/recommendations/domain/recommended_action.dart';
import 'package:sews_mobile/features/risk/data/risk_repository.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Current time; overridden in tests.
final clockProvider = Provider<DateTime Function()>((ref) => DateTime.now);

final academicsRepositoryProvider =
    Provider<AcademicsRepository>((ref) => AcademicsRepository(ref.watch(supabaseClientProvider)));
final attendanceRepositoryProvider =
    Provider<AttendanceRepository>((ref) => AttendanceRepository(ref.watch(supabaseClientProvider)));
final assignmentsRepositoryProvider =
    Provider<AssignmentsRepository>((ref) => AssignmentsRepository(ref.watch(supabaseClientProvider)));
final riskRepositoryProvider = Provider<RiskRepository>((ref) => RiskRepository(ref.watch(supabaseClientProvider)));
final recommendationsRepositoryProvider =
    Provider<RecommendationsRepository>((ref) => RecommendationsRepository(ref.watch(supabaseClientProvider)));
final notificationsRepositoryProvider =
    Provider<NotificationsRepository>((ref) => NotificationsRepository(ref.watch(supabaseClientProvider)));
final checkinsRepositoryProvider =
    Provider<CheckinsRepository>((ref) => CheckinsRepository(ref.watch(supabaseClientProvider)));
final mentorRepositoryProvider = Provider<MentorRepository>((ref) => MentorRepository(ref.watch(supabaseClientProvider)));
final adminRepositoryProvider = Provider<AdminRepository>((ref) => AdminRepository(ref.watch(supabaseClientProvider)));

final academicOverviewProvider = FutureProvider<AcademicOverview>((ref) async {
  final studentId = await ref.watch(currentStudentIdProvider.future);
  return ref.watch(academicsRepositoryProvider).fetchOverview(studentId);
});

final attendanceSummaryProvider = FutureProvider<AttendanceSummary?>((ref) async {
  final studentId = await ref.watch(currentStudentIdProvider.future);
  final data = await ref.watch(attendanceRepositoryProvider).fetchCurrentYear(studentId);
  final year = data.academicYear;
  if (year == null) return null;
  return AttendanceSummary.compute(
    academicYear: year,
    courses: data.courses,
    records: data.records,
    today: ref.read(clockProvider)(),
  );
});

final assignmentOverviewProvider = FutureProvider<AssignmentOverview>((ref) async {
  final studentId = await ref.watch(currentStudentIdProvider.future);
  final (assignments, submissions) = await ref.watch(assignmentsRepositoryProvider).fetch(studentId);
  return AssignmentOverview.build(assignments, submissions, ref.read(clockProvider)());
});

final riskOverviewProvider = FutureProvider<RiskOverview>((ref) async {
  final studentId = await ref.watch(currentStudentIdProvider.future);
  return ref.watch(riskRepositoryProvider).fetchOverview(studentId);
});

final recommendedActionsProvider = FutureProvider<List<RecommendedAction>>((ref) async {
  // Depends on the linked student so that it refreshes with the account.
  await ref.watch(currentStudentIdProvider.future);
  return ref.watch(recommendationsRepositoryProvider).fetchOpenActions();
});

final notificationsProvider = FutureProvider<List<AppNotification>>((ref) async {
  final userId = ref.watch(currentUserIdProvider);
  if (userId == null) return const [];
  return ref.watch(notificationsRepositoryProvider).fetchRecent(userId);
});

final unreadNotificationCountProvider = Provider<int>(
  (ref) => ref.watch(notificationsProvider).value?.where((n) => !n.isRead).length ?? 0,
);

// ------------------------------------------------------------------ realtime

/// Realtime is on in the app; widget tests switch it off (no socket in tests).
final realtimeEnabledProvider = Provider<bool>((ref) => true);

/// Listens for new notifications addressed to the signed-in user and refreshes the list.
/// Realtime applies the notifications table's RLS, so only the caller's own rows are sent;
/// the filter keeps the subscription narrow. Push previews stay generic (database rule).
final notificationsRealtimeProvider = Provider<void>((ref) {
  if (!ref.watch(realtimeEnabledProvider)) return;
  final userId = ref.watch(currentUserIdProvider);
  if (userId == null) return;
  final client = ref.watch(supabaseClientProvider);
  final channel = client
      .channel('notifications:$userId')
      .onPostgresChanges(
        event: PostgresChangeEvent.insert,
        schema: 'public',
        table: 'notifications',
        filter: PostgresChangeFilter(type: PostgresChangeFilterType.eq, column: 'recipient_id', value: userId),
        callback: (_) => ref.invalidate(notificationsProvider),
      )
      .subscribe();
  ref.onDispose(() => client.removeChannel(channel));
});

// ------------------------------------------------------------------ mentor

final caseloadProvider = FutureProvider<List<CaseloadEntry>>(
  (ref) => ref.watch(mentorRepositoryProvider).fetchCaseload(),
);

final mentorInterventionsProvider = FutureProvider<List<StaffIntervention>>(
  (ref) => ref.watch(mentorRepositoryProvider).fetchInterventions(),
);

/// One mentee: only students in the caller's caseload can be opened (RLS decides the caseload).
final menteeDetailProvider = FutureProvider.family<MenteeDetail, String>((ref, studentId) async {
  final caseload = await ref.watch(caseloadProvider.future);
  final entry = caseload.where((e) => e.studentId == studentId).firstOrNull;
  if (entry == null) throw const AppFailure(FailureKind.forbidden);
  final mentor = ref.watch(mentorRepositoryProvider);
  final results = await (
    ref.watch(riskRepositoryProvider).fetchOverview(studentId),
    mentor.fetchTrends(studentId),
    mentor.fetchInterventions(studentId: studentId),
  ).wait;
  return MenteeDetail(entry: entry, risk: results.$1, trends: results.$2, interventions: results.$3);
});

// ------------------------------------------------------------------ admin

final adminOverviewProvider = FutureProvider<AdminOverview>(
  (ref) => ref.watch(adminRepositoryProvider).fetchOverview(),
);
