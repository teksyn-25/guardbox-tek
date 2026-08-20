import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:guardbox/main.dart';

// The real device symptom this reproduces: app opens to a spinner that
// never resolves to anything. Root cause — _StartupRouter's FutureBuilder
// only checks snapshot.hasData, never snapshot.hasError. If reading stored
// credentials throws (e.g. flutter_secure_storage's Android Keystore read
// failing on a specific device), the Future completes with an error, hasData
// never becomes true, and the spinner never goes away — no error shown,
// nothing actionable for the user.
const _secureChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

void main() {
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, null);
  });

  testWidgets(
      'falls back to setup instead of hanging forever when secure storage read throws',
      (tester) async {
    // A server URL is already stored, so _resolve() proceeds to read the
    // token next — that's the read that throws.
    SharedPreferences.setMockInitialValues(
        {'server_url': 'https://guardbox.example.com'});
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, (call) async {
      if (call.method == 'read') {
        throw PlatformException(code: 'Keystore', message: 'read failed');
      }
      return null;
    });

    await tester.pumpWidget(const GuardBoxApp());
    await tester.pumpAndSettle();

    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.text('Server URL'), findsOneWidget);
  });
}
