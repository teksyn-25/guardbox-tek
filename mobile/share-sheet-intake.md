# WhatsApp Share-Sheet Intake

How a file travels from WhatsApp to GuardBox without being saved to the device.

## Prerequisites

Configure WhatsApp before using GuardBox:
- Settings → Storage and Data → Media auto-download → **No media** (all networks)
- Settings → Chats → Media visibility / Save to Camera Roll → **OFF**

With these settings, WhatsApp never downloads files automatically.

## Flow

```
WhatsApp image (not yet on device — auto-download OFF)
        │
        │  user taps Share
        ▼
WhatsApp downloads file into its own private app sandbox
(outside GuardBox's control — never reaches gallery)
        │
        ▼
Android share sheet — GuardBox appears
(registered via SEND intent filter in AndroidManifest.xml)
        │
        │  user selects GuardBox
        ▼
Flutter app opens / comes to foreground
        │
        ▼
receive_sharing_intent plugin
writes temp copy to Flutter's private app cache
(NOT gallery — not accessible to other apps)
        │
        ▼
share_handler.dart
  1. reads bytes into memory
  2. File(path).delete()     ← temp file deleted immediately
  3. api.uploadFile(bytes)   ← no filename transmitted
        │
        ▼
Backend: CDR sanitise → storage.save()
        │
        ▼
Flutter dashboard — clean reconstructed PNG shown
```

## What never happens

- The original file never reaches the gallery or file manager.
- No other app on the device can read the file during this flow.
- GuardBox never stores the original filename, file size, or timestamp.
- The temp copy in Flutter's cache is deleted before upload begins.

## What WhatsApp does (outside GuardBox's control)

WhatsApp downloads the file to its own private sandbox when you tap Share.
This is confined to WhatsApp's private storage and invisible to other apps.
GuardBox cannot prevent this — it is how Android's share-sheet mechanism works.
With auto-download OFF, this only happens when you explicitly choose to share.

## Code references

| What | Where |
|---|---|
| Share intent registration | `android/app/src/main/AndroidManifest.xml` |
| Share handler (bytes → delete temp → upload) | `lib/services/share_handler.dart` |
| Upload client (no filename in multipart) | `lib/services/api_client.dart` — `uploadFile()` |
| Backend CDR + storage | `backend/cdr/sanitize.py`, `backend/intake/upload.py` |
