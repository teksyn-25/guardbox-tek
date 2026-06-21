import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:guardbox/screens/setup_screen.dart';
import 'package:guardbox/theme.dart';

// flutter_secure_storage uses a native method channel. In widget tests there
// is no native code, so any call to the channel throws MissingPluginException.
// setup_screen never calls secure storage methods directly, but importing
// config.dart brings FlutterSecureStorage into scope. This mock handler
// silences the channel so tests do not fail if the plugin initialises eagerly.
const _secureChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

Widget _app() => MaterialApp(
      theme: guardBoxTheme(),
      home: const SetupScreen(),
      routes: {
        '/login': (_) => const Scaffold(body: Text('login-screen')),
      },
    );

void main() {
  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, (_) async => null);
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, null);
  });

  // ── Validation ────────────────────────────────────────────────────────────

  group('URL validation', () {
    testWidgets('shows Required error when URL is empty', (tester) async {
      await tester.pumpWidget(_app());
      await tester.tap(find.text('Continue'));
      await tester.pump();
      expect(find.text('Required'), findsOneWidget);
    });

    testWidgets('shows error when URL has no scheme', (tester) async {
      await tester.pumpWidget(_app());
      await tester.enterText(
          find.byType(TextFormField), 'guardbox.example.com');
      await tester.tap(find.text('Continue'));
      await tester.pump();
      expect(find.text('Enter a valid URL'), findsOneWidget);
    });

    testWidgets('blocks http:// — HTTPS enforcement', (tester) async {
      await tester.pumpWidget(_app());
      await tester.enterText(
          find.byType(TextFormField), 'http://guardbox.example.com');
      await tester.tap(find.text('Continue'));
      await tester.pump();
      expect(
        find.text('HTTPS required — plaintext HTTP is not allowed'),
        findsOneWidget,
      );
    });

    testWidgets('blocks http:// with path', (tester) async {
      await tester.pumpWidget(_app());
      await tester.enterText(
          find.byType(TextFormField), 'http://guardbox.example.com/api');
      await tester.tap(find.text('Continue'));
      await tester.pump();
      expect(
        find.text('HTTPS required — plaintext HTTP is not allowed'),
        findsOneWidget,
      );
    });

    testWidgets('accepts valid https:// URL and navigates to login',
        (tester) async {
      await tester.pumpWidget(_app());
      await tester.enterText(
          find.byType(TextFormField), 'https://guardbox.example.com');
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
      expect(find.text('login-screen'), findsOneWidget);
    });

    testWidgets('accepts https:// with port', (tester) async {
      await tester.pumpWidget(_app());
      await tester.enterText(
          find.byType(TextFormField), 'https://guardbox.example.com:8443');
      await tester.tap(find.text('Continue'));
      await tester.pumpAndSettle();
      expect(find.text('login-screen'), findsOneWidget);
    });
  });

  // ── UI structure ──────────────────────────────────────────────────────────

  group('UI', () {
    testWidgets('renders GuardBox title', (tester) async {
      await tester.pumpWidget(_app());
      expect(find.text('GuardBox'), findsOneWidget);
    });

    testWidgets('renders Continue button', (tester) async {
      await tester.pumpWidget(_app());
      expect(find.text('Continue'), findsOneWidget);
    });

    testWidgets('renders server URL input field', (tester) async {
      await tester.pumpWidget(_app());
      expect(find.byType(TextFormField), findsOneWidget);
    });

    testWidgets('shows loading indicator while saving', (tester) async {
      await tester.pumpWidget(_app());
      await tester.enterText(
          find.byType(TextFormField), 'https://guardbox.example.com');
      await tester.tap(find.text('Continue'));
      // pump one frame — saving state is set before async completes
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}
