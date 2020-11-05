//
//  NotificationsUtilities.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-24.
//

import Foundation
import SwiftUI

struct NotificationData: Identifiable, Codable {
    var id: Int
    var Timestamp: String
    var Color: String
    var Title: String
    var Subtitle: String
    var URL: String
    var Read: Bool
}

var notificationData = NotificationData(id: 0, Timestamp: "", Color: "", Title: "", Subtitle: "", URL: "", Read: false)

var notifications = [NotificationData]()

func getNotificationsList() {
    notifications = [NotificationData]()
    DispatchQueue.main.async {
        UIApplication.shared.applicationIconBadgeNumber = 0
    }
    let rnd = Int.random(in: 1..<1000000)
    let server = notificationsBaseServer+"/"+userData.ESSUser+"/"+userData.ESSToken+"/notifications.json?\(rnd)"
    guard let url = URL(string: server) else {
            return
        }
    let semaphore = DispatchSemaphore(value: 0)
    let request = URLRequest(url: url)
    let task = URLSession.shared.dataTask(with: request, completionHandler: { (data, response, error) -> Void in
        if let error = error {
            print(error)
            semaphore.signal()
            return
        }
        if let data = data {
            do {
                let jsonResult = try JSONSerialization.jsonObject(with: data, options: JSONSerialization.ReadingOptions.mutableContainers) as? NSDictionary
                let jsonNotifications = jsonResult?[userData.ESSUser] as! [AnyObject]
                for jsonNotification in jsonNotifications {
                    notificationData.id = jsonNotification["id"] as! Int
                    notificationData.Timestamp = jsonNotification["Timestamp"] as! String
                    notificationData.Color = jsonNotification["Color"] as! String
                    notificationData.Title = jsonNotification["Title"] as! String
                    notificationData.Subtitle = jsonNotification["Subtitle"] as! String
                    notificationData.URL = jsonNotification["URL"] as! String
                    notificationData.Read = jsonNotification["Read"] as! Bool
                    if !notificationData.Read {
                        DispatchQueue.main.async {
                            UIApplication.shared.applicationIconBadgeNumber += 1
                        }
                    }
                    notifications.append(notificationData)
                }
                semaphore.signal()
            }
            catch {
                print(error)
            }
        }
    })
        task.resume()
        semaphore.wait()
}

func deleteNotifications(offsets: IndexSet) {
    withAnimation {
        notifications.remove(atOffsets: offsets)
    }
    sendNotificationsToServer()
}

func sendNotificationsToServer()
{
    struct DataToSend: Codable {
        var user: String
        var notifications: [NotificationData]
    }
    do {
        let dataToSend = DataToSend(user: userData.ESSUser, notifications: notifications)
        let jsonData = try JSONEncoder().encode(dataToSend)
        let url = URL(string: notificationsUpdateServer)!
        var request = URLRequest(url: url)
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.addValue("application/json", forHTTPHeaderField: "Accept")
        request.httpMethod = "POST"
        request.httpBody = jsonData
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data, error == nil else {
                print(error?.localizedDescription ?? "No data")
                return
            }
            let responseJSON = try? JSONSerialization.jsonObject(with: data, options: [])
            if let responseJSON = responseJSON as? [String: Any] {
                print(responseJSON)
            }
            else {
            }
        }
        task.resume()
    }
    catch {}
}
