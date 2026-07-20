# PDF Scraper & Google Drive Uploader

A beautiful and powerful FastAPI-based application that scrapes documents from `hoon.co.in`, downloads PDF attachments using a `mubeng` proxy, uploads them to Google Drive, and saves logs for easy monitoring and downloading.

## Features
- **Background Scraping**: Runs asynchronous background tasks to crawl document APIs.
- **Proxy Rotation Support**: Routes target web requests through a configurable `mubeng` proxy.
- **Random Delay Gaps**: Introduces randomized delays (30s-60s) between requests to prevent IP bans.
- **Google Drive Integration**: Auto-uploads files to a Google Drive folder using a Service Account JSON.
- **Robust Exception Handling & Retries**: Re-tries downloading/uploading up to 5 times. Persists range progress to `state.json` to allow resumption after crashes or restarts.
- **Detailed Web Logs & Files**: Automatically logs successes, failures, and empty responses into `failed.txt`, `not_uploaded.txt`, and `no_data.txt`, all viewable and downloadable directly from the web interface.
- **Premium Web Dashboard**: Dark theme, glassmorphic layout, glowing badges, real-time statistics counters, live console logs, and settings editor.

## Project Structure
```
├── app/
│   ├── __init__.py
│   ├── drive_service.py       # Google Drive API Client
│   ├── main.py                # FastAPI server & API routes
│   ├── scraper.py             # Scraping engine & loop
│   └── static/                # Web UI files
│       ├── app.js
│       ├── index.html
│       └── style.css
├── Procfile                   # Cloud provider start instructions
├── README.md                  # This documentation
├── requirements.txt           # Python dependencies
├── run.sh                     # Local start script
└── state.json                 # Auto-generated scraper state
```

## Setup & Local Running

1. **Clone/Download** the workspace files.
2. Run the application:
   ```bash
   ./run.sh
   ```
   This will automatically create a virtual environment, install requirements, and run the server on `http://localhost:8000`.

## Google Drive Service Account Configuration
To upload files to Google Drive, the app uses a Google Cloud Service Account.
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Drive API**.
3. Go to **APIs & Services > Credentials** and click **Create Credentials > Service Account**.
4. In the Service Account details, select the Service Account, go to **Keys** tab, click **Add Key > Create New Key** and choose **JSON**.
5. Save the downloaded JSON file.
6. Open your Google Drive, create a folder where files will be uploaded, and **Share** the folder with the Service Account email address (found in your JSON key as `client_email`), giving it **Editor** permissions.
7. Open the Web UI at `http://localhost:8000`, navigate to **Settings**, paste the JSON key content into the text area, and enter the **Google Drive Folder ID** (the long alphanumeric string at the end of the folder URL).
8. Click **Save Settings** and then click **Test Connection** to verify access.

## Cloud Deployment with Bundled Tor Proxy (Koyeb / Render)

This application includes a `Dockerfile` that packages **FastAPI**, **Google Drive Uploader**, and a **Tor SOCKS5 Daemon (`socks5://127.0.0.1:9050`)** together in a single container. 

When deployed to Koyeb or Render, Tor automatically runs in the background, providing **100% anonymous IP rotation** and bypassing Cloudflare proxy blocks without exposing your personal IP address.

### Deploying on Koyeb (Recommended)
1. Push this repository to GitHub.
2. Go to [Koyeb Dashboard](https://app.koyeb.com/) and click **Create Service**.
3. Select **GitHub** as deployment source and choose your repository.
4. Set Builder to **Dockerfile**.
5. Set Port to **8000** (or let Koyeb pass `$PORT`).
6. Click **Deploy**. Koyeb will build the image, start the Tor daemon on `127.0.0.1:9050`, and launch the Web App!

### Deploying on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New > Web Service**.
2. Connect your GitHub repository.
3. Select **Docker** as Runtime.
4. Click **Create Web Service**.
