import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'folder_tags.dart';
import '../widgets/folder_choice_dialog.dart';

typedef UploadCallback = Future<String> Function(Uint8List bytes);

// Native side (ShareIntentReader.kt) reads shared images from the
// content:// URI straight into memory — no File/FileOutputStream, ever —
// and emits one event per share intent. This is what makes CLAUDE.md's
// WhatsApp claim "GuardBox itself never saves the original to disk"
// literally true. See mobile/share-sheet-intake.md for the full flow.
const _shareChannel = EventChannel('com.guardbox.guardbox/share');

class ShareHandlerService {
  static void init(GlobalKey<NavigatorState> navKey, UploadCallback onFile) {
    _shareChannel.receiveBroadcastStream().listen(
      (event) => _handle(event, navKey, onFile),
      onError: (_) {},
    );
  }

  static Future<void> _handle(
    dynamic event,
    GlobalKey<NavigatorState> navKey,
    UploadCallback onFile,
  ) async {
    final items = List<Map<Object?, Object?>>.from(event as List);
    for (final item in items) {
      if (item['error'] != null) continue;
      final bytes = item['bytes'] as Uint8List;
      final fileId = await onFile(bytes);

      // User's own explicit choice of folder — never guessed. Android's
      // share intent can't identify which app sent this, so we ask instead
      // of pretending to know. Purely organizational; does not touch the
      // verified FileItem.source used for the security-claim text.
      final context = navKey.currentContext;
      if (context != null) {
        final tag = await promptFolderChoice(context);
        await setFolderTag(fileId, tag);
      }
    }
    navKey.currentState?.pushNamedAndRemoveUntil('/dashboard', (_) => false);
  }
}
