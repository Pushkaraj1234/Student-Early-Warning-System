import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/app.dart';
import 'package:sews_mobile/core/config/app_config.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final AppConfig config;
  try {
    config = AppConfig.fromEnvironment();
  } on ConfigException catch (error) {
    runApp(ConfigErrorApp(message: error.message));
    return;
  }

  // Restores any persisted session before the first frame; the auth controller then
  // receives it as the initial auth event (session restoration).
  await Supabase.initialize(
    url: config.supabaseUrl,
    publishableKey: config.publishableKey,
    authOptions: const FlutterAuthClientOptions(authFlowType: AuthFlowType.pkce),
  );

  runApp(
    ProviderScope(
      // Failed loads show an error with a Retry button instead of retrying silently.
      retry: (_, _) => null,
      overrides: [supabaseClientProvider.overrideWithValue(Supabase.instance.client)],
      child: const SewsApp(),
    ),
  );
}
