#!/usr/bin/env python3
import json
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

def main():
    print("=" * 65)
    print(" Google Drive Personal Account (5TB) OAuth Token Setup Helper")
    print("=" * 65)
    print("This script will generate a Refresh Token for your personal 5TB Google Account.\n")
    
    client_id = input("Enter your OAuth Client ID: ").strip()
    client_secret = input("Enter your OAuth Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Client ID and Client Secret are required.")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    oauth_json = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": creds.refresh_token
    }

    print("\n" + "=" * 65)
    print(" SUCCESS! Copy and paste the JSON object below into the Web UI Settings:")
    print("=" * 65)
    print(json.dumps(oauth_json, indent=2))
    print("=" * 65)

if __name__ == "__main__":
    main()
