
//
//  ios14_demoApp.swift
//  ios14-demo
//
//  Created by Prafulla Singh on 23/6/20.
//
import SwiftUI

@main
struct ESS_Notify: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject var notificationCenter = NotificationCenter()
    
    var body: some Scene {
        WindowGroup {
            SplashView(notificationCenter: notificationCenter)
        }
    }
}
