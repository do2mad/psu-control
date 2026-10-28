#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Nachgebautes UDP3305S-E im Netzwerk (SCPI ueber TCP, Port 5025).

Zum Testen der iOS-/Mac-App ohne echtes Netzteil: auf dem Mac starten,
dann in der App die IP des Macs eintragen (oder "Netzwerk durchsuchen").

    python3 tools/fake_device.py              # lauscht auf allen Schnittstellen, Port 5025
    python3 tools/fake_device.py --port 5026  # anderer Port
    python3 tools/fake_device.py -v           # jeden Befehl anzeigen
"""
import argparse
import os
import socketserver
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mac"))
from udp3305 import SimScpi  # noqa: E402

SIM = SimScpi()


class Handler(socketserver.StreamRequestHandler):
    verbose = False

    def handle(self):
        peer = "%s:%d" % self.client_address
        print("Verbunden:", peer)
        for raw in self.rfile:
            cmd = raw.decode("ascii", "replace").strip()
            if not cmd:
                continue
            want = "?" in cmd
            with SIM.lock:
                reply = SIM.query(cmd) if want else SIM.write(cmd)
            if self.verbose:
                print(f"{peer}  {cmd}" + (f"  ->  {reply}" if want else ""))
            if want:
                self.wfile.write(((reply or "") + "\n").encode())
        print("Getrennt:", peer)


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser(description="Simuliertes UDP3305S-E (SCPI/TCP)")
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5025)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    Handler.verbose = a.verbose
    with Server((a.bind, a.port), Handler) as srv:
        print(f"Simuliertes UDP3305S-E lauscht auf {a.bind}:{a.port}  (Ctrl+C beendet)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
