# Flutter deployment — how it runs without Docker

Flutter does not need Docker. It runs directly on the phone as a native app. Docker is only for the backend server on Fedora.

```
Fedora server                        Phone
┌─────────────────────────┐          ┌─────────────────────┐
│ docker-compose up       │          │ Flutter app         │
│  └── backend container  │  HTTPS   │  (installed APK     │
│       FastAPI + CDR     │◄────────►│   or IPA)           │
│       port 443          │          │                     │
└─────────────────────────┘          └─────────────────────┘
```

## How the Flutter app gets onto the phone

- `flutter build apk` → produces `guardbox.apk` → sideload on Android (`adb install` or share the file directly)
- `flutter build ios` → requires Xcode + Apple Developer account → TestFlight or direct device install

The Flutter app itself has no server, no daemon, no Docker. It is a native binary that:

1. Reads the server URL (configured once by the user on first launch)
2. Makes HTTPS calls to the Fedora backend
3. Displays the results

## What runs where

Only the backend runs on Fedora. Flutter never touches the server — it only talks to it over HTTPS.

## Deploy story

1. `docker-compose up` on Fedora — backend is live
2. Install APK on Android phone — app is live
3. User opens app, types in server URL once — done

No additional infrastructure required. The Flutter app is a thin HTTPS client; all CDR processing, storage, and the Telegram bot run inside the Docker container on the server.
