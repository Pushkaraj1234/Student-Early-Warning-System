import 'dart:io';

/// Socket and TLS failures raised by `dart:io` on Android, iOS and desktop.
bool isPlatformNetworkError(Object error) => error is SocketException || error is HandshakeException;
