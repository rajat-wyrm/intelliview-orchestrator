import os

WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    "my-secret-key-123"
)