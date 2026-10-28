// SPDX-License-Identifier: MIT
//
// LineSocket – einfache, blockierende TCP-Verbindung fuer SCPI.
// Befehle werden mit "\n" abgeschlossen, Antworten zeilenweise gelesen.
// Wird nur von einem seriellen DispatchQueue aus benutzt (siehe NativeBridge).

import Foundation
import Darwin

enum SocketError: LocalizedError {
    case resolve(String)
    case connect(String)
    case timeout
    case closed
    case notConnected
    case io(String)

    var errorDescription: String? {
        switch self {
        case .resolve(let h): return "Adresse \(h) unbekannt"
        case .connect(let m): return "Verbindung fehlgeschlagen: \(m)"
        case .timeout: return "Zeitüberschreitung"
        case .closed: return "Verbindung vom Gerät geschlossen"
        case .notConnected: return "nicht verbunden"
        case .io(let m): return m
        }
    }
}

final class LineSocket {
    let host: String
    let port: UInt16
    let timeout: TimeInterval
    private var fd: Int32 = -1
    private var buffer: [UInt8] = []

    init(host: String, port: UInt16, timeout: TimeInterval = 2.5) {
        self.host = host
        self.port = port
        self.timeout = timeout
    }

    deinit { close() }

    var isOpen: Bool { fd >= 0 }

    func open() throws {
        close()
        var hints = addrinfo()
        hints.ai_family = AF_INET
        hints.ai_socktype = SOCK_STREAM
        hints.ai_protocol = IPPROTO_TCP
        var result: UnsafeMutablePointer<addrinfo>?
        guard getaddrinfo(host, String(port), &hints, &result) == 0, let info = result else {
            throw SocketError.resolve(host)
        }
        defer { freeaddrinfo(result) }

        let s = socket(info.pointee.ai_family, info.pointee.ai_socktype, info.pointee.ai_protocol)
        guard s >= 0 else { throw SocketError.io("socket() fehlgeschlagen") }
        var one: Int32 = 1
        setsockopt(s, SOL_SOCKET, SO_NOSIGPIPE, &one, socklen_t(MemoryLayout<Int32>.size))
        setsockopt(s, Int32(IPPROTO_TCP), TCP_NODELAY, &one, socklen_t(MemoryLayout<Int32>.size))

        // Nicht blockierend verbinden, damit wir eine Zeitgrenze setzen koennen
        let flags = fcntl(s, F_GETFL, 0)
        _ = fcntl(s, F_SETFL, flags | O_NONBLOCK)
        let rc = Darwin.connect(s, info.pointee.ai_addr, info.pointee.ai_addrlen)
        if rc != 0 {
            guard errno == EINPROGRESS else {
                let msg = String(cString: strerror(errno))
                Darwin.close(s)
                throw SocketError.connect(msg)
            }
            var pfd = pollfd(fd: s, events: Int16(POLLOUT), revents: 0)
            let pr = poll(&pfd, 1, Int32(timeout * 1000))
            if pr <= 0 {
                Darwin.close(s)
                throw SocketError.timeout
            }
            var err: Int32 = 0
            var len = socklen_t(MemoryLayout<Int32>.size)
            getsockopt(s, SOL_SOCKET, SO_ERROR, &err, &len)
            if err != 0 {
                Darwin.close(s)
                throw SocketError.connect(String(cString: strerror(err)))
            }
        }
        _ = fcntl(s, F_SETFL, flags)   // wieder blockierend
        fd = s
        buffer.removeAll()
    }

    func close() {
        if fd >= 0 {
            Darwin.close(fd)
            fd = -1
        }
        buffer.removeAll()
    }

    /// Verwirft unerwartet anstehende Daten, damit Abfrage und Antwort zusammenpassen.
    func drain() throws {
        guard isOpen else { throw SocketError.notConnected }
        buffer.removeAll()
        var tmp = [UInt8](repeating: 0, count: 4096)
        while true {
            var pfd = pollfd(fd: fd, events: Int16(POLLIN), revents: 0)
            if poll(&pfd, 1, 0) <= 0 { return }
            let n = recv(fd, &tmp, tmp.count, 0)
            if n <= 0 {
                close()
                throw SocketError.closed
            }
        }
    }

    func send(_ line: String) throws {
        guard isOpen else { throw SocketError.notConnected }
        let bytes = Array((line + "\n").utf8)
        var offset = 0
        while offset < bytes.count {
            let n = bytes.withUnsafeBytes { raw -> Int in
                Darwin.send(fd, raw.baseAddress! + offset, bytes.count - offset, 0)
            }
            if n <= 0 {
                close()
                throw SocketError.io("Senden fehlgeschlagen")
            }
            offset += n
        }
    }

    func readLine() throws -> String {
        guard isOpen else { throw SocketError.notConnected }
        let deadline = Date().addingTimeInterval(timeout)
        var tmp = [UInt8](repeating: 0, count: 4096)
        while true {
            if let nl = buffer.firstIndex(of: 10) {
                let line = Array(buffer[..<nl])
                buffer.removeSubrange(...nl)
                return String(decoding: line, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
            }
            let remaining = deadline.timeIntervalSinceNow
            if remaining <= 0 {
                close()
                throw SocketError.timeout
            }
            var pfd = pollfd(fd: fd, events: Int16(POLLIN), revents: 0)
            if poll(&pfd, 1, Int32(remaining * 1000)) <= 0 {
                close()
                throw SocketError.timeout
            }
            let n = recv(fd, &tmp, tmp.count, 0)
            if n <= 0 {
                close()
                throw SocketError.closed
            }
            buffer.append(contentsOf: tmp[0..<n])
        }
    }

    func query(_ cmd: String) throws -> String {
        try drain()
        try send(cmd)
        return try readLine()
    }

    func write(_ cmd: String) throws {
        try drain()
        try send(cmd)
    }
}
