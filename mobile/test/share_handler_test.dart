import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:guardbox/services/share_handler.dart';

// Native side (ShareIntentReader.kt) reads shared images from the
// content:// URI straight into memory and emits one event per share
// intent — see mobile/android-manifest.md and CLAUDE.md's WhatsApp
// disk-write rule. These tests validate the Dart-side channel contract
// only; the "never touches disk" property itself is native code and is
// verified by manual device check (see the implementation plan).
const _shareChannel = EventChannel('com.guardbox.guardbox/share');

class _SinkBox {
  MockStreamHandlerEventSink? sink;
}

void main() {
  // Registered inside each testWidgets body (not in setUp) — setUp runs
  // outside the FakeAsync zone testWidgets creates for its body, so a
  // StreamController listened-to there schedules delivery on the real
  // zone's microtask queue, which pump()'s FakeAsync-scoped
  // flushMicrotasks() can never drain.
  //
  // `onListen` only fires once ShareHandlerService.init() starts
  // listening, so the sink is captured into a mutable holder rather than
  // returned directly (which would read it before it's ever set).
  _SinkBox registerMockShareChannel() {
    final box = _SinkBox();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockStreamHandler(
      _shareChannel,
      MockStreamHandler.inline(onListen: (args, events) {
        box.sink = events;
      }),
    );
    return box;
  }

  setUp(() {
    // setFolderTag() persists via SharedPreferences — mock its storage so
    // the folder-tag write after each dialog choice doesn't hit a
    // real/missing platform channel.
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockStreamHandler(_shareChannel, null);
  });

  Widget app(GlobalKey<NavigatorState> navKey) => MaterialApp(
        navigatorKey: navKey,
        home: const Scaffold(body: Text('home-screen')),
        routes: {
          '/dashboard': (_) => const Scaffold(body: Text('dashboard-screen')),
        },
      );

  Map<Object?, Object?> item(String label, {String? error}) => {
        if (error != null) 'error': error,
        if (error == null) 'bytes': Uint8List.fromList(label.codeUnits),
        'fileName': '$label.png',
        'mimeType': 'image/png',
      };

  testWidgets('single-image event uploads and navigates to dashboard',
      (tester) async {
    final navKey = GlobalKey<NavigatorState>();
    final uploaded = <Uint8List>[];
    final sinkBox = registerMockShareChannel();
    await tester.pumpWidget(app(navKey));

    ShareHandlerService.init(navKey, (bytes) async {
      uploaded.add(bytes);
      return 'file-1';
    });
    await tester.pump();

    sinkBox.sink!.success([item('a')]);
    await tester.pumpAndSettle();
    expect(find.text('Save to'), findsOneWidget);

    await tester.tap(find.text('Other'));
    await tester.pumpAndSettle();

    expect(uploaded, [Uint8List.fromList('a'.codeUnits)]);
    expect(find.text('dashboard-screen'), findsOneWidget);
  });

  testWidgets(
      'multi-image event uploads each item and navigates exactly once',
      (tester) async {
    final navKey = GlobalKey<NavigatorState>();
    final uploaded = <Uint8List>[];
    final sinkBox = registerMockShareChannel();
    await tester.pumpWidget(app(navKey));

    ShareHandlerService.init(navKey, (bytes) async {
      uploaded.add(bytes);
      return 'file-${uploaded.length}';
    });
    await tester.pump();

    sinkBox.sink!.success([item('a'), item('b')]);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Other')); // resolves first item's dialog
    await tester.pumpAndSettle();
    await tester.tap(find.text('Other')); // resolves second item's dialog
    await tester.pumpAndSettle();

    expect(uploaded, [
      Uint8List.fromList('a'.codeUnits),
      Uint8List.fromList('b'.codeUnits),
    ]);
    // Navigated to dashboard exactly once, after both items — not per item.
    expect(find.text('dashboard-screen'), findsOneWidget);
  });

  testWidgets('item with error key is skipped, remaining items processed',
      (tester) async {
    final navKey = GlobalKey<NavigatorState>();
    final uploaded = <Uint8List>[];
    final sinkBox = registerMockShareChannel();
    await tester.pumpWidget(app(navKey));

    ShareHandlerService.init(navKey, (bytes) async {
      uploaded.add(bytes);
      return 'file-1';
    });
    await tester.pump();

    sinkBox.sink!.success([item('too-big', error: 'file_too_large'), item('ok')]);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Other'));
    await tester.pumpAndSettle();

    expect(uploaded, [Uint8List.fromList('ok'.codeUnits)]);
    expect(find.text('dashboard-screen'), findsOneWidget);
  });

  testWidgets('stream error does not throw', (tester) async {
    final navKey = GlobalKey<NavigatorState>();
    final sinkBox = registerMockShareChannel();
    await tester.pumpWidget(app(navKey));

    ShareHandlerService.init(navKey, (bytes) async => 'file-1');
    await tester.pump();

    sinkBox.sink!.error(code: 'boom', message: 'native failure');
    await tester.pump();

    // No crash, no navigation, no dialog — the stream error is swallowed
    // exactly like the current onError: (_) {} behavior.
    expect(find.text('home-screen'), findsOneWidget);
  });
}
