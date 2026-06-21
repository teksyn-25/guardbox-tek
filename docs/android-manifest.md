# AndroidManifest.xml — what it does

`AndroidManifest.xml` is the identity and permissions declaration for the Android app. Android reads it before running anything.

---

## `<application>` block

Declares the app itself — its label ("guardbox", shown under the icon), the icon, and the entry class. `${applicationName}` is filled in by Flutter at build time.

---

## First `<intent-filter>` — launcher

```xml
<action android:name="android.intent.action.MAIN" />
<category android:name="android.intent.category.LAUNCHER" />
```

Tells Android this is the screen to open when the user taps the app icon on the home screen. Without this, the app installs but never appears in the launcher.

---

## Second `<intent-filter>` — deep link for auth

```xml
<data android:scheme="guardbox" android:host="auth" />
```

Tells Android: "when any app tries to open a URL starting with `guardbox://auth`, route it to GuardBox." This is how the Telegram OAuth callback returns the session token to the app — the backend redirects to `guardbox://auth?token=xxx` and Android hands that URL to GuardBox, which reads the token from it.

---

## Third `<intent-filter>` — WhatsApp share-sheet

```xml
<action android:name="android.intent.action.SEND" />
<data android:mimeType="image/*" />
```

Registers GuardBox as a share target for image files. This is what makes "GuardBox" appear in the share sheet when the user taps Share inside WhatsApp. Without this, the user has no way to send a file from WhatsApp into the app.

---

## `flutterEmbedding` meta-data

Required by Flutter's embedding layer. Without it, Flutter's plugin system does not initialize correctly and all plugins (including `receive_sharing_intent`) will fail silently.

---

## `<queries>` block

Required since Android 11 (API 30). Android restricts which other apps your app can "see." This declares that GuardBox needs to query apps that handle plain text processing — Flutter needs this for its text-selection plugin on Android.
