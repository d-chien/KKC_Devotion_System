# KKC Devotion System

Based on the Design Document and Functional Specifications.

## Prerequisites
- Python 3.9+
- Google Cloud Project with Firestore enabled
- Firebase Admin Credentials JSON file
- LINE Developers Channel (Channel ID, Secret)

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Environment Configuration**
   Set the following environment variables (or rely on default `core/config.py` defaults for testing, but LINE Login won't work without keys):
   - `LINE_CHANNEL_ID`
   - `LINE_CHANNEL_SECRET`
   - `FIREBASE_CREDENTIALS_PATH` (Path to your service account json)
   - `SECRET_KEY`

3. **Running the Server**
   ```bash
   python backend/main.py
   ```
   
   The server will start at `http://localhost:8000`.

## Features
- **Member Portal**: `http://localhost:8000/`
    - LINE Login
    - Dashboard (Total, Charts, List)
    - Profile Binding
- **Admin Portal**: `http://localhost:8000/admin/`
    - Dashboard
    - Data Upload (Excel/CSV)
    - User Management

## Technical Notes
- **Backend**: FastAPI
- **Frontend**: HTML5 + TailwindCSS + Vanilla JS
- **Database**: Google Firestore

## Project Structure
- `backend/`: FastAPI application code.
- `frontend/`: Static HTML/JS/CSS files.
- `Design_Document.md`: Original Design Specs.
