import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// The Supabase client. Overridden in `main.dart` (and with a fake HTTP client in
/// tests). It only ever holds the publishable key: all authorization happens in
/// Postgres Row Level Security.
final supabaseClientProvider = Provider<SupabaseClient>(
  (ref) => throw StateError('supabaseClientProvider must be overridden at startup'),
);
