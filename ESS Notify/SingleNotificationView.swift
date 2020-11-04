//
//  SingleNotificationView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-25.
//

import SwiftUI
import WebKit

struct SingleNotificationView: View {
    @Binding var listView: Int
    @Binding var noteURL: String

    var body: some View {
        VStack {
            Button(action: {withAnimation(.easeOut(duration: 0.3)) {listView = 0 }}){
                HStack{
                    Image(systemName: "arrowshape.turn.up.backward.fill")
                    Text("Back")
                    Spacer()
                }
            }.frame(minWidth: 0, maxWidth: .infinity)
            .padding()
            .background(cellColor)
            .foregroundColor(Color.white)
            .font(.footnote)
            Spacer()
            WebView(request: URLRequest(url: URL(string: noteURL) ?? URL(string: "http://www.blank.com/")!))
        }
    }
}

struct WebView: UIViewRepresentable {
    let request: URLRequest
    
    func makeUIView(context: Context) -> WKWebView {
        return WKWebView()
    }
    
    func updateUIView(_ uiView: WKWebView, context: Context){
        uiView.load(request)
    }
}
