import UIKit
import WebKit

/// Hosts the shared web interface and answers its native calls (see shared/web/app.js).
final class WebAppController: UIViewController, WKScriptMessageHandler, WKNavigationDelegate {
    private var webView: WKWebView!
    private lazy var reader = PageReader(host: self)

    private var documents: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    override func loadView() {
        let configuration = WKWebViewConfiguration()
        configuration.setURLSchemeHandler(BundleSchemeHandler(), forURLScheme: BundleSchemeHandler.scheme)
        configuration.userContentController.add(WeakMessageHandler(self), name: "native")
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.isOpaque = false
        webView.backgroundColor = Palette.background
        webView.scrollView.backgroundColor = Palette.background
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.navigationDelegate = self
        view = webView
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        var address = "\(BundleSchemeHandler.scheme)://app/index.html"
        #if DEBUG
        // Test hooks: xcrun simctl launch <device> <bundle> -startPage library -testRead <url> -testKind works
        let defaults = UserDefaults.standard
        if let page = defaults.string(forKey: "startPage") { address += "#\(page)" }
        if let url = defaults.string(forKey: "testRead").flatMap(URL.init(string:)) {
            let kind = defaults.string(forKey: "testKind") ?? "story"
            if let encoded = defaults.string(forKey: "testScript64"), let data = Data(base64Encoded: encoded) {
                reader.debugScript = String(data: data, encoding: .utf8)
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
                self?.reader.read(url: url, kind: kind, args: ["url": url.absoluteString, "storyId": defaults.string(forKey: "testStoryId") ?? ""], labels: [:]) { json in
                    try? json.write(to: self!.documents.appendingPathComponent("test-read.json"), atomically: true, encoding: .utf8)
                }
            }
        }
        #endif
        webView.load(URLRequest(url: URL(string: address)!))
    }

