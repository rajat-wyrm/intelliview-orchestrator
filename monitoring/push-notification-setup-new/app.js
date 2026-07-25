import { initializeApp } from "firebase/app";
import { getMessaging, getToken } from "firebase/messaging";
import { getFirestore, doc, setDoc } from "firebase/firestore";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyChfmEBP90TuAQ9sPk3swL-ZTm8GIuCycI",
  authDomain: "push-notification-demo-f0cc4.firebaseapp.com",
  projectId: "push-notification-demo-f0cc4",
  storageBucket: "push-notification-demo-f0cc4.firebasestorage.app",
  messagingSenderId: "302607376382",
  appId: "1:302607376382:web:672ffe6216a3388a076aaf"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const messaging = getMessaging(app);

const status = document.getElementById("status");

function updateStatus(message, color = "black") {
  status.textContent = message;
  status.style.color = color;
}

let registration = null;

async function saveToken(token) {
  await setDoc(
    doc(db, "tokens", token),
    {
      token,
      updatedAt: new Date().toISOString()
    },
    { merge: true }
  );
}

async function generateToken() {
  const token = await getToken(messaging, {
    vapidKey: "BNPrQKG2ZQcveLLZHRvC1G0R4L_NYrsb6vqzeStgy5qhAz_ih_RirWhC6Ae6jefqD94Uzr3DIevXxvQvwMFpGXU",
    serviceWorkerRegistration: registration
  });

  if (!token) {
    updateStatus("No token generated", "red");
    return;
  }

  await saveToken(token);

  updateStatus("Token generated & saved", "green");

  console.log(token);
}

// Enable Notifications button
document.getElementById("enable").addEventListener("click", async () => {

  try {

    const permission = await Notification.requestPermission();

    if (permission !== "granted") {
      updateStatus(
        "Permission denied. Enable notifications from browser settings.",
        "red"
      );
      return;
    }

    updateStatus("Permission granted", "green");

    registration = await navigator.serviceWorker.register(
      "/firebase-messaging-sw.js",
      { scope: "/" }
    );

    await navigator.serviceWorker.ready;

    updateStatus("Service Worker registered", "green");

    await generateToken();

  } catch (error) {
    updateStatus(error.message, "red");
    console.error(error);
  }

});

// Issue 6 - periodic token refresh check
setInterval(async () => {

  if (!registration) return;

  try {

    await generateToken();

    console.log("Token refresh check completed");

  } catch (err) {

    console.error(err);

  }

}, 60 * 60 * 1000);
