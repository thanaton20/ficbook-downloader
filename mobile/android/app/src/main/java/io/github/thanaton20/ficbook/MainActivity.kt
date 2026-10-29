package io.github.thanaton20.ficbook

import android.annotation.SuppressLint
import android.app.Activity
import android.app.DownloadManager
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.widget.FrameLayout
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewClientCompat
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

/** Hosts the shared web interface and answers its native calls (see shared/web/app.js). */
class MainActivity : Activity() {
    private lateinit var ui: WebView
    private lateinit var reader: PageReader
    private val folder = "${Environment.DIRECTORY_DOWNLOADS}/Ficbook/"
    private val savedFiles by lazy { getSharedPreferences("saved-files", MODE_PRIVATE) }

    @SuppressLint("SetJavaScriptEnabled", "JavascriptInterface")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val root = FrameLayout(this)
        ui = WebView(this)
        ui.setBackgroundColor(getColor(R.color.background))
        ui.settings.javaScriptEnabled = true
        ui.settings.domStorageEnabled = true
        root.addView(ui, FrameLayout.LayoutParams(-1, -1))
        reader = PageReader(this, root)
        setContentView(root)

        val assets = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
        ui.webViewClient = object : WebViewClientCompat() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                assets.shouldInterceptRequest(request.url)

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == HOST) return false
                openUrl(request.url)
                return true
            }

            override fun onPageFinished(view: WebView, url: String) {
                // Test hook for debug builds: adb shell am start ... --es testJS64 <base64 script>
                if (!debuggable) return
                val encoded = intent.getStringExtra("testJS64") ?: return
                ui.evaluateJavascript(String(Base64.decode(encoded, Base64.DEFAULT)), null)
            }
        }
        if (debuggable) WebView.setWebContentsDebuggingEnabled(true)
        ui.addJavascriptInterface(Bridge(), "AndroidBridge")
        ui.loadUrl("https://$HOST/assets/web/index.html")

        // The page can't see Android's bars, so pass their size in as CSS variables.
        ViewCompat.setOnApplyWindowInsetsListener(root) { _, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            val density = resources.displayMetrics.density
            val script = "document.documentElement.style.setProperty('--safe-top','${bars.top / density}px');" +
                "document.documentElement.style.setProperty('--safe-bottom','${bars.bottom / density}px');"
            ui.evaluateJavascript(script, null)
            insetScript = script
            reader.applyInsets(bars.top, bars.bottom)
            insets
        }
    }

    private var insetScript = ""
    private val debuggable get() = applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0

    @Deprecated("Activity back handling without AndroidX")
    override fun onBackPressed() {
        if (!reader.cancelIfShowing()) super.onBackPressed()
    }

    private inner class Bridge {
        @JavascriptInterface
        fun post(message: String) {
            runOnUiThread { handle(JSONObject(message)) }
        }
    }

    private fun handle(message: JSONObject) {
        val id = message.optInt("id")
        val args = message.optJSONObject("args") ?: JSONObject()
        when (message.optString("method")) {
            "read" -> {
                if (insetScript.isNotEmpty()) ui.evaluateJavascript(insetScript, null)
                reader.read(
                    args.optString("url"),
                    args.optString("kind"),
                    args.optJSONObject("args") ?: JSONObject(),
                    args.optJSONObject("labels") ?: JSONObject(),
                ) { json -> replyRaw(id, json) }
            }
            "cover" -> cover(id, args.optString("url"))
            "image" -> image(id, args.optString("url"))
            "save" -> save(id, args)
            "share" -> share(id, args.optString("name"))
            "openFiles" -> {
                try {
                    startActivity(Intent(DownloadManager.ACTION_VIEW_DOWNLOADS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } catch (_: ActivityNotFoundException) {
                }
                reply(id, JSONObject().put("ok", true))
            }
            "clipboard" -> {
                val clip = getSystemService(ClipboardManager::class.java).primaryClip
                val text = if (clip != null && clip.itemCount > 0) clip.getItemAt(0).coerceToText(this).toString() else ""
                reply(id, JSONObject().put("ok", true).put("data", text))
            }
            "openUrl" -> {
                openUrl(Uri.parse(args.optString("url")))
                reply(id, JSONObject().put("ok", true))
            }
            else -> reply(id, error("script_error"))
        }
    }

    private fun cover(id: Int, address: String) {
        thread {
            val jpeg = try {
                val connection = URL(address).openConnection() as HttpURLConnection
                connection.connectTimeout = 20_000
                connection.readTimeout = 20_000
                val bytes = connection.inputStream.use { it.readBytes() }
                val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ByteArrayOutputStream().also { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, it) }.toByteArray()
            } catch (_: Exception) {
                null
            }
            runOnUiThread {
                if (jpeg != null) reply(id, JSONObject().put("ok", true).put("data", Base64.encodeToString(jpeg, Base64.NO_WRAP)))
                else reply(id, JSONObject().put("ok", false))
            }
        }
    }

    /** A picture for display, as the server sent it (covers, avatars). */
    private fun image(id: Int, address: String) {
        thread {
            val result = try {
                val connection = URL(address).openConnection() as HttpURLConnection
                connection.connectTimeout = 20_000
                connection.readTimeout = 20_000
                val mime = connection.contentType?.substringBefore(';')?.trim() ?: "image/jpeg"
                val bytes = connection.inputStream.use { it.readBytes() }
                if (bytes.isNotEmpty() && mime.startsWith("image/")) "data:$mime;base64,${Base64.encodeToString(bytes, Base64.NO_WRAP)}" else null
            } catch (_: Exception) {
                null
            }
            runOnUiThread {
                if (result != null) reply(id, JSONObject().put("ok", true).put("data", result))
                else reply(id, JSONObject().put("ok", false))
            }
        }
    }

    private fun save(id: Int, args: JSONObject) {
        val name = args.optString("name").replace('/', ' ').ifBlank { "story.txt" }
        val mime = args.optString("mime", "application/octet-stream")
        val data = try {
            Base64.decode(args.optString("base64"), Base64.DEFAULT)
        } catch (_: IllegalArgumentException) {
            reply(id, error("script_error"))
            return
        }
        val collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI
        try {
            // Replace an earlier copy instead of collecting "name (1).epub" duplicates.
            contentResolver.delete(
                collection,
                "${MediaStore.MediaColumns.DISPLAY_NAME}=? AND ${MediaStore.MediaColumns.RELATIVE_PATH}=?",
                arrayOf(name, folder),
            )
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                put(MediaStore.MediaColumns.MIME_TYPE, mime)
                put(MediaStore.MediaColumns.RELATIVE_PATH, folder)
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
            val uri = contentResolver.insert(collection, values) ?: throw IllegalStateException("Could not create $name")
            contentResolver.openOutputStream(uri)?.use { it.write(data) }
            contentResolver.update(uri, ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }, null, null)
            savedFiles.edit().putString(name, "$uri|$mime").apply()
            reply(id, JSONObject().put("ok", true).put("data", JSONObject().put("name", name)))
        } catch (exception: Exception) {
            reply(id, error("script_error").put("params", JSONObject().put("message", exception.message ?: "")))
        }
    }

    private fun share(id: Int, name: String) {
        val saved = savedFiles.getString(name, null)?.split("|")
        val uri = saved?.getOrNull(0)?.let(Uri::parse)
        val exists = uri != null && try {
            contentResolver.openFileDescriptor(uri, "r")?.close()
            true
        } catch (_: Exception) {
            false
        }
        if (!exists) {
            savedFiles.edit().remove(name).apply()
            reply(id, JSONObject().put("ok", false))
            return
        }
        // Share a copy through our FileProvider: MediaStore links show up as bare numbers
        // in the share sheet and in the receiving app, the provider keeps the file name.
        val copy = File(cacheDir, "share").apply { deleteRecursively(); mkdirs() }.resolve(name)
        contentResolver.openInputStream(uri!!)?.use { input -> copy.outputStream().use { input.copyTo(it) } }
        val shared = FileProvider.getUriForFile(this, "$packageName.files", copy)
        val send = Intent(Intent.ACTION_SEND)
            .setType(saved?.getOrNull(1) ?: "application/octet-stream")
            .putExtra(Intent.EXTRA_STREAM, shared)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        send.clipData = ClipData.newUri(contentResolver, name, shared)
        startActivity(Intent.createChooser(send, name).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
        reply(id, JSONObject().put("ok", true))
    }

    private fun openUrl(uri: Uri) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (_: ActivityNotFoundException) {
        }
    }

    private fun reply(id: Int, result: JSONObject) = replyRaw(id, result.toString())

    private fun replyRaw(id: Int, json: String) {
        ui.evaluateJavascript("FicbookNative._resolve($id, $json)", null)
    }

    private fun error(code: String) = JSONObject().put("ok", false).put("error", code)

    companion object {
        private const val HOST = "appassets.androidplatform.net"
    }
}
