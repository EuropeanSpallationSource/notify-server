//
//  LoginView.swift
//  ESS Notify
//
//  Created by Emanuele Laface on 2020-10-22.
//

import SwiftUI

struct LoginView: View {
    @State private var username = ""
    @State private var password = ""
    @State private var isLogged: Bool = false
    @State private var errorLogin: Bool = false
    
    var body: some View {
        bgColor.overlay(
            VStack {
                if self.isLogged {
                    NotificationsView()
                }
                else {
                    Spacer()
                    Image("ess-logo").padding(.all, -25.0)
                    Spacer()
                    TextField("ESS Username", text: $username).padding().font(/*@START_MENU_TOKEN@*/.title2/*@END_MENU_TOKEN@*/).multilineTextAlignment(/*@START_MENU_TOKEN@*/.center/*@END_MENU_TOKEN@*/).background(bgColor).border(cellColor, width: 10).cornerRadius(/*@START_MENU_TOKEN@*/30.0/*@END_MENU_TOKEN@*/).foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
                    Spacer()
                    SecureField("ESS Password", text: $password).padding().font(/*@START_MENU_TOKEN@*/.title2/*@END_MENU_TOKEN@*/).multilineTextAlignment(/*@START_MENU_TOKEN@*/.center/*@END_MENU_TOKEN@*/).background(bgColor).border(cellColor, width: 10).cornerRadius(/*@START_MENU_TOKEN@*/30.0/*@END_MENU_TOKEN@*/).foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
                    Spacer()
                    Button("Login") {
                        if verifyCredentials(username: username, password: password) {
                            self.isLogged = true
                        }
                        else {
                            self.errorLogin = true
                        }
                    }
                    .frame(minWidth: 0, maxWidth: .infinity)
                    .padding()
                    .background(cellColor).border(cellColor, width: 10)
                    .cornerRadius(/*@START_MENU_TOKEN@*/30.0/*@END_MENU_TOKEN@*/)
                    .foregroundColor(/*@START_MENU_TOKEN@*/.white/*@END_MENU_TOKEN@*/)
                    .alert(isPresented: $errorLogin) {
                        Alert(title: Text("Error"), message: Text("Wrong Username or Password"), dismissButton: .default(Text("Try Again")))
                    }
                    Spacer()
                }
            }
        )
    }
}
struct LoginView_Previews: PreviewProvider {
    static var previews: some View {
        LoginView()
    }
}
