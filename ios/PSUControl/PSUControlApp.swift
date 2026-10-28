// SPDX-License-Identifier: MIT
//
// PSU Control – Steuerung fuer das Labornetzteil UNI-T UDP3305S-E ueber LAN (SCPI, Port 5025).

import SwiftUI

@main
struct PSUControlApp: App {
    var body: some Scene {
        WindowGroup {
            WebView()
                .background(Color(red: 0x2b / 255.0, green: 0x2d / 255.0, blue: 0x31 / 255.0))
                .ignoresSafeArea(.container, edges: .bottom)
                .preferredColorScheme(.dark)
        }
    }
}
