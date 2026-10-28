// SPDX-License-Identifier: MIT
//
// NativeBridge – Gegenstueck zu web/ios-bridge.js.
// JavaScript ruft window.webkit.messageHandlers.native.postMessage({op: ...}) auf und
// erhaelt die Antwort als Promise. Alle SCPI-Zugriffe laufen nacheinander ueber eine
// serielle Queue; die Netzwerksuche laeuft parallel dazu.

import Foundation
import WebKit

final class NativeBridge: NSObject, WKScriptMessageHandlerWithReply {

    private let scpiQueue = DispatchQueue(label: "psucontrol.scpi", qos: .userInitiated)
    private let scanQueue = DispatchQueue(label: "psucontrol.scan", qos: .userInitiated, attributes: .concurrent)
    private var socket: LineSocket?
    private static let configKey = "psucontrol.config"

    enum BridgeError: LocalizedError {
        case badRequest(String)
        var errorDescription: String? {
            switch self { case .badRequest(let m): return m }
        }
    }

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage,
                               replyHandler: @escaping (Any?, String?) -> Void) {
        guard let body = message.body as? [String: Any], let op = body["op"] as? String else {
            replyHandler(nil, "Ungültige Anfrage")
            return
        }
        let queue = ["scan", "probe", "localIPs"].contains(op) ? scanQueue : scpiQueue
        queue.async {
            do {
                let result = try self.handle(op: op, body: body)
                DispatchQueue.main.async { replyHandler(result, nil) }
            } catch {
                let text = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
                DispatchQueue.main.async { replyHandler(nil, text) }
            }
        }
    }

    private func port(_ body: [String: Any]) -> UInt16 {
        if let p = body["port"] as? Int, p > 0, p < 65536 { return UInt16(p) }
        if let p = body["port"] as? Double, p > 0, p < 65536 { return UInt16(p) }
        return 5025
    }

    private func string(_ body: [String: Any], _ key: String) throws -> String {
        guard let s = body[key] as? String, !s.isEmpty else { throw BridgeError.badRequest("\(key) fehlt") }
        return s
    }

    private func handle(op: String, body: [String: Any]) throws -> Any? {
        switch op {
        case "connect":
            socket?.close()
            let s = LineSocket(host: try string(body, "host"), port: port(body))
            try s.open()
            socket = s
            return true

        case "query":
            guard let s = socket, s.isOpen else { throw SocketError.notConnected }
            return try s.query(try string(body, "cmd"))

        case "write":
            guard let s = socket, s.isOpen else { throw SocketError.notConnected }
            try s.write(try string(body, "cmd"))
            return nil

        case "close":
            socket?.close()
            socket = nil
            return nil

        case "probe":
            return try NetworkScanner.probe(host: try string(body, "host"), port: port(body), timeout: 2.5)

        case "scan":
            return NetworkScanner.scan(port: port(body), skip: body["skip"] as? String ?? "")

        case "localIPs":
            return NetworkScanner.localIPv4()

        case "cfgGet":
            return UserDefaults.standard.string(forKey: Self.configKey)

        case "cfgSet":
            UserDefaults.standard.set(body["value"] as? String, forKey: Self.configKey)
            return nil

        default:
            throw BridgeError.badRequest("Unbekannte Operation \(op)")
        }
    }
}
