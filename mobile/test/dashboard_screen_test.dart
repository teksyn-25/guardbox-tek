import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:guardbox/screens/dashboard_screen.dart';
import 'package:guardbox/services/api_client.dart';
import 'package:guardbox/theme.dart';

// ── mocks ─────────────────────────────────────────────────────────────────────

class _MockApiClient extends Mock implements ApiClient {}

// ── method channel mocks ──────────────────────────────────────────────────────

const _secureChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
const _filePickerChannel = MethodChannel('miguelruivo.flutter.plugins.filepicker');

final _tinyBytes = Uint8List.fromList([137, 80, 78, 71, 1, 2, 3, 4]);

void _stubFilePicker({bool cancel = false}) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_filePickerChannel, (call) async {
    if (call.method == 'pickFiles') {
      if (cancel) return null;
      return {
        'files': [
          {
            'name': 'test.png',
            'size': _tinyBytes.length,
            'bytes': _tinyBytes,
            'path': null,
          }
        ],
      };
    }
    return null;
  });
}

// ── helpers ───────────────────────────────────────────────────────────────────

Widget _app(ApiClient api) => MaterialApp(
      theme: guardBoxTheme(),
      home: DashboardScreen.testable(api: api),
      scaffoldMessengerKey: GlobalKey<ScaffoldMessengerState>(),
    );

void main() {
  late _MockApiClient mockApi;

  setUpAll(() {
    registerFallbackValue(Uint8List(0));
  });

  setUp(() {
    mockApi = _MockApiClient();

    // silence native channel (config.dart imports FlutterSecureStorage at module level)
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, (_) async => null);

    // default: listFiles returns empty lists, uploadFile succeeds
    when(() => mockApi.listFiles(any())).thenAnswer((_) async => []);
    when(() => mockApi.uploadFile(any())).thenAnswer((_) async => 'new-id');
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, null);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_filePickerChannel, null);
  });

  // ── FAB visible ───────────────────────────────────────────────────────────

  testWidgets('FAB is visible on dashboard', (tester) async {
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();
    expect(find.byType(FloatingActionButton), findsOneWidget);
  });

  testWidgets('FAB shows add icon when idle', (tester) async {
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();
    expect(find.byIcon(Icons.add), findsOneWidget);
  });

  // ── FAB pick + upload ─────────────────────────────────────────────────────

  testWidgets('FAB tap calls uploadFile with bytes — no filename', (tester) async {
    _stubFilePicker();
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    final captured = verify(() => mockApi.uploadFile(captureAny())).captured;
    expect(captured, hasLength(1));
    expect(captured.first, isA<Uint8List>(),
        reason: 'only raw bytes are passed — no filename');
  });

  testWidgets('FAB shows spinner during upload', (tester) async {
    _stubFilePicker();
    // make uploadFile slow so we can observe the in-progress state
    when(() => mockApi.uploadFile(any())).thenAnswer(
        (_) => Future.delayed(const Duration(milliseconds: 100), () => 'id'));

    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pump(); // one frame — upload has started but not completed

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.byIcon(Icons.add), findsNothing);

    await tester.pumpAndSettle();
  });

  testWidgets('FAB disables during upload (no double-submit)', (tester) async {
    _stubFilePicker();
    when(() => mockApi.uploadFile(any())).thenAnswer(
        (_) => Future.delayed(const Duration(milliseconds: 100), () => 'id'));

    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pump();

    final fab = tester.widget<FloatingActionButton>(
        find.byType(FloatingActionButton));
    expect(fab.onPressed, isNull,
        reason: 'FAB must be disabled while upload is in progress');

    await tester.pumpAndSettle();
  });

  testWidgets('cancelling file picker does not call uploadFile', (tester) async {
    _stubFilePicker(cancel: true);
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    verifyNever(() => mockApi.uploadFile(any()));
  });

  testWidgets('upload error shows snackbar', (tester) async {
    _stubFilePicker();
    when(() => mockApi.uploadFile(any()))
        .thenThrow(const ApiException(415, 'Unsupported file type'));

    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('Unsupported file type'), findsOneWidget);
  });

  testWidgets('dashboard reloads after successful upload', (tester) async {
    _stubFilePicker();
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    // listFiles called once on init + once after upload = 4 total (pending+saved × 2)
    verify(() => mockApi.listFiles(any())).called(greaterThanOrEqualTo(4));
  });
}
