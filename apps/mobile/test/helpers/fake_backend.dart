import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

typedef Responder = http.Response Function(http.Request request);

/// An in-memory stand-in for the Supabase HTTP APIs (Auth + PostgREST). Requests are
/// recorded so tests can assert exactly what the app asked for.
class FakeBackend {
  FakeBackend() {
    client = SupabaseClient(
      'https://fake-project.supabase.co',
      'sb_publishable_test_key',
      httpClient: MockClient(_handle),
      authOptions: AuthClientOptions(autoRefreshToken: false, pkceAsyncStorage: _MemoryStorage()),
    );
  }

  late final SupabaseClient client;
  final List<http.Request> requests = [];
  final List<(String, String, Responder)> _routes = [];

  /// When set, every request fails with this error (simulates being offline).
  Exception? networkError;

  /// Later registrations take precedence over earlier ones for the same method + path.
  void on(String method, String path, Responder respond) => _routes.add((method, path, respond));

  void onGet(String path, Object? body) => on('GET', path, (_) => jsonResponse(body));

  Iterable<http.Request> requestsTo(String path) => requests.where((r) => r.url.path == path);

  Future<http.Response> _handle(http.Request request) async {
    requests.add(request);
    final error = networkError;
    if (error != null) throw error;
    for (final (method, path, respond) in _routes.reversed) {
      if (request.method == method && request.url.path == path) return _attach(respond(request), request);
    }
    return _attach(
      jsonResponse({'message': 'no fake route for ${request.method} ${request.url.path}'}, status: 404),
      request,
    );
  }

  /// Real HTTP responses carry their request; the Supabase clients rely on it.
  static http.Response _attach(http.Response response, http.Request request) =>
      http.Response.bytes(response.bodyBytes, response.statusCode, headers: response.headers, request: request);
}

class _MemoryStorage extends GotrueAsyncStorage {
  final Map<String, String> _values = {};

  @override
  Future<String?> getItem({required String key}) async => _values[key];

  @override
  Future<void> setItem({required String key, required String value}) async => _values[key] = value;

  @override
  Future<void> removeItem({required String key}) async => _values.remove(key);
}

http.Response jsonResponse(Object? body, {int status = 200}) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json; charset=utf-8'});

String rest(String table) => '/rest/v1/$table';

String rpcPath(String function) => '/rest/v1/rpc/$function';

const String tokenPath = '/auth/v1/token';
const String signupPath = '/auth/v1/signup';
const String logoutPath = '/auth/v1/logout';

String _b64(Map<String, Object> json) => base64Url.encode(utf8.encode(jsonEncode(json))).replaceAll('=', '');

String fakeJwt(String sub) {
  final exp = DateTime.now().add(const Duration(hours: 1)).millisecondsSinceEpoch ~/ 1000;
  return '${_b64({'alg': 'HS256', 'typ': 'JWT'})}.${_b64({'sub': sub, 'role': 'authenticated', 'exp': exp})}.sig';
}

Map<String, dynamic> userJson(String id, String email, {bool confirmed = true}) => {
      'id': id,
      'aud': 'authenticated',
      'role': 'authenticated',
      'email': email,
      'app_metadata': {'provider': 'email'},
      'user_metadata': <String, dynamic>{},
      'created_at': '2026-09-01T00:00:00Z',
      if (confirmed) 'email_confirmed_at': '2026-09-01T00:00:00Z',
    };

Map<String, dynamic> sessionJson(String userId, String email) => {
      'access_token': fakeJwt(userId),
      'token_type': 'bearer',
      'expires_in': 3600,
      'expires_at': DateTime.now().add(const Duration(hours: 1)).millisecondsSinceEpoch ~/ 1000,
      'refresh_token': 'refresh-token',
      'user': userJson(userId, email),
    };

http.Response authError(String code, {int status = 400}) =>
    jsonResponse({'error_code': code, 'msg': 'error $code'}, status: status);

http.Response postgrestError(String code, String message, {int status = 400}) =>
    jsonResponse({'code': code, 'message': message, 'details': null, 'hint': null}, status: status);
