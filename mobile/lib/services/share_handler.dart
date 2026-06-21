import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

typedef UploadCallback = Future<void> Function(Uint8List bytes);

class ShareHandlerService {
  static void init(GlobalKey<NavigatorState> navKey, UploadCallback onFile) {
    // Files shared while the app is already running.
    ReceiveSharingIntent.instance.getMediaStream().listen(
      (files) => _handle(files, navKey, onFile),
      onError: (_) {},
    );

    // File that launched the app via share.
    ReceiveSharingIntent.instance.getInitialMedia().then((files) {
      if (files.isNotEmpty) {
        _handle(files, navKey, onFile);
        ReceiveSharingIntent.instance.reset();
      }
    });
  }

  static Future<void> _handle(
    List<SharedMediaFile> files,
    GlobalKey<NavigatorState> navKey,
    UploadCallback onFile,
  ) async {
    for (final f in files) {
      if (f.type != SharedMediaType.image) continue;
      final bytes = await File(f.path).readAsBytes();
      // Delete the plugin-cached copy immediately — original filename and file
      // must not remain in GuardBox's storage after the bytes are in memory.
      try { await File(f.path).delete(); } catch (_) {}
      await onFile(bytes);
    }
    navKey.currentState?.pushNamedAndRemoveUntil('/dashboard', (_) => false);
  }
}
