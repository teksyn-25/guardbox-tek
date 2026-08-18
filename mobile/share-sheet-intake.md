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
ShareIntentReader.kt (native Android)
opens the content:// URI via ContentResolver.openInputStream()
straight into an in-memory ByteArray — no File/FileOutputStream/
cacheDir reference anywhere in this class
        │
        │  EventChannel: one event per share intent
        ▼
share_handler.dart
  1. receives bytes over the EventChannel
  2. api.uploadFile(bytes)   ← no filename transmitted
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
- GuardBox's own code never writes the file to disk at any point — bytes
  go straight from `ContentResolver.openInputStream()` into memory.

## What WhatsApp does (outside GuardBox's control)

WhatsApp downloads the file to its own private sandbox when you tap Share.
This is confined to WhatsApp's private storage and invisible to other apps.
GuardBox cannot prevent this — it is how Android's share-sheet mechanism works.
With auto-download OFF, this only happens when you explicitly choose to share.

## Code references

| What | Where |
|---|---|
| Share intent registration | `android/app/src/main/AndroidManifest.xml` |
| Native intent reader (content:// URI → in-memory bytes, no disk) | `android/app/src/main/kotlin/com/guardbox/guardbox/ShareIntentReader.kt` |
| Activity wiring (feeds intents to the reader) | `android/app/src/main/kotlin/com/guardbox/guardbox/MainActivity.kt` |
| Share handler (EventChannel → upload) | `lib/services/share_handler.dart` |
| Upload client (no filename in multipart) | `lib/services/api_client.dart` — `uploadFile()` |
| Backend CDR + storage | `backend/cdr/sanitize.py`, `backend/intake/upload.py` |
