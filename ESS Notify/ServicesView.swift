//
//  ServicesView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-26.
//

import SwiftUI

struct ServicesView: View {
    @Binding var listView: Int
    @State var serviceList = services
    
    var body: some View {
        VStack {
            Text("Available Notification Services")
            .font(.footnote)
            .frame(minWidth: 0, maxWidth: .infinity)
            .padding()
            .background(cellColor)
            List{
                ForEach(0..<serviceList.count, id: \.self) { i in
                    Button(action: {
                        serviceList[i].Subscribed.toggle()
                        services[i].Subscribed.toggle()
                    })
                    {
                        HStack {
                            if serviceList[i].Subscribed {
                                Image(systemName: "checkmark.seal.fill")
                            }
                            else {
                                Image(systemName: "square")
                            }
                            Spacer()
                            Text(serviceList[i].Category)
                            Spacer()
                        }
                    }.listRowBackground(Color(hex: serviceList[i].Color))
                }
            }
            Spacer()
            Button(action: { sendServicesToServer()
                    withAnimation(.easeOut(duration: 0.3)) {listView = 0 }}){
                HStack{
                    Image(systemName: "text.badge.checkmark")
                    Text("Save")
                }
            }.frame(minWidth: 0, maxWidth: .infinity)
            .padding()
            .background(cellColor)
            .foregroundColor(Color.white)
            .font(.footnote)
        }.onAppear() {
            getServicesList()
            serviceList = services
        }
    }
}
