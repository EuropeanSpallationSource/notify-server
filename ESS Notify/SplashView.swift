//
//  SplashView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-23.
//

import SwiftUI

struct SplashView: View {
    @State private var isLoaded: Bool = false
    @ObservedObject var notificationCenter: NotificationCenter

    var body: some View {
        bgColor.overlay(
            VStack {
                if self.isLoaded {
                    if userData.Registered {
                        NotificationsView()
                    }
                    else {
                        LoginView()
                    }
                }
                else {
                    Image("ess-logo")
                }
            }
        ).onAppear() {
            DispatchQueue.main.asyncAfter(deadline: .now()) {
                loadCredentials()
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                if userData.Registered {
                    userData.Registered = verifyCredentials(username: userData.ESSUser, password: userData.ESSToken)
                }
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                registerForPushNotifications()
                requestGrantForLocalNetwork()
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                withAnimation {
                    self.isLoaded = true
                }
            }
        }
    }
}
