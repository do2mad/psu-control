// SPDX-License-Identifier: MIT
//
// WebView – zeigt die gemeinsame Oberflaeche (web/index.html) an und
// verbindet sie ueber ios-bridge.js mit der nativen Seite.

import SwiftUI
import WebKit

struct WebView: UIViewRepresentable {

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let controller = WKUserContentController()
        if let url = Self.resource("ios-bridge", "js"), let js = try? String(contentsOf: url, encoding: .utf8) {
            controller.addUserScript(WKUserScript(source: js, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
        controller.addScriptMessageHandler(context.coordinator.bridge, contentWorld: .page, name: "native")

        let config = WKWebViewConfiguration()
        config.userContentController = controller
        config.allowsInlineMediaPlayback = true

        let webView = WKWebView(frame: .zero, configuration: config)
        let bg = UIColor(red: 0x2b / 255.0, green: 0x2d / 255.0, blue: 0x31 / 255.0, alpha: 1)
        webView.isOpaque = false
        webView.backgroundColor = bg
        webView.scrollView.backgroundColor = bg
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.uiDelegate = context.coordinator
        if #available(iOS 16.4, *) {
            webView.isInspectable = true      // Safari > Entwickler > Geraet: Oberflaeche debuggen
        }
        if let index = Self.resource("index", "html") {
            webView.loadFileURL(index, allowingReadAccessTo: index.deletingLastPathComponent())
        }
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    /// Sucht eine Datei im Ordner "web" des App-Bundles (oder direkt im Bundle).
    static func resource(_ name: String, _ ext: String) -> URL? {
        Bundle.main.url(forResource: name, withExtension: ext, subdirectory: "web")
            ?? Bundle.main.url(forResource: name, withExtension: ext)
    }

    final class Coordinator: NSObject, WKUIDelegate {
        let bridge = NativeBridge()

        private func presenter() -> UIViewController? {
            let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
            var vc = scene?.windows.first(where: { $0.isKeyWindow })?.rootViewController
            while let next = vc?.presentedViewController { vc = next }
            return vc
        }

        // alert()
        func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
            let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
            guard let p = presenter() else { completionHandler(); return }
            p.present(a, animated: true)
        }

        // confirm()
        func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
            let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "Abbrechen", style: .cancel) { _ in completionHandler(false) })
            a.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler(true) })
            guard let p = presenter() else { completionHandler(false); return }
            p.present(a, animated: true)
        }
    }
}
