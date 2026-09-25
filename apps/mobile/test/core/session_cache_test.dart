import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/core/supabase/supabase_providers.dart';
import 'package:sews_mobile/features/auth/application/auth_controller.dart';

import '../helpers/fake_backend.dart';
import '../helpers/v2_fixtures.dart';

const _mentorA = AuthSnapshot(AuthStatus.signedIn, userId: 'mentor-a', email: 'mentor.a@synthetic.example.com');
const _mentorB = AuthSnapshot(AuthStatus.signedIn, userId: 'mentor-b', email: 'mentor.b@synthetic.example.com');

class _SwitchableAuthController extends AuthController {
  @override
  AuthSnapshot build() => _mentorA;

  void switchTo(AuthSnapshot snapshot) => state = snapshot;
}

void main() {
  late FakeBackend backend;
  late ProviderContainer container;

  setUp(() {
    backend = FakeBackend();
    // Each account sees its own rows (RLS on the real server); the fake returns the caller's
    // rows in the order the accounts sign in.
    var caseloadCalls = 0;
    backend
      ..on('POST', rpcPath('get_mentor_caseload'), (_) {
        caseloadCalls++;
        return jsonResponse([caseloadRow(name: caseloadCalls == 1 ? 'Mentee of A' : 'Mentee of B')]);
      })
      ..onGet(rest('interventions'), [interventionRow()]);
    container = ProviderContainer(
      retry: (_, _) => null,
      overrides: [
        supabaseClientProvider.overrideWithValue(backend.client),
        authControllerProvider.overrideWith(_SwitchableAuthController.new),
      ],
    );
  });

  tearDown(() => container.dispose());

  _SwitchableAuthController auth() => container.read(authControllerProvider.notifier) as _SwitchableAuthController;

  test('another sign-in discards the previous mentor caseload instead of showing the cached one', () async {
    final first = await container.read(caseloadProvider.future);
    expect(first.single.fullName, 'Mentee of A');

    auth().switchTo(_mentorB);
    final second = await container.read(caseloadProvider.future);

    expect(second.single.fullName, 'Mentee of B');
    expect(backend.requestsTo(rpcPath('get_mentor_caseload')), hasLength(2));
  });

  test('intervention status is refetched for the next session', () async {
    await container.read(mentorInterventionsProvider.future);
    auth().switchTo(_mentorB);
    await container.read(mentorInterventionsProvider.future);

    expect(backend.requestsTo(rest('interventions')), hasLength(2));
  });

  test('staff data is not served after sign-out', () async {
    await container.read(caseloadProvider.future);
    auth().switchTo(const AuthSnapshot(AuthStatus.signedOut));

    final unauthenticated = isA<AppFailure>().having((f) => f.kind, 'kind', FailureKind.unauthenticated);
    await expectLater(container.read(caseloadProvider.future), throwsA(unauthenticated));
    await expectLater(container.read(mentorInterventionsProvider.future), throwsA(unauthenticated));
    await expectLater(container.read(adminOverviewProvider.future), throwsA(unauthenticated));
  });
}
