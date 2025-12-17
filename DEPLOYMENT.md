# CI/CD Deployment Guide (GitHub Actions)

This guide covers automating the deployment of:
1.  **Backend** to **Google Cloud Run**.
2.  **Frontend** to **Firebase Hosting**.

## Architecture
- **Frontend**: Static files served via Firebase Hosting (Global CDN).
- **Backend**: FastAPI container running on Cloud Run.
- **Routing**: Firebase Hosting is configured to proxy `/api/**` requests to the Cloud Run service, providing a unified domain name (no CORS issues).

## Prerequisites
1.  **GitHub Repository**: Your code must be pushed to GitHub.
2.  **Google Cloud Project**: With Billing enabled.
3.  **Firebase Project**: Linked to your GCP Project.

## Step 1: Google Cloud & Firebase Setup

1.  **Enable APIs** in [GCP Console](https://console.cloud.google.com/):
    - Cloud Run Admin API
    - Artifact Registry API
    - IAM Credentials API
    - Firebase Management API

2.  **Create Service Account for GitHub Actions**:
    - Go to **IAM & Admin** > **Service Accounts**.
    - Create a new account (e.g., `github-actions-deploy`).
    - Grant the following Roles:
        - *Cloud Run Admin* (To deploy services)
        - *Service Account User* (To act as the runtime service account)
        - *Artifact Registry Admin* (To push container images)
        - *Firebase Admin* (To deploy hosting)
    - Create and download a **JSON Key** for this account.

## Step 2: GitHub Repository Secrets

Go to your GitHub Repo -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.

Add the following secrets (COPY values from your local `.env` file where applicable):

| Secret Name | Value | Description |
|---|---|---|
| `GCP_CREDENTIALS` | (Content of your JSON Key file) | The Service Account JSON Key you downloaded. |
| `GCP_PROJECT_ID` | `your-project-id` | Your Google Cloud Project ID. |
| `LINE_CHANNEL_ID` | (Value from .env) | Your LINE Channel ID. |
| `LINE_CHANNEL_SECRET` | (Value from .env) | Your LINE Channel Secret. |
| `SECRET_KEY` | (Value from .env) | Your JWT Secret Key. |

## Step 3: Create `firebase.json`

Create a file named `firebase.json` in the root directory to configure the hosting rules and API rewriting.

```json
{
  "hosting": {
    "public": "frontend",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "kkc-devotion-system",
          "region": "asia-east1"
        }
      }
    ]
  }
}
```

## Step 4: Create GitHub Workflow

Create a file at `.github/workflows/deploy.yml`:

```yaml
name: Deploy Production

on:
  push:
    branches:
      - main
    paths-ignore:
      - 'README.md'

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: asia-east1
  SERVICE_NAME: kkc-devotion-system

jobs:
  # 1. Deploy Backend to Cloud Run
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Google Auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: '${{ secrets.GCP_CREDENTIALS }}'

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Deploy to Cloud Run
        # This builds the source (Dockerfile) and deploys it
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --source . \
            --region ${{ env.REGION }} \
            --project ${{ env.PROJECT_ID }} \
            --allow-unauthenticated \
            --set-env-vars "LINE_CHANNEL_ID=${{ secrets.LINE_CHANNEL_ID }},LINE_CHANNEL_SECRET=${{ secrets.LINE_CHANNEL_SECRET }},SECRET_KEY=${{ secrets.SECRET_KEY }}"

  # 2. Deploy Frontend to Firebase Hosting
  deploy-frontend:
    needs: deploy-backend
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to Firebase Hosting
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.GCP_CREDENTIALS }}'
          channelId: live
          projectId: ${{ secrets.GCP_PROJECT_ID }}
```

## Step 5: Verification

1.  Commit and Push the files (`firebase.json`, `.github/workflows/deploy.yml`) to GitHub.
2.  Go to the **Actions** tab in GitHub to monitor the deployment.
3.  Once green, open your Firebase Hosting URL (e.g., `https://[your-project-id].web.app`).
4.  **Important**: Update your **LINE Login Callback URL** in the LINE Developers Console to:
    `https://[your-project-id].web.app/api/auth/line/callback`