    #if DEBUG
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        // Test hook: -testJS64 <base64 script> runs in the interface once it has loaded.
        guard let encoded = UserDefaults.standard.string(forKey: "testJS64"),
              let data = Data(base64Encoded: encoded),
              let script = String(data: data, encoding: .utf8) else { return }
        webView.evaluateJavaScript(script)
    }
    #endif

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url, url.scheme != BundleSchemeHandler.scheme else {
            decisionHandler(.allow)
            return
        }
        UIApplication.shared.open(url)
        decisionHandler(.cancel)
    }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        guard
            let body = message.body as? [String: Any],
            let id = body["id"] as? Int,
            let method = body["method"] as? String
        else { return }
        let args = body["args"] as? [String: Any] ?? [:]
        switch method {
        case "read": read(id, args)
        case "cover": cover(id, args)
        case "image": image(id, args)
        case "save": save(id, args)
        case "share": share(id, args)
        case "openFiles": openFiles(id)
        case "clipboard": reply(id, ["ok": true, "data": UIPasteboard.general.string ?? ""])
        case "openUrl":
            if let url = URL(string: args["url"] as? String ?? "") { UIApplication.shared.open(url) }
            reply(id, ["ok": true])
        default: reply(id, ["ok": false, "error": "script_error", "params": ["message": "Unknown call \(method)"]])
        }
    }

    // MARK: - Calls

    private func read(_ id: Int, _ args: [String: Any]) {
        guard let url = URL(string: args["url"] as? String ?? ""), let kind = args["kind"] as? String else {
            reply(id, ["ok": false, "error": "script_error"])
            return
        }
        let labels = args["labels"] as? [String: String] ?? [:]
        let pageArgs = args["args"] as? [String: Any] ?? [:]
        reader.read(url: url, kind: kind, args: pageArgs, labels: labels) { [weak self] json in
            self?.replyRaw(id, json)
        }
    }

    private func cover(_ id: Int, _ args: [String: Any]) {
        guard let url = URL(string: args["url"] as? String ?? "") else {
            reply(id, ["ok": false])
            return
        }
        URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            let jpeg = data.flatMap(UIImage.init(data:))?.jpegData(compressionQuality: 0.9)
            DispatchQueue.main.async {
                if let jpeg {
                    self?.reply(id, ["ok": true, "data": jpeg.base64EncodedString()])
                } else {
                    self?.reply(id, ["ok": false])
                }
            }
        }.resume()
    }

    /// A picture for display, as the server sent it (covers, avatars).
    private func image(_ id: Int, _ args: [String: Any]) {
        guard let url = URL(string: args["url"] as? String ?? "") else {
            reply(id, ["ok": false])
            return
        }
        URLSession.shared.dataTask(with: url) { [weak self] data, response, _ in
            let mime = response?.mimeType ?? "image/jpeg"
            DispatchQueue.main.async {
                if let data, !data.isEmpty, mime.hasPrefix("image/") {
                    self?.reply(id, ["ok": true, "data": "data:\(mime);base64,\(data.base64EncodedString())"])
                } else {
                    self?.reply(id, ["ok": false])
                }
            }
        }.resume()
    }

    private func save(_ id: Int, _ args: [String: Any]) {
        guard
            let name = args["name"] as? String,
            let encoded = args["base64"] as? String,
            let data = Data(base64Encoded: encoded)
        else {
            reply(id, ["ok": false, "error": "script_error"])
            return
        }
        let target = documents.appendingPathComponent(safeName(name))
        do {
            try data.write(to: target, options: .atomic)
            reply(id, ["ok": true, "data": ["name": target.lastPathComponent]])
        } catch {
            reply(id, ["ok": false, "error": "script_error", "params": ["message": error.localizedDescription]])
        }
    }

    private func share(_ id: Int, _ args: [String: Any]) {
        let file = documents.appendingPathComponent(safeName(args["name"] as? String ?? ""))
        guard FileManager.default.fileExists(atPath: file.path) else {
            reply(id, ["ok": false])
            return
        }
        let sheet = UIActivityViewController(activityItems: [file], applicationActivities: nil)
        sheet.popoverPresentationController?.sourceView = view
        sheet.popoverPresentationController?.sourceRect = CGRect(x: view.bounds.midX, y: view.bounds.midY, width: 1, height: 1)
        present(sheet, animated: true)
        reply(id, ["ok": true])
    }

    private func openFiles(_ id: Int) {
        // The Files app opens a folder from a shareddocuments:// link to its path.
        let path = documents.path.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? documents.path
        if let url = URL(string: "shareddocuments://\(path)") {
            UIApplication.shared.open(url)
        }
        reply(id, ["ok": true])
    }

    // MARK: - Replies

    private func reply(_ id: Int, _ result: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: result), let json = String(data: data, encoding: .utf8) else { return }
        replyRaw(id, json)
    }

    private func replyRaw(_ id: Int, _ json: String) {
        webView.evaluateJavaScript("FicbookNative._resolve(\(id), \(json))")
    }

    private func safeName(_ name: String) -> String {
        let cleaned = name.replacingOccurrences(of: "/", with: " ").replacingOccurrences(of: ":", with: " ")
        return cleaned.isEmpty ? "story.txt" : cleaned
    }
}

/// Serves shared/web from the app bundle, so the page has a stable origin for its settings.
final class BundleSchemeHandler: NSObject, WKURLSchemeHandler {
    static let scheme = "ficbook-app"
    private let root = Bundle.main.resourceURL!.appendingPathComponent("web").standardizedFileURL

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url else { return }
        let path = url.path.isEmpty || url.path == "/" ? "index.html" : String(url.path.dropFirst())
        let file = root.appendingPathComponent(path).standardizedFileURL
        guard file.path.hasPrefix(root.path), let data = try? Data(contentsOf: file) else {
            task.didFailWithError(URLError(.fileDoesNotExist))
            return
        }
        let headers = ["Content-Type": mimeType(file.pathExtension), "Cache-Control": "no-cache"]
        task.didReceive(HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}

    private func mimeType(_ ext: String) -> String {
        switch ext {
        case "html": return "text/html; charset=utf-8"
        case "css": return "text/css; charset=utf-8"
        case "js": return "text/javascript; charset=utf-8"
        case "svg": return "image/svg+xml"
        case "png": return "image/png"
        default: return "application/octet-stream"
        }
    }
}

/// WKUserContentController keeps its handlers alive; this avoids a retain cycle with the controller.
final class WeakMessageHandler: NSObject, WKScriptMessageHandler {
    private weak var target: WKScriptMessageHandler?

    init(_ target: WKScriptMessageHandler) {
        self.target = target
    }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        target?.userContentController(controller, didReceive: message)
    }
}
