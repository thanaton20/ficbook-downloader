import UIKit
import WebKit

/// Opens ficbook pages in an ordinary WebKit view and reads them with shared/web/parse.js.
///
/// The view stays hidden while pages load. When ficbook shows its security check
/// or age confirmation, the page is shown so the person can answer it themselves;
/// reading resumes as soon as the story page comes back.
final class PageReader: NSObject, WKNavigationDelegate {
    private struct Job {
        let url: URL
        let kind: String
        let args: String
        let completion: (String) -> Void
    }

    private weak var host: UIViewController?
    private let webView: WKWebView
    private let overlay = UIView()
    private let titleLabel = UILabel()
    private let messageLabel = UILabel()
    private let cancelButton = UIButton(type: .system)
    private let continueButton = UIButton(type: .system)
    private var job: Job?
    private var timeout: Timer?
    private var labels: [String: String] = [:]
    #if DEBUG
    var debugScript: String?
    #endif

    init(host: UIViewController) {
        self.host = host
        let configuration = WKWebViewConfiguration()
        if let url = Bundle.main.url(forResource: "parse", withExtension: "js", subdirectory: "web"),
           let source = try? String(contentsOf: url, encoding: .utf8) {
            configuration.userContentController.addUserScript(
                WKUserScript(source: source, injectionTime: .atDocumentEnd, forMainFrameOnly: true)
            )
        }
        webView = WKWebView(frame: .zero, configuration: configuration)
        super.init()
        webView.navigationDelegate = self
        buildOverlay()
    }

    func read(url: URL, kind: String, args: [String: Any], labels: [String: String], completion: @escaping (String) -> Void) {
        finish(#"{"ok":false,"error":"cancelled"}"#)
        self.labels = labels
        let encoded = (try? JSONSerialization.data(withJSONObject: args)).flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
        job = Job(url: url, kind: kind, args: encoded, completion: completion)
        startTimeout()
        webView.load(URLRequest(url: url))
    }

    // MARK: - Navigation

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        evaluate()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        failed(error)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        failed(error)
    }

    private func failed(_ error: Error) {
        guard let job, overlay.isHidden else { return }
        if (error as NSError).code == NSURLErrorCancelled { return }
        finish(errorJSON("load_failed", url: job.url.absoluteString))
    }

    private func evaluate() {
        guard let job else { return }
        let kind = (try? JSONSerialization.data(withJSONObject: [job.kind])).flatMap { String(data: $0, encoding: .utf8) } ?? "[\"story\"]"
        var script = "JSON.stringify(window.FicbookParse ? FicbookParse.run(\(kind)[0], \(job.args)) : {ok:false,error:'script_error'})"
        #if DEBUG
        if let debugScript { script = debugScript }
        #endif
        webView.evaluateJavaScript(script) { [weak self] value, _ in
            guard let self, self.job != nil else { return }
            let json = value as? String ?? #"{"ok":false,"error":"script_error"}"#
            switch Self.errorCode(json) {
            case "security_check": self.showOverlay(message: self.labels["check"])
            case "age_check": self.showOverlay(message: self.labels["age"])
            default: self.finish(json)
            }
        }
    }

    private func finish(_ json: String) {
        timeout?.invalidate()
        timeout = nil
        overlay.isHidden = true
        guard let job else { return }
        self.job = nil
        job.completion(json)
    }

    private func startTimeout() {
        timeout?.invalidate()
        timeout = Timer.scheduledTimer(withTimeInterval: 45, repeats: false) { [weak self] _ in
            guard let self, let job = self.job, self.overlay.isHidden else { return }
            self.webView.stopLoading()
            self.finish(self.errorJSON("load_failed", url: job.url.absoluteString))
        }
    }

    // MARK: - Check overlay

    private func buildOverlay() {
        guard let host else { return }
        overlay.backgroundColor = Palette.card
        overlay.isHidden = true
        overlay.translatesAutoresizingMaskIntoConstraints = false
        host.view.addSubview(overlay)

        titleLabel.font = .systemFont(ofSize: 17, weight: .bold)
        titleLabel.textColor = Palette.ink
        messageLabel.font = .systemFont(ofSize: 15)
        messageLabel.textColor = Palette.muted
        messageLabel.numberOfLines = 0
        cancelButton.titleLabel?.font = .systemFont(ofSize: 16, weight: .semibold)
        cancelButton.tintColor = Palette.accent
        cancelButton.addAction(UIAction { [weak self] _ in self?.finish(#"{"ok":false,"error":"cancelled"}"#) }, for: .touchUpInside)
        continueButton.titleLabel?.font = .systemFont(ofSize: 16, weight: .bold)
        continueButton.tintColor = Palette.accent
        continueButton.addAction(UIAction { [weak self] _ in self?.retry() }, for: .touchUpInside)

        let buttons = UIStackView(arrangedSubviews: [cancelButton, UIView(), continueButton])
        let header = UIStackView(arrangedSubviews: [buttons, titleLabel, messageLabel])
        header.axis = .vertical
        header.spacing = 6
        header.isLayoutMarginsRelativeArrangement = true
        header.directionalLayoutMargins = NSDirectionalEdgeInsets(top: 8, leading: 16, bottom: 12, trailing: 16)
        let rule = UIView()
        rule.backgroundColor = Palette.line
        [header, rule, webView].forEach {
            $0.translatesAutoresizingMaskIntoConstraints = false
            overlay.addSubview($0)
        }
        NSLayoutConstraint.activate([
            overlay.topAnchor.constraint(equalTo: host.view.topAnchor),
            overlay.bottomAnchor.constraint(equalTo: host.view.bottomAnchor),
            overlay.leadingAnchor.constraint(equalTo: host.view.leadingAnchor),
            overlay.trailingAnchor.constraint(equalTo: host.view.trailingAnchor),
            header.topAnchor.constraint(equalTo: overlay.safeAreaLayoutGuide.topAnchor),
            header.leadingAnchor.constraint(equalTo: overlay.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: overlay.trailingAnchor),
            rule.topAnchor.constraint(equalTo: header.bottomAnchor),
            rule.leadingAnchor.constraint(equalTo: overlay.leadingAnchor),
            rule.trailingAnchor.constraint(equalTo: overlay.trailingAnchor),
            rule.heightAnchor.constraint(equalToConstant: 1),
            webView.topAnchor.constraint(equalTo: rule.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: overlay.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: overlay.trailingAnchor),
            webView.bottomAnchor.constraint(equalTo: overlay.bottomAnchor),
        ])
    }

    private func showOverlay(message: String?) {
        timeout?.invalidate()
        titleLabel.text = labels["title"]
        messageLabel.text = message
        cancelButton.setTitle(labels["cancel"], for: .normal)
        continueButton.setTitle(labels["continue"], for: .normal)
        if let host, overlay.superview == host.view { host.view.bringSubviewToFront(overlay) }
        overlay.isHidden = false
    }

    private func retry() {
        guard let job else { return }
        webView.load(URLRequest(url: job.url))
    }

    // MARK: - JSON

    private func errorJSON(_ code: String, url: String) -> String {
        let result: [String: Any] = ["ok": false, "error": code, "params": ["url": url]]
        return (try? JSONSerialization.data(withJSONObject: result)).flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
    }

    private static func errorCode(_ json: String) -> String? {
        guard
            let data = json.data(using: .utf8),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            object["ok"] as? Bool == false
        else { return nil }
        return object["error"] as? String
    }
}
