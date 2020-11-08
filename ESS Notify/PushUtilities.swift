//
//  PushUtilities.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-24.
//

import Foundation
import UserNotifications
import SwiftUI

class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
      let tokenParts = deviceToken.map { data in String(format: "%02.2hhx", data) }
        userData.APNToken = tokenParts.joined()
    }
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error ) {
      print("Failed to register: \(error)")
    }
}

func registerForPushNotifications() {
    UNUserNotificationCenter.current()
        .requestAuthorization(
            options: [.alert, .badge, .sound]) { success, _ in
            guard success else { return }
            getNotificationSettings()
    }
}

class NotificationCenter: NSObject, ObservableObject, UNUserNotificationCenterDelegate {
    override init() {
        super.init()
        UNUserNotificationCenter.current().delegate = self
    }
}
extension NotificationCenter {
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        handlePush(pushData: notification)
        completionHandler(.banner)
    }
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        handlePush(pushData: response.notification)
        completionHandler()
    }
    func userNotificationCenter(_ center: UNUserNotificationCenter, openSettingsFor notification: UNNotification?) {}
}

func handlePush (pushData: UNNotification) {
    getNotificationsList()
//    UIApplication.shared.applicationIconBadgeNumber = 15
//    print(pushData.request.content)
//    print(pushData.request.content.title)
//    print(pushData.request.content.subtitle)
//    print(pushData.request.content.body)
//    print(pushData.request.content.badge)
//    print(pushData.request.content.summaryArgument)
//    print(pushData.request.content.categoryIdentifier)
//    UIApplication.shared.applicationIconBadgeNumber=0
//    print(pushData.request.content.userInfo) // All the data are here
}

func requestGrantForLocalNetwork() {
    // this is a workaround because it doesn't exists yet an API for this request
    print(ProcessInfo.processInfo.hostName)
}

func getNotificationSettings() {
  UNUserNotificationCenter.current().getNotificationSettings { settings in
    print("Notification settings: \(settings)")
    guard settings.authorizationStatus == .authorized else { return }
    DispatchQueue.main.async {
      UIApplication.shared.registerForRemoteNotifications()
    }
  }
}
