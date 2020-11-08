//
//  ListNotificationsView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-25.
//

import SwiftUI
import SwiftUIRefresh

struct ListNotificationsView: View {
    @State var noteList = notifications
    @Binding var listView: Int
    @Binding var noteURL: String
    @State private var currentTime = Date()
    @State private var readAll = false
    @State private var deleteAll = false
    @State private var currentColor = "any"
    @State private var isShowing = false
    
    let timer = Timer.publish(every: 1, on: .main, in: .default).autoconnect()

    var body: some View {
        VStack {
            Text("ESS Notify")
                .font(.footnote)
                .frame(minWidth: 0, maxWidth: .infinity)
                .padding()
                .background(cellColor)
            List{
                ForEach(0..<noteList.count, id: \.self) { i in
                    if notifications[i].Color == currentColor || currentColor == "any" {
                        Button(action: {
                            withAnimation(.easeOut(duration: 0.3)) {
                                notifications[i].Read = true
                                sendNotificationsToServer()
                                self.noteURL = noteList[i].URL
                                self.listView = 1
                            }
                        })
                        {
                            VStack{
                                HStack{
                                    if !noteList[i].Read {
                                        HStack {
                                            Image(systemName: "circlebadge.fill").foregroundColor(Color.red)
                                            Text("New").font(.footnote)
                                        }
                                    }
                                    Spacer()
                                    Text(noteList[i].Timestamp).font(.footnote)
                                }
                                Text(noteList[i].Title)
                                Text(noteList[i].Subtitle)
                            }
                        }.listRowBackground(Color(hex: noteList[i].Color))
                        if i<noteList.count-1 {
                            Divider().listRowBackground(bgColor).deleteDisabled(true)
                        }
                    }
                }.onDelete{ indexSet in DispatchQueue.main.asyncAfter(deadline: .now()) {
                    deleteNotifications(offsets: indexSet)
                    noteList = notifications
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        getNotificationsList()
                        setCurrentColors()
                    }
                }
            }.environment(\.defaultMinListRowHeight, 20)
            .pullToRefresh(isShowing: $isShowing) {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    getNotificationsList()
                    setCurrentColors()
                    noteList=notifications
                    isShowing = false
                    if noteList.count == 0 {
                        listView = 2
                        listView = 0
                    }
                }
            }
            Spacer()
            HStack {
                HStack {
                    Menu {
                        Picker(selection: $currentColor, label: Text("")) {
                            ForEach(notificationsColors.sorted(by: >), id: \.key) { key, value in
                                Text(value).tag(key)
                            }
                            Text("All").tag("any")
                        }
                    } label: {
                        Label("", systemImage: "line.horizontal.3.decrease.circle.fill")
                            .padding()
                            .background(cellColor)
                            .foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
                    }
                    Button(action: {
                        if notifications.count > 0 {
                            readAll = true
                        }
                    }){Image(systemName: "envelope.open.fill")}.frame(minWidth: 0, maxWidth: .infinity)
                    .padding()
                    .background(cellColor)
                    .foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
                    .alert(isPresented: $readAll) { () -> Alert in
                        let readAllButton = Alert.Button.default(Text("Mark as Read")) {
                            readBulkNotifications(color: currentColor)
                            noteList=notifications
                            readAll = false
                        }
                        return Alert(title: Text("Read All"), message: Text("Do you want to mark the current messages as read?"), primaryButton: readAllButton, secondaryButton: Alert.Button.cancel(Text("Cancel")){ readAll = false })
                    }
                    Button(action: {
                        if notifications.count > 0 {
                            deleteAll = true
                        }
                    }){Image(systemName: "trash.fill")}.frame(minWidth: 0, maxWidth: .infinity)
                    .padding()
                    .background(cellColor)
                    .foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
                    .alert(isPresented: $deleteAll) { () -> Alert in
                        let readAllButton = Alert.Button.default(Text("Delete All")) {
                            deleteBulkNotifications(color: currentColor)
                            setCurrentColors()
                            noteList=notifications
                            deleteAll = false
                        }
                        return Alert(title: Text("Delete All"), message: Text("Do you want to delete the current messages?"), primaryButton: readAllButton, secondaryButton: Alert.Button.cancel(Text("Cancel")){ deleteAll = false })
                    }
                }
                Button(action: {
                        withAnimation(.easeOut(duration: 0.3)) {self.listView = 2}
                }){Image(systemName: "gearshape.2.fill")
                }.frame(minWidth: 0, maxWidth: .infinity)
                    .padding()
                    .background(cellColor)
                    .foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
            }
        }
        .onAppear() {
            UITableView.appearance().backgroundColor = .clear
            getNotificationsList()
            setCurrentColors()
        }
        .onReceive(timer) { newTime in
            if newTime.timeIntervalSince(currentTime) > 2 {
                getNotificationsList()
                setCurrentColors()
            }
            setCurrentColors()
            noteList=notifications
            currentTime = newTime
        }

    }
}
