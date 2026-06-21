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

// ── FilePicker fake ───────────────────────────────────────────────────────────
// FilePicker.platform is a late static that is never initialised during tests
// (no plugin registration). Subclass and inject via FilePicker.platform = ...

class _FakeFilePicker extends FilePicker {
  _FakeFilePicker({required this.bytes});
  final Uint8List? bytes; // null → simulate cancel

  @override
  Future<FilePickerResult?> pickFiles({
    String? dialogTitle,
    String? initialDirectory,
    FileType type = FileType.any,
    List<String>? allowedExtensions,
    Function(FilePickerStatus)? onFileLoading,
    bool allowCompression = true,
    int compressionQuality = 30,
    bool allowMultiple = false,
    bool withData = false,
    bool withReadStream = false,
    bool lockParentWindow = false,
    bool readSequential = false,
  }) async {
    if (bytes == null) return null;
    return FilePickerResult([
      PlatformFile(name: 'test.png', size: bytes!.length, bytes: bytes),
    ]);
  }

  @override
  Future<bool?> clearTemporaryFiles() async => true;

  @override
  Future<String?> getDirectoryPath({
    String? dialogTitle,
    String? initialDirectory,
    bool lockParentWindow = false,
  }) async => null;

  @override
  Future<String?> saveFile({
    String? dialogTitle,
    String? fileName,
    String? initialDirectory,
    FileType type = FileType.any,
    List<String>? allowedExtensions,
    bool lockParentWindow = false,
    Uint8List? bytes,
  }) async => null;
}

// ── secure storage channel (silenced) ────────────────────────────────────────

const _secureChannel =
    MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

final _tinyBytes = Uint8List.fromList([137, 80, 78, 71, 1, 2, 3, 4]);

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

    // default picker: returns _tinyBytes (overridden in cancel test)
    FilePicker.platform = _FakeFilePicker(bytes: _tinyBytes);

    // silence secure storage native channel
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, (_) async => null);

    // default API stubs
    when(() => mockApi.listFiles(any())).thenAnswer((_) async => []);
    when(() => mockApi.uploadFile(any())).thenAnswer((_) async => 'new-id');
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_secureChannel, null);
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
    FilePicker.platform = _FakeFilePicker(bytes: null); // simulate cancel
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    verifyNever(() => mockApi.uploadFile(any()));
  });

  testWidgets('upload error shows snackbar', (tester) async {
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
    await tester.pumpWidget(_app(mockApi));
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    // listFiles called once on init + once after upload = 4 total (pending+saved × 2)
    verify(() => mockApi.listFiles(any())).called(greaterThanOrEqualTo(4));
  });
}
