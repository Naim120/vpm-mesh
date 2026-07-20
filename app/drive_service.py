import io
import json
import logging
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger("drive_service")
logging.basicConfig(level=logging.INFO)

class DriveService:
    def __init__(self, auth_config: dict = None):
        self.service = None
        self.auth_config = auth_config
        if auth_config:
            try:
                self._authenticate()
            except Exception:
                pass

    def _authenticate(self):
        try:
            scopes = [
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Check if User OAuth 2.0 Refresh Token is provided
            if isinstance(self.auth_config, dict) and "refresh_token" in self.auth_config:
                credentials = Credentials(
                    token=None,
                    refresh_token=self.auth_config.get("refresh_token"),
                    client_id=self.auth_config.get("client_id"),
                    client_secret=self.auth_config.get("client_secret"),
                    token_uri="https://oauth2.googleapis.com/token",
                    scopes=scopes
                )
                self.service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
                logger.info("Successfully authenticated Google Drive via User OAuth 2.0 (5TB Personal Storage).")
            # Check if Service Account JSON is provided
            elif isinstance(self.auth_config, dict) and self.auth_config.get("type") == "service_account":
                credentials = service_account.Credentials.from_service_account_info(
                    self.auth_config, scopes=scopes
                )
                self.service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
                logger.info("Successfully authenticated Google Drive Service Account.")
            else:
                raise ValueError("Unrecognized authentication format. Provide Service Account JSON or User OAuth dict.")
        except Exception as e:
            logger.error(f"Failed to authenticate Google Drive service: {e}")
            self.service = None
            raise e

    def update_credentials(self, auth_config: dict):
        """Update account credentials and re-authenticate."""
        self.auth_config = auth_config
        self._authenticate()

    def test_connection(self, folder_id: str) -> dict:
        """Tests if we can authenticate and read the folder."""
        if not self.auth_config:
            return {"success": False, "error": "No Google Drive credentials or configuration provided."}
        
        try:
            if not self.service:
                self._authenticate()
            
            # Fetch folder details to verify read permissions
            folder = self.service.files().get(
                fileId=folder_id, 
                fields="id, name, mimeType",
                supportsAllDrives=True
            ).execute()
            
            if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                return {
                    "success": False, 
                    "error": f"ID exists, but it is not a folder. Type: {folder.get('mimeType')}"
                }
                
            return {
                "success": True, 
                "folder_name": folder.get('name'),
                "folder_id": folder.get('id')
            }
        except Exception as e:
            logger.error(f"Google Drive connection test failed for folder '{folder_id}': {e}")
            return {"success": False, "error": str(e)}

    def upload_file(self, file_content: bytes, filename: str, mime_type: str, folder_id: str = None) -> str:
        """Uploads a file to Google Drive. Returns the uploaded file's ID."""
        if not self.service:
            if self.auth_config:
                self._authenticate()
            else:
                raise ValueError("Google Drive service is not authenticated. Please provide credentials first.")

        try:
            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]

            fh = io.BytesIO(file_content)
            media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
            
            # Execute upload with Shared Drive support
            file_obj = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            file_id = file_obj.get('id')
            logger.info(f"Successfully uploaded '{filename}' to Google Drive. File ID: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Error uploading file '{filename}' to Google Drive: {e}")
            raise e
