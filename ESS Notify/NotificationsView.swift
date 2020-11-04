//
//  NotificationsView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-23.
//

import SwiftUI

struct NotificationsView: View {
    @State private var listView = 0
    @State private var noteURL = ""
    
    var body: some View {
        if listView == 0 {
            ListNotificationsView(listView: $listView, noteURL: $noteURL)
        }
        if listView == 1 {
            SingleNotificationView(listView: $listView, noteURL: $noteURL)
        }
        if listView == 2 {
            ServicesView(listView: $listView)
        }
    }
}

struct NotificationsView_Previews: PreviewProvider {
    static var previews: some View {
        NotificationsView()
    }
}
