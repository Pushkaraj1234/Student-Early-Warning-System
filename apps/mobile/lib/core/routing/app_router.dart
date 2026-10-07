import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/routing/redirect.dart';
import 'package:sews_mobile/core/routing/routes.dart';
import 'package:sews_mobile/features/academics/presentation/academics_screen.dart';
import 'package:sews_mobile/features/admin/presentation/admin_screen.dart';
import 'package:sews_mobile/features/assignments/presentation/assignments_screen.dart';
import 'package:sews_mobile/features/attendance/presentation/attendance_screen.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';
import 'package:sews_mobile/features/auth/presentation/check_email_screen.dart';
import 'package:sews_mobile/features/auth/presentation/login_screen.dart';
import 'package:sews_mobile/features/auth/presentation/password_screens.dart';
import 'package:sews_mobile/features/auth/presentation/register_screen.dart';
import 'package:sews_mobile/features/auth/presentation/splash_screen.dart';
import 'package:sews_mobile/features/checkins/presentation/checkin_screen.dart';
import 'package:sews_mobile/features/dashboard/presentation/dashboard_screen.dart';
import 'package:sews_mobile/features/mentor/presentation/mentor_dashboard_screen.dart';
import 'package:sews_mobile/features/mentor/presentation/mentor_student_screen.dart';
import 'package:sews_mobile/features/notifications/presentation/notifications_screen.dart';
import 'package:sews_mobile/features/onboarding/presentation/onboarding_screen.dart';
import 'package:sews_mobile/features/profile/presentation/profile_screen.dart';
import 'package:sews_mobile/features/risk/presentation/risk_explanation_screen.dart';
import 'package:sews_mobile/features/shell/home_shell.dart';
import 'package:sews_mobile/features/shell/not_found_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  // Re-evaluate redirects whenever the auth state or the profile changes.
  final refresh = ValueNotifier<int>(0);
  ref
    ..listen(authControllerProvider, (_, _) => refresh.value++)
    ..listen(profileProvider, (_, _) => refresh.value++)
    ..listen(appVersionSupportedProvider, (_, _) => refresh.value++)
    ..onDispose(refresh.dispose);

  final router = GoRouter(
    initialLocation: Routes.splash,
    refreshListenable: refresh,
    redirect: (context, state) => resolveRedirect(
      auth: ref.read(authControllerProvider).status,
      profile: ref.read(profileProvider),
      location: state.matchedLocation,
      versionSupported: ref.read(appVersionSupportedProvider),
    ),
    errorBuilder: (_, _) => const NotFoundScreen(),
    routes: [
      // The top-level redirect moves every user on from the root (it is a gateway); this
      // route only makes the address valid.
      GoRoute(path: Routes.root, redirect: (_, _) => Routes.splash),
      GoRoute(path: Routes.splash, builder: (_, _) => const SplashScreen()),
      GoRoute(path: Routes.login, builder: (_, _) => const LoginScreen()),
      GoRoute(path: Routes.register, builder: (_, _) => const RegisterScreen()),
      GoRoute(
        path: Routes.checkEmail,
        builder: (_, state) => CheckEmailScreen(email: state.extra is String ? state.extra! as String : null),
      ),
      GoRoute(path: Routes.forgotPassword, builder: (_, _) => const ForgotPasswordScreen()),
      GoRoute(path: Routes.resetPassword, builder: (_, _) => const ResetPasswordScreen()),
      GoRoute(path: Routes.onboarding, builder: (_, _) => const OnboardingScreen()),
      GoRoute(path: Routes.unsupportedRole, builder: (_, _) => const UnsupportedRoleScreen()),
      GoRoute(path: Routes.notifications, builder: (_, _) => const NotificationsScreen()),
      GoRoute(path: Routes.profile, builder: (_, _) => const ProfileScreen()),
      GoRoute(path: Routes.checkin, builder: (_, _) => const CheckinScreen()),
      GoRoute(path: Routes.updateRequired, builder: (_, _) => const UpdateRequiredScreen()),
      GoRoute(
        path: Routes.mentorHome,
        builder: (_, _) => const MentorDashboardScreen(),
        routes: [
          GoRoute(
            path: 'students/:studentId',
            builder: (_, state) => MentorStudentScreen(studentId: state.pathParameters['studentId']!),
          ),
        ],
      ),
      GoRoute(path: Routes.adminHome, builder: (_, _) => const AdminScreen()),
      StatefulShellRoute.indexedStack(
        builder: (_, _, navigationShell) => HomeShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(
              path: Routes.home,
              builder: (_, _) => const DashboardScreen(),
              routes: [GoRoute(path: 'risk', builder: (_, _) => const RiskExplanationScreen())],
            ),
          ]),
          StatefulShellBranch(routes: [GoRoute(path: Routes.academics, builder: (_, _) => const AcademicsScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: Routes.attendance, builder: (_, _) => const AttendanceScreen())]),
          StatefulShellBranch(
            routes: [GoRoute(path: Routes.assignments, builder: (_, _) => const AssignmentsScreen())],
          ),
        ],
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});
