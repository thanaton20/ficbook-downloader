package io.github.thanaton20.ficbook

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Typeface
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject

/**
 * Opens ficbook pages in an ordinary WebView and reads them with shared/web/parse.js.
 *
 * The view stays hidden while pages load. When ficbook shows its security check
 * or age confirmation, the page is shown so the person can answer it themselves;
 * reading resumes as soon as the story page comes back.
 */
@SuppressLint("SetJavaScriptEnabled", "ViewConstructor")
class PageReader(private val activity: Activity, parent: FrameLayout) {
    private class Job(val url: String, val kind: String, val args: JSONObject, val completion: (String) -> Unit)

    private val webView = WebView(activity)
    private val overlay = LinearLayout(activity)
    private val header = LinearLayout(activity)
    private val title = TextView(activity)
    private val message = TextView(activity)
    private val cancel = TextView(activity)
    private val proceed = TextView(activity)
    private val handler = Handler(Looper.getMainLooper())
    private val parseScript = activity.assets.open("web/parse.js").bufferedReader().use { it.readText() }
    private var job: Job? = null
    private var labels = JSONObject()
    private val timeout = Runnable {
        val current = job
        if (current != null && overlay.visibility != View.VISIBLE) {
            webView.stopLoading()
            finish(errorJson("load_failed", current.url))
        }
    }

    init {
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) = evaluate()

            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                val current = job ?: return
                if (request.isForMainFrame && overlay.visibility != View.VISIBLE) finish(errorJson("load_failed", current.url))
            }
        }
        buildOverlay(parent)
    }

    fun read(url: String, kind: String, args: JSONObject, labels: JSONObject, completion: (String) -> Unit) {
        finish(CANCELLED)
        this.labels = labels
        job = Job(url, kind, args, completion)
        handler.postDelayed(timeout, 45_000)
        webView.loadUrl(url)
    }

    /** Back button: stop waiting on a check page. */
    fun cancelIfShowing(): Boolean {
        if (overlay.visibility != View.VISIBLE) return false
        finish(CANCELLED)
        return true
    }

    fun applyInsets(top: Int, bottom: Int) {
        header.setPadding(dp(16), top + dp(8), dp(16), dp(12))
        overlay.setPadding(0, 0, 0, bottom)
    }

    private fun evaluate() {
        val current = job ?: return
        val call = "JSON.stringify(FicbookParse.run(${JSONObject.quote(current.kind)}, ${current.args}))"
        webView.evaluateJavascript("$parseScript\n;$call") { value ->
            if (job !== current) return@evaluateJavascript
            // evaluateJavascript hands back the string as a JSON literal.
            val json = try {
                JSONArray("[$value]").getString(0)
            } catch (_: Exception) {
                """{"ok":false,"error":"script_error"}"""
            }
            when (errorCode(json)) {
                "security_check" -> showOverlay(labels.optString("check"))
                "age_check" -> showOverlay(labels.optString("age"))
                else -> finish(json)
            }
        }
    }

    private fun finish(json: String) {
        handler.removeCallbacks(timeout)
        overlay.visibility = View.GONE
        val current = job ?: return
        job = null
        current.completion(json)
    }

    private fun buildOverlay(parent: FrameLayout) {
        overlay.orientation = LinearLayout.VERTICAL
        overlay.setBackgroundColor(activity.getColor(R.color.card))
        overlay.visibility = View.GONE
        overlay.isClickable = true

        header.orientation = LinearLayout.VERTICAL
        header.setPadding(dp(16), dp(8), dp(16), dp(12))
        val buttons = LinearLayout(activity)
        buttons.orientation = LinearLayout.HORIZONTAL
        for ((view, bold) in listOf(cancel to false, proceed to true)) {
            view.setTextColor(activity.getColor(R.color.accent))
            view.textSize = 16f
            view.typeface = Typeface.create(Typeface.DEFAULT, if (bold) Typeface.BOLD else Typeface.NORMAL)
            view.minHeight = dp(44)
            view.gravity = Gravity.CENTER_VERTICAL
        }
        cancel.setOnClickListener { finish(CANCELLED) }
        proceed.setOnClickListener { job?.let { webView.loadUrl(it.url) } }
        buttons.addView(cancel, LinearLayout.LayoutParams(0, -2, 1f))
        buttons.addView(proceed, LinearLayout.LayoutParams(-2, -2))
        title.setTextColor(activity.getColor(R.color.ink))
        title.textSize = 17f
        title.typeface = Typeface.DEFAULT_BOLD
        message.setTextColor(activity.getColor(R.color.muted))
        message.textSize = 15f
        header.addView(buttons)
        header.addView(title)
        header.addView(message)

        val rule = View(activity)
        rule.setBackgroundColor(activity.getColor(R.color.line))
        overlay.addView(header, LinearLayout.LayoutParams(-1, -2))
        overlay.addView(rule, LinearLayout.LayoutParams(-1, 1))
        overlay.addView(webView, LinearLayout.LayoutParams(-1, 0, 1f))
        parent.addView(overlay, FrameLayout.LayoutParams(-1, -1))
    }

    private fun showOverlay(text: String) {
        handler.removeCallbacks(timeout)
        title.text = labels.optString("title")
        message.text = text
        cancel.text = labels.optString("cancel")
        proceed.text = labels.optString("continue")
        overlay.visibility = View.VISIBLE
        overlay.bringToFront()
    }

    private fun errorCode(json: String): String? = try {
        val result = JSONObject(json)
        if (result.optBoolean("ok")) null else result.optString("error")
    } catch (_: Exception) {
        null
    }

    private fun errorJson(code: String, url: String) =
        JSONObject().put("ok", false).put("error", code).put("params", JSONObject().put("url", url)).toString()

    private fun dp(value: Int) = (value * activity.resources.displayMetrics.density).toInt()

    companion object {
        private const val CANCELLED = """{"ok":false,"error":"cancelled"}"""
    }
}
