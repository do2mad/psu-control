// SPDX-License-Identifier: MIT
//
// NetworkScanner – findet Geraete mit offenem SCPI-Port im eigenen /24-Netz.
// Es werden viele nicht blockierende Verbindungsversuche gleichzeitig gestartet
// und per poll() ausgewertet. Danach fragt der Scanner jedes gefundene Geraet mit *IDN? ab.

import Foundation
import Darwin

enum NetworkScanner {

    /// IPv4-Adressen der aktiven WLAN-/Ethernet-Schnittstellen (ohne Loopback, Mobilfunk, VPN).
    static func localIPv4() -> [String] {
        var result: [String] = []
        var ifap: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifap) == 0, let first = ifap else { return [] }
        defer { freeifaddrs(ifap) }
        var ptr: UnsafeMutablePointer<ifaddrs>? = first
        while let p = ptr {
            defer { ptr = p.pointee.ifa_next }
            let flags = Int32(p.pointee.ifa_flags)
            guard let addr = p.pointee.ifa_addr,
                  addr.pointee.sa_family == UInt8(AF_INET),
                  (flags & IFF_UP) != 0, (flags & IFF_LOOPBACK) == 0 else { continue }
            let name = String(cString: p.pointee.ifa_name)
            guard name.hasPrefix("en") || name.hasPrefix("bridge") else { continue }
            var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            if getnameinfo(addr, socklen_t(addr.pointee.sa_len), &host, socklen_t(host.count),
                           nil, 0, NI_NUMERICHOST) == 0 {
                let ip = String(cString: host)
                if !ip.hasPrefix("169.254."), !result.contains(ip) { result.append(ip) }
            }
        }
        return result
    }

    /// Liefert die Hosts, auf denen `port` eine TCP-Verbindung annimmt.
    static func openHosts(_ hosts: [String], port: UInt16, timeoutMs: Int32 = 600) -> [String] {
        var open: [String] = []
        let chunkSize = 64
        var index = 0
        while index < hosts.count {
            let chunk = Array(hosts[index..<min(index + chunkSize, hosts.count)])
            index += chunkSize
            var pending: [(fd: Int32, host: String)] = []
            for h in chunk {
                var addr = sockaddr_in()
                addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
                addr.sin_family = sa_family_t(AF_INET)
                addr.sin_port = port.bigEndian
                guard inet_pton(AF_INET, h, &addr.sin_addr) == 1 else { continue }
                let s = socket(AF_INET, SOCK_STREAM, 0)
                guard s >= 0 else { continue }
                var one: Int32 = 1
                setsockopt(s, SOL_SOCKET, SO_NOSIGPIPE, &one, socklen_t(MemoryLayout<Int32>.size))
                _ = fcntl(s, F_SETFL, fcntl(s, F_GETFL, 0) | O_NONBLOCK)
                let rc = withUnsafePointer(to: &addr) {
                    $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                        Darwin.connect(s, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
                    }
                }
                if rc == 0 {
                    open.append(h)
                    Darwin.close(s)
                } else if errno == EINPROGRESS {
                    pending.append((s, h))
                } else {
                    Darwin.close(s)
                }
            }
            let deadline = Date().addingTimeInterval(Double(timeoutMs) / 1000)
            while !pending.isEmpty {
                let remaining = Int32(deadline.timeIntervalSinceNow * 1000)
                if remaining <= 0 { break }
                var pfds = pending.map { pollfd(fd: $0.fd, events: Int16(POLLOUT), revents: 0) }
                if poll(&pfds, nfds_t(pfds.count), remaining) <= 0 { break }
                var still: [(fd: Int32, host: String)] = []
                for (k, p) in pfds.enumerated() {
                    if p.revents == 0 {
                        still.append(pending[k])
                        continue
                    }
                    var err: Int32 = 0
                    var len = socklen_t(MemoryLayout<Int32>.size)
                    getsockopt(p.fd, SOL_SOCKET, SO_ERROR, &err, &len)
                    if err == 0 && (p.revents & Int16(POLLOUT)) != 0 { open.append(pending[k].host) }
                    Darwin.close(p.fd)
                }
                pending = still
            }
            for p in pending { Darwin.close(p.fd) }
        }
        return open
    }

    /// Fragt die Kennung (*IDN?) eines Geraets ab.
    static func probe(host: String, port: UInt16, timeout: TimeInterval = 1.5) throws -> String {
        let s = LineSocket(host: host, port: port, timeout: timeout)
        try s.open()
        defer { s.close() }
        return try s.query("*IDN?")
    }

    /// Durchsucht alle eigenen /24-Netze. `skip` wird nicht per *IDN? abgefragt
    /// (das ist das gerade verbundene Geraet).
    static func scan(port: UInt16, skip: String) -> [String: Any] {
        var networks: [String] = []
        var hosts: [String] = []
        for ip in localIPv4() {
            let parts = ip.split(separator: ".")
            guard parts.count == 4 else { continue }
            let prefix = parts[0..<3].joined(separator: ".")
            let net = prefix + ".0/24"
            if networks.contains(net) { continue }
            networks.append(net)
            for n in 1...254 {
                let h = "\(prefix).\(n)"
                if h != ip { hosts.append(h) }
            }
        }
        let open = openHosts(hosts, port: port)
        var found: [[String: Any]] = Array(repeating: [:], count: open.count)
        let lock = NSLock()
        DispatchQueue.concurrentPerform(iterations: open.count) { i in
            let h = open[i]
            var idn = ""
            if h != skip {
                idn = (try? probe(host: h, port: port)) ?? ""
                if idn.isEmpty { idn = "(antwortet nicht auf *IDN?)" }
            }
            let entry: [String: Any] = ["host": h, "port": Int(port), "idn": idn]
            lock.lock()
            found[i] = entry
            lock.unlock()
        }
        return ["networks": networks, "found": found]
    }
}
