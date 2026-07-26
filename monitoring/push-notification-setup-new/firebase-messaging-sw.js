importScripts(
  "https://www.gstatic.com/firebasejs/12.15.0/firebase-app-compat.js"
);

importScripts(
  "https://www.gstatic.com/firebasejs/12.15.0/firebase-messaging-compat.js"
);


firebase.initializeApp({

apiKey: "AIzaSyChfmEBP90TuAQ9sPk3swL-ZTm8GIuCycI",
authDomain: "push-notification-demo-f0cc4.firebaseapp.com",
projectId: "push-notification-demo-f0cc4",
storageBucket: "push-notification-demo-f0cc4.firebasestorage.app",
messagingSenderId: "302607376382",
appId: "1:302607376382:web:672ffe6216a3388a076aaf"

});


const messaging = firebase.messaging();


messaging.onBackgroundMessage((payload) => {

  console.log("Background message:", payload);

  const title =
    payload.notification?.title ||
    payload.data?.title ||
    "New Notification";

  const options = {
    body:
      payload.notification?.body ||
      payload.data?.body ||
      "You have a new notification.",
    icon:
      payload.notification?.icon ||
      "/firebase-logo.png",
    data: {
      url: payload.data?.url || "/",
    },
  };

  self.registration.showNotification(title, options);

});
self.addEventListener("notificationclick", (event) => {

  event.notification.close();

  const urlToOpen = event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({
      type: "window",
      includeUncontrolled: true,
    }).then((clientList) => {

      for (const client of clientList) {
        if (client.url === urlToOpen && "focus" in client) {
          return client.focus();
        }
      }

      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }

    })
  );

});
