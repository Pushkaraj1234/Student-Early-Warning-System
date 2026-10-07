abstract final class Routes {
  /// The site root on the web (where auth links return); always moved on from.
  static const String root = '/';
  static const String splash = '/splash';
  static const String login = '/login';
  static const String register = '/register';
  static const String checkEmail = '/check-email';
  static const String forgotPassword = '/forgot-password';
  static const String resetPassword = '/reset-password';
  static const String onboarding = '/onboarding';
  static const String unsupportedRole = '/unsupported';
  static const String home = '/home';
  static const String risk = '/home/risk';
  static const String academics = '/academics';
  static const String attendance = '/attendance';
  static const String assignments = '/assignments';
  static const String notifications = '/notifications';
  static const String profile = '/profile';
  static const String checkin = '/checkin';
  static const String updateRequired = '/update-required';

  // Staff
  static const String mentorHome = '/mentor';
  static const String mentorStudentPrefix = '/mentor/students';
  static String mentorStudent(String studentId) => '$mentorStudentPrefix/$studentId';
  static const String adminHome = '/admin';

  /// Routes shared by every signed-in role.
  static const Set<String> shared = {notifications, profile};

  /// Reachable while signed out.
  static const Set<String> public = {login, register, checkEmail, forgotPassword};

  /// Entry/transition screens a signed-in, onboarded student is moved away from.
  static const Set<String> gateways = {
    ...public,
    root,
    splash,
    onboarding,
    unsupportedRole,
    resetPassword,
    updateRequired,
  };
}
