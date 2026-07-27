const { initializeApp, cert } = require("firebase-admin/app");
const { getMessaging } = require("firebase-admin/messaging");
const { getFirestore } = require("firebase-admin/firestore");

const serviceAccount = require("./serviceAccountKey.json");

initializeApp({
  credential: cert(serviceAccount),
});

const db = getFirestore();

async function sendNotification() {
  let tokens = [];

  // CLI token support
  const cliToken = process.argv[2];

  if (cliToken) {
    tokens = [cliToken];
    console.log("Using CLI token");
  } else {
    const snapshot = await db.collection("tokens").get();

    tokens = snapshot.docs.map((doc) => doc.data().token);

    if (tokens.length === 0) {
      console.log("No stored tokens found");
      return;
    }

    console.log(`Found ${tokens.length} stored token(s)`);
  }

  const message = {
    tokens,
    notification: {
      title: "Test Notification",
      body: "Hello from Firebase",
    },
  };

  const response =
    await getMessaging().sendEachForMulticast(message);

  console.log(response);
}

sendNotification().catch(console.error);    