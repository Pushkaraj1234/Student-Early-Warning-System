/// Network errors that only exist on platforms with `dart:io` (see platform_network_error_io.dart).
///
/// In the browser there is no `dart:io`: a failed request surfaces as `http.ClientException`,
/// which [AppFailure] already maps to a network failure, so nothing extra is recognised here.
bool isPlatformNetworkError(Object error) => false;
