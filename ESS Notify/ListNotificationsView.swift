//
//  ListNotificationsView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-25.
//

import SwiftUI

struct ListNotificationsView: View {
    @State var noteList = notifications
    @Binding var listView: Int
    @Binding var noteURL: String
    @State private var currentTime = Date()
    
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
                }.onDelete{ indexSet in DispatchQueue.main.asyncAfter(deadline: .now()) {
                    deleteNotifications(offsets: indexSet)
                    noteList = notifications
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        getNotificationsList()
                    }
                }
            }.environment(\.defaultMinListRowHeight, 20)
            Spacer()
            HStack {
                Button(action: {
                    getNotificationsList()
                }){Image(systemName: "arrow.clockwise")}.frame(minWidth: 0, maxWidth: .infinity)
                .padding()
                .background(cellColor)
                .foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
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
        }
        .onReceive(timer) { newTime in
            if newTime.timeIntervalSince(currentTime) > 2 {
                getNotificationsList()
            }
            noteList=notifications
            currentTime = newTime
        }

    }
}
