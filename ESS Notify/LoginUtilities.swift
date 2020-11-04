//
//  AuthUtilities.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-24.
//

import Foundation

struct UserData: Codable {
    var APNToken: String
    var ESSUser: String
    var ESSToken: String
    var Registered: Bool
}

var userData = UserData(APNToken: "", ESSUser: "", ESSToken: "", Registered: false)

func sendAuthToServer(server: String) -> Bool
{
    do {
        let jsonData = try JSONEncoder().encode(userData)
        let url = URL(string: server)!
        let semaphore = DispatchSemaphore(value: 0)
        var request = URLRequest(url: url)
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.addValue("application/json", forHTTPHeaderField: "Accept")
        request.httpMethod = "POST"
        request.httpBody = jsonData
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data, error == nil else {
                print(error?.localizedDescription ?? "No data")
                semaphore.signal()
                return
            }
            let responseJSON = try? JSONSerialization.jsonObject(with: data, options: [])
            if let responseJSON = responseJSON as? [String: Any] {
                userData.ESSUser = responseJSON["ESSUser"] as? String ?? ""
                userData.ESSToken = responseJSON["ESSToken"] as? String ?? ""
                userData.Registered = responseJSON["Registered"] as? Bool ?? false
                semaphore.signal()
            }
            else {
                semaphore.signal()
            }
        }
        task.resume()
        semaphore.wait()
    }
    catch { }
    if userData.Registered {
        return true
    }
    else {
        return false
    }
}

func loadCredentials() {
    DispatchQueue.main.async {
        do {
            let paths = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)
            let url = paths[0].appendingPathComponent("credentials")
            let data = try Data(contentsOf: url)
            userData = try JSONDecoder().decode(UserData.self, from: data)
        } catch {
            // do nothing
        }
    }
}

func saveCredentials() {
    do {
        let data = try JSONEncoder().encode(userData)
        let paths = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)
        let url = paths[0].appendingPathComponent("credentials")
        try data.write(to: url)
    }
    catch {
            print("Save failed")
        }
    }

func verifyCredentials(username: String, password: String) -> Bool {
    userData.ESSUser = username
    userData.ESSToken = password
    let isValid = sendAuthToServer(server: authServer)
    if isValid {
        saveCredentials()
        return true
    }
    return false
}
