# backend/firebase_admin_config.py
import firebase_admin
from firebase_admin import credentials
import os
from dotenv import load_dotenv
from pathlib import Path
import json

# Load .env variables from the backend directory.
# Ensure this path is correct if your .env is not in the 'backend' directory directly.
# This assumes .env is in the same directory as 'main.py' and 'strikewise' folder.
load_dotenv()

# Get Firebase service account key from environment variable
# It's recommended to store this as a single JSON string in your environment variable.
FIREBASE_SERVICE_ACCOUNT_KEY_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")

if not FIREBASE_SERVICE_ACCOUNT_KEY_JSON:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_KEY is missing or empty in .env. "
                       "Please add the JSON content of your Firebase service account key.")

try:
    # Parse the JSON string into a dictionary
    firebase_config = json.loads(FIREBASE_SERVICE_ACCOUNT_KEY_JSON)
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except json.JSONDecodeError:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY is not a valid JSON string.")
except Exception as e:
    raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}. "
                       "Check your FIREBASE_SERVICE_ACCOUNT_KEY format and content.")