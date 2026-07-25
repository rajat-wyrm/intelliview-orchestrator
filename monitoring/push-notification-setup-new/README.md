# 🔔 Firebase Push Notification Setup (FCM)

A web-based push notification system using *Firebase Cloud Messaging (FCM)* to deliver real-time browser notifications even when the application is not actively open.

## 🚀 Features

- Firebase Cloud Messaging integration
- Browser notification permission handling
- FCM token generation
- Service Worker support
- Push notification sending using Firebase Admin SDK

## 🛠️ Tech Stack

- JavaScript
- Node.js
- Vite
- Firebase Web SDK
- Firebase Admin SDK

## 📂 Project Structure


push-notification-setup/
│
├── index.html
├── app.js
├── firebase-messaging-sw.js
├── send.cjs
├── package.json
└── README.md


## ⚙️ Setup

Install dependencies:

bash
npm install


Run project:

bash
npm run dev


Open the localhost URL, allow notifications, and generate the FCM token.

## 🔑 Firebase Admin Service Account Setup

The `send.cjs` script requires a Firebase Admin Service Account key.

### Steps

1. Open the Firebase Console.
2. Select your project.
3. Go to **Project Settings → Service Accounts**.
4. Click **Generate New Private Key**.
5. Download the JSON file.
6. Rename it to `serviceAccountKey.json`.
7. Place it in the project root (the same folder as `send.cjs`).

> **Important**
>
> - Never commit `serviceAccountKey.json` to GitHub.
> - It is ignored by `.gitignore`.
> - `serviceAccountKey.example.json` is provided only as a template.

## 📩 Send Notification

Run:

bash
node send.cjs


Successful response:

json
{
  "fcm_status": "success",
  "message_id": "projects/xxx/messages/yyy"
}


## 🔐 Security

Sensitive files like:


serviceAccountKey.json
node_modules/


are excluded using .gitignore.

## 👩‍💻 Author

Gungun Jain
