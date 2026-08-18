package com.guardbox.guardbox

import android.content.Intent
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    private val shareReader = ShareIntentReader()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        shareReader.attach(flutterEngine.dartExecutor.binaryMessenger)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Only the very first launch — onCreate re-runs on activity
        // recreation (e.g. process-death restore) with savedInstanceState
        // non-null and would otherwise replay the same share intent.
        if (savedInstanceState == null) {
            shareReader.handleIntent(applicationContext, intent)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        shareReader.handleIntent(applicationContext, intent)
    }
}
