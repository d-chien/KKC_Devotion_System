# Deployment Instructions

This guide follows the **Google Cloud Run** deployment strategy. This service will host both the FastAPI backend and serve the static frontend files.

## Prerequisites

1.  **Google Cloud Platform Project**: Create one at [console.cloud.google.com](https://console.cloud.google.com/).
2.  **Google Cloud SDK**: Install the `gcloud` CLI.
3.  **Firebase Credentials**: Download your service account JSON key.

## Steps

### 1. Prepare Environment Variables
You need to set the environment variables in Cloud Run.
Prepare the following values:
- `LINE_CHANNEL_ID`: Your LINE Channel ID.
- `LINE_CHANNEL_SECRET`: Your LINE Channel Secret.
- `SECRET_KEY`: A random string for JWT security.
- `FIREBASE_CREDENTIALS_PATH`: Path to the json file. **Note**: For Cloud Run, it's safer to use Google Secret Manager or store the JSON in the container (less secure).
    - *Best Practice*: Allow the Cloud Run service account access to Firestore directly via IAM, so you don't need a JSON file key!
    - *Code Adjustment*: The `backend/core/database.py` already supports default credentials (`firebase_admin.initialize_app()` without args) if the key file is missing.

### 2. Build and Deploy with gcloud

Run the following command from the project root:

```bash
# 1. Login to Google Cloud
gcloud auth login

# 2. Set your specific project ID
gcloud config set project [YOUR_PROJECT_ID]

# 3. Deploy to Cloud Run (source based deployment)
gcloud run deploy kkc-devotion-system \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars LINE_CHANNEL_ID=[YOUR_ID],LINE_CHANNEL_SECRET=[YOUR_SECRET],SECRET_KEY=[YOUR_KEY]
```

### 3. Verify Deployment

1.  The command will output a service URL (e.g., `https://kkc-devotion-system-xyz-de.a.run.app`).
2.  Open this URL in your browser.
3.  Go to LINE Developers Console -> **LINE Login** settings.
4.  Adding the Callback URL: `https://[YOUR_URL]/api/auth/line/callback`.

### 4. Firestore Permissions

Ensure the **Default Compute Service Account** used by Cloud Run has the "Cloud Datastore User" or "Firebase Admin" role in your GCP IAM settings.

---

## Alternative: Firebase Hosting (Frontend) + Cloud Run (Backend)

If you prefer using Firebase Hosting for the frontend:

1.  Install firebase tools: `npm install -g firebase-tools`
2.  Initialize: `firebase init hosting`
3.  Edit `firebase.json` to rewrite API calls to Cloud Run:
    ```json
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "kkc-devotion-system",
          "region": "asia-east1"
        }
      }
    ]
    ```
4.  Deploy: `firebase deploy`
