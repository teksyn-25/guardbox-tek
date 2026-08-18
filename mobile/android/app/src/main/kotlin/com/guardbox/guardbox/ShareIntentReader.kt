package com.guardbox.guardbox

import android.content.ContentResolver
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.EventChannel
import java.io.ByteArrayOutputStream

/**
 * Reads WhatsApp / share-sheet images straight from the OS share Intent's
 * content:// URI into memory and hands them to Dart over an EventChannel.
 *
 * This class deliberately never touches a File, FileOutputStream, or
 * context.cacheDir anywhere in its body — that absence is what makes
 * CLAUDE.md's WhatsApp security claim ("GuardBox itself never saves the
 * original to disk") literally true. See share_handler.dart on the Dart
 * side and mobile/share-sheet-intake.md for the full flow.
 */
private const val CHANNEL_NAME = "com.guardbox.guardbox/share"
private const val MAX_FILE_SIZE = 25 * 1024 * 1024 // matches backend/intake/upload.py

class ShareIntentReader : EventChannel.StreamHandler {
    private var eventSink: EventChannel.EventSink? = null
    private val pendingEvents = mutableListOf<Any>()

    fun attach(messenger: BinaryMessenger) {
        EventChannel(messenger, CHANNEL_NAME).setStreamHandler(this)
    }

    override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
        eventSink = events
        pendingEvents.forEach { events.success(it) }
        pendingEvents.clear()
    }

    override fun onCancel(arguments: Any?) {
        eventSink = null
    }

    fun handleIntent(context: Context, intent: Intent) {
        val mimeType = intent.type ?: return
        if (!mimeType.startsWith("image/")) return

        val uris: List<Uri> = when (intent.action) {
            Intent.ACTION_SEND ->
                intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)?.let { listOf(it) } ?: return
            Intent.ACTION_SEND_MULTIPLE ->
                intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM) ?: return
            else -> return
        }
        if (uris.isEmpty()) return

        val items = uris.map { readImage(context, it, mimeType) }
        emit(items)
    }

    private fun emit(event: Any) {
        val sink = eventSink
        if (sink != null) sink.success(event) else pendingEvents.add(event)
    }

    /**
     * Reads one shared image entirely in memory. Never opens a File/
     * FileOutputStream — only ContentResolver's own InputStream on the
     * content:// URI, buffered straight into a ByteArrayOutputStream.
     */
    private fun readImage(context: Context, uri: Uri, mimeType: String): Map<String, Any?> {
        val resolver: ContentResolver = context.contentResolver
        val (displayName, declaredSize) = queryMeta(resolver, uri)

        if (declaredSize != null && declaredSize > MAX_FILE_SIZE) {
            return mapOf("error" to "file_too_large", "fileName" to displayName)
        }

        val initialCapacity = (declaredSize ?: 8192L).coerceAtMost(MAX_FILE_SIZE.toLong()).toInt()
        val buffer = ByteArrayOutputStream(initialCapacity)
        val chunk = ByteArray(64 * 1024)

        resolver.openInputStream(uri)?.use { input ->
            var total = 0
            while (true) {
                val read = input.read(chunk)
                if (read == -1) break
                total += read
                if (total > MAX_FILE_SIZE) {
                    return mapOf("error" to "file_too_large", "fileName" to displayName)
                }
                buffer.write(chunk, 0, read)
            }
        } ?: return mapOf("error" to "file_too_large", "fileName" to displayName)

        return mapOf(
            "bytes" to buffer.toByteArray(),
            "mimeType" to mimeType,
            "fileName" to displayName,
        )
    }

    /** Cheap cursor read — not a file copy — used to reject oversized files early. */
    private fun queryMeta(resolver: ContentResolver, uri: Uri): Pair<String?, Long?> {
        var name: String? = null
        var size: Long? = null
        resolver.query(uri, null, null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIdx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                val sizeIdx = cursor.getColumnIndex(OpenableColumns.SIZE)
                if (nameIdx >= 0) name = cursor.getString(nameIdx)
                if (sizeIdx >= 0 && !cursor.isNull(sizeIdx)) size = cursor.getLong(sizeIdx)
            }
        }
        return name to size
    }
}
