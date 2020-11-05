//
//  ServicesUtilities.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-26.
//

import Foundation
import SwiftUI

struct ServiceData: Identifiable, Codable {
    var id: Int
    var Category: String
    var Color: String
    var Subscribed: Bool
}

var serviceData = ServiceData(id: 0, Category: "", Color: "", Subscribed: false)
var services = [ServiceData]()

func getServicesList() {
    services = [ServiceData]()
    
    let rnd = Int.random(in: 1..<1000000)
    let server = notificationsBaseServer+"/"+userData.ESSUser+"/"+userData.ESSToken+"/services.json?\(rnd)"
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
                let jsonNotifications = jsonResult?["services"] as! [AnyObject]
                for jsonNotification in jsonNotifications {
                    serviceData.id = jsonNotification["id"] as! Int
                    serviceData.Category = jsonNotification["Category"] as! String
                    serviceData.Color = jsonNotification["Color"] as! String
                    serviceData.Subscribed = jsonNotification["Subscribed"] as! Bool
                    services.append(serviceData)
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

func sendServicesToServer()
{
    struct DataToSend: Codable {
        var user: String
        var services: [ServiceData]
    }
    do {
        let dataToSend = DataToSend(user: userData.ESSUser, services: services)
        let jsonData = try JSONEncoder().encode(dataToSend)
        let url = URL(string: servicesUpdateServer)!
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
