import os
import json
import time
import random
import logging
import datetime
import threading
import http.client
import urllib.parse
import httpx
from app.drive_service import DriveService

logger = logging.getLogger("scraper")

STATE_FILE = "state.json"

class ScraperWorker:
    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.stop_event = threading.Event()
        self.logs = []
        
        # Load initial state or set defaults
        self.state = self.load_state()
        
        # Initialize Drive Service
        self.drive_service = None
        self.init_drive_service()

    def init_drive_service(self):
        sa = self.state.get("gdrive_service_account")
        if sa:
            try:
                self.drive_service = DriveService(sa)
            except Exception as e:
                self.log(f"Error initializing Google Drive with saved credentials: {e}")
                self.drive_service = None
        else:
            self.drive_service = None

    def load_state(self) -> dict:
        default_state = {
            "start_num": 130623,
            "end_num": 130700,
            "current_num": 130623,
            "proxy_url": "socks5://127.0.0.1:9050",
            "min_delay": 30,
            "max_delay": 60,
            "gdrive_folder_id": "",
            "gdrive_service_account": None,
            "status": "idle", # "idle", "running", "stopped", "completed", "error"
            "error_message": "",
            "stats": {
                "total_requests": 0,
                "success_count": 0,
                "failed_count": 0,
                "no_data_count": 0,
                "files_downloaded": 0,
                "files_uploaded": 0,
                "not_uploaded_count": 0
            }
        }
        
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    saved = json.load(f)
                    # Merge saved state with defaults to ensure all keys exist
                    for k, v in saved.items():
                        if isinstance(v, dict) and isinstance(default_state.get(k), dict):
                            default_state[k].update(v)
                        else:
                            default_state[k] = v
            except Exception as e:
                logger.error(f"Error loading state.json: {e}")
        
        return default_state

    def save_state(self):
        with self.lock:
            try:
                with open(STATE_FILE, "w") as f:
                    json.dump(self.state, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving state.json: {e}")

    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        logger.info(message)
        with self.lock:
            self.logs.append(log_entry)
            if len(self.logs) > 300:
                self.logs.pop(0)

    def get_status(self) -> dict:
        with self.lock:
            return {
                "start_num": self.state["start_num"],
                "end_num": self.state["end_num"],
                "current_num": self.state["current_num"],
                "proxy_url": self.state["proxy_url"],
                "min_delay": self.state["min_delay"],
                "max_delay": self.state["max_delay"],
                "gdrive_folder_id": self.state["gdrive_folder_id"],
                "has_credentials": self.state["gdrive_service_account"] is not None,
                "status": self.state["status"],
                "error_message": self.state.get("error_message", ""),
                "stats": self.state["stats"],
                "logs": self.logs
            }

    def update_settings(self, settings: dict):
        with self.lock:
            for k, v in settings.items():
                if k in self.state:
                    self.state[k] = v
            
            # Re-initialize drive service if credentials updated
            if "gdrive_service_account" in settings:
                sa = settings["gdrive_service_account"]
                if sa:
                    try:
                        self.drive_service = DriveService(sa)
                    except Exception as e:
                        self.log(f"Failed to initialize Drive service: {e}")
                        self.drive_service = None
                else:
                    self.drive_service = None
                    
        self.save_state()
        self.log("Settings updated successfully.")

    def test_drive_connection(self) -> dict:
        if not self.drive_service:
            sa = self.state.get("gdrive_service_account")
            if sa:
                try:
                    self.drive_service = DriveService(sa)
                except Exception as e:
                    return {"success": False, "error": f"Failed to authenticate credentials: {e}"}
            else:
                return {"success": False, "error": "Google Drive credentials not configured. Please paste your OAuth JSON (or Service Account JSON) in Settings."}
        
        folder_id = self.state.get("gdrive_folder_id")
        if not folder_id:
            return {"success": False, "error": "Google Drive Folder ID is not configured."}
            
        return self.drive_service.test_connection(folder_id)

    def start(self, start_num: int = None, end_num: int = None):
        with self.lock:
            if self.state["status"] == "running":
                self.log("Scraper is already running.")
                return
            
            if start_num is not None:
                self.state["start_num"] = start_num
                self.state["current_num"] = start_num
                # Reset statistics for a fresh start
                self.state["stats"] = {
                    "total_requests": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "no_data_count": 0,
                    "files_downloaded": 0,
                    "files_uploaded": 0,
                    "not_uploaded_count": 0
                }
            if end_num is not None:
                self.state["end_num"] = end_num

            # Check credentials and folder before starting
            if not self.drive_service:
                self.state["status"] = "error"
                self.state["error_message"] = "Google Drive credentials not set."
                self.log("Cannot start scraper: Google Drive credentials not set.")
                self.save_state()
                return
            
            folder_id = self.state.get("gdrive_folder_id")
            if not folder_id:
                self.state["status"] = "error"
                self.state["error_message"] = "Google Drive Folder ID not set."
                self.log("Cannot start scraper: Google Drive Folder ID not set.")
                self.save_state()
                return

            self.state["status"] = "running"
            self.state["error_message"] = ""
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            
        self.save_state()
        self.log(f"Started scraper range: {self.state['start_num']} to {self.state['end_num']}")

    def resume(self):
        with self.lock:
            if self.state["status"] == "running":
                self.log("Scraper is already running.")
                return
            
            if self.state["current_num"] > self.state["end_num"]:
                self.log("Cannot resume: already completed the requested range.")
                return

            # Check credentials and folder before resuming
            if not self.drive_service:
                self.state["status"] = "error"
                self.state["error_message"] = "Google Drive credentials not set."
                self.log("Cannot resume scraper: Google Drive credentials not set.")
                self.save_state()
                return

            folder_id = self.state.get("gdrive_folder_id")
            if not folder_id:
                self.state["status"] = "error"
                self.state["error_message"] = "Google Drive Folder ID not set."
                self.log("Cannot resume scraper: Google Drive Folder ID not set.")
                self.save_state()
                return

            self.state["status"] = "running"
            self.state["error_message"] = ""
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            
        self.save_state()
        self.log(f"Resumed scraper from {self.state['current_num']} to {self.state['end_num']}")

    def stop(self):
        with self.lock:
            if self.state["status"] != "running":
                self.log("Scraper is not running.")
                return
            self.state["status"] = "stopped"
            self.stop_event.set()
        
        self.save_state()
        self.log("Scraper stop request sent.")

    def _renew_tor_circuit(self):
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect(("127.0.0.1", 9051))
                s.sendall(b'AUTHENTICATE ""\r\n')
                resp = s.recv(1024)
                if b"250" in resp:
                    s.sendall(b'SIGNAL NEWNYM\r\n')
                    resp2 = s.recv(1024)
                    if b"250" in resp2:
                        self.log("Tor exit circuit renewed successfully (assigned fresh exit IP).")
                        return True
        except Exception as e:
            logger.debug(f"Tor circuit renewal not available: {e}")
        return False

    def _fetch_document_json(self, current_num: int, proxy_url: str = None) -> tuple[int, str]:
        target_url = f"https://hoon.co.in/api/get_schedule_documents/{current_num}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # If proxy_url is set, try requesting via SOCKS5 (Tor) or HTTP Proxy
        if proxy_url:
            max_proxy_attempts = 5
            for attempt in range(1, max_proxy_attempts + 1):
                if self.stop_event.is_set():
                    break
                try:
                    if proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://"):
                        with httpx.Client(proxy=proxy_url, timeout=30.0, follow_redirects=True) as socks_client:
                            r = socks_client.get(target_url, headers=headers)
                            if r.status_code == 200 and "status" in r.text:
                                return r.status_code, r.text
                            elif r.status_code == 403:
                                self.log(f"[{current_num}] Tor attempt {attempt}/{max_proxy_attempts} returned 403. Renewing Tor exit circuit...")
                                self._renew_tor_circuit()
                            else:
                                self.log(f"[{current_num}] Tor attempt {attempt}/{max_proxy_attempts} returned status {r.status_code}. Retrying...")
                    else:
                        parsed = urllib.parse.urlparse(proxy_url if "://" in proxy_url else f"http://{proxy_url}")
                        host = parsed.hostname or proxy_url
                        is_https = parsed.scheme == "https"
                        port = parsed.port or (443 if is_https else 80)
                        
                        if is_https:
                            import ssl
                            ssl_ctx = ssl.create_default_context()
                            conn = http.client.HTTPSConnection(host, port, context=ssl_ctx, timeout=12)
                        else:
                            conn = http.client.HTTPConnection(host, port, timeout=12)
                            
                        conn.request("GET", target_url, headers=headers)
                        res = conn.getresponse()
                        body = res.read().decode("utf-8", errors="ignore")
                        
                        if res.status == 200 and "status" in body:
                            return res.status, body
                        elif res.status == 403:
                            self.log(f"[{current_num}] Proxy attempt {attempt}/{max_proxy_attempts} returned 403 (Cloudflare block). Retrying...")
                        else:
                            self.log(f"[{current_num}] Proxy attempt {attempt}/{max_proxy_attempts} returned status {res.status}. Retrying...")
                except Exception as e:
                    self.log(f"[{current_num}] Proxy attempt {attempt}/{max_proxy_attempts} error ({e}). Retrying...")
                
                time.sleep(1)
            
            self.log(f"[{current_num}] Proxy retries exhausted. Falling back to direct connection...")

        # Direct connection fallback
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as direct_client:
                r = direct_client.get(target_url, headers=headers)
                return r.status_code, r.text
        except Exception as e:
            self.log(f"[{current_num}] Direct connection error: {e}")
            return 0, ""

    def _run_loop(self):
        try:
            start = self.state["start_num"]
            end = self.state["end_num"]
            current = self.state["current_num"]
            
            self.log(f"Started scraper range: {start} to {end}")
            self.save_state()

            # Setup HTTPX Client with Proxy
            proxy_input = self.state.get("proxy_url")
            proxy_url = None
            if proxy_input and proxy_input.strip():
                proxy_url = proxy_input.strip()
                if not (proxy_url.startswith("http://") or proxy_url.startswith("https://") or proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://")):
                    proxy_url = f"socks5://{proxy_url}"

            if proxy_url:
                self.log(f"Configuring client with proxy: {proxy_url}")
            else:
                self.log("Running without proxy.")

            # Create HTTP client for file downloads
            dl_proxy = proxy_url if (proxy_url and (proxy_url.startswith("socks5://") or proxy_url.startswith("socks5h://"))) else None
            with httpx.Client(proxy=dl_proxy, timeout=30.0, follow_redirects=True) as dl_client:
                while current <= end and not self.stop_event.is_set():
                    self.log(f"Processing number: {current}...")
                    
                    status_code, body_text = self._fetch_document_json(current, proxy_url)
                    
                    # Increment request counter
                    with self.lock:
                        self.state["stats"]["total_requests"] += 1
                    
                    if status_code == 200 and body_text:
                        try:
                            data_json = json.loads(body_text)
                            self._process_response(current, data_json, dl_client)
                        except json.JSONDecodeError:
                            self.log(f"[{current}] No valid JSON returned. Skipping.")
                    elif status_code > 0:
                        self.log(f"[{current}] HTTP Error: Received status code {status_code}. Skipping.")
                    else:
                        self.log(f"[{current}] All connection attempts failed. Skipping.")
                    
                    # Update current count and save state
                    with self.lock:
                        self.state["current_num"] = current + 1
                        current = self.state["current_num"]
                    self.save_state()
                    
                    # Check if completed
                    if current > end:
                        with self.lock:
                            self.state["status"] = "completed"
                        self.save_state()
                        self.log("Scraping range finished successfully.")
                        break

                    # Sleep between requests if not stopping
                    if not self.stop_event.is_set():
                        min_d = self.state.get("min_delay", 30)
                        max_d = self.state.get("max_delay", 60)
                        delay = random.uniform(min_d, max_d)
                        self.log(f"Sleeping for {delay:.2f} seconds before next request...")
                        
                        # Sleep in small increments to allow responsive stopping
                        slept = 0
                        while slept < delay and not self.stop_event.is_set():
                            time.sleep(1)
                            slept += 1
                            
        except Exception as e:
            self.log(f"Fatal error in scraper worker: {e}")
            with self.lock:
                self.state["status"] = "error"
                self.state["error_message"] = str(e)
            self.save_state()

    def _process_response(self, number: int, data_json: dict, client: httpx.Client) -> bool:
        status = data_json.get("status")
        
        # Rule 2: status is failed
        if status == "failed":
            self.log(f"[{number}] Status is failed. Saving to failed.txt")
            self._append_to_file("failed.txt", str(number))
            with self.lock:
                self.state["stats"]["failed_count"] += 1
            return True
            
        # Rule 1: status is success
        elif status == "success":
            data_arr = data_json.get("data")
            
            # Rule 4: status is success but "data" is empty array
            if not isinstance(data_arr, list) or len(data_arr) == 0:
                self.log(f"[{number}] Success status but empty data. Saving to no_data.txt")
                self._append_to_file("no_data.txt", str(number))
                with self.lock:
                    self.state["stats"]["no_data_count"] += 1
                return True
            
            # If data is present, inspect files
            uploaded_files = []
            for item in data_arr:
                file_val = item.get("uploadedfile")
                if file_val: # Check if not null and not empty
                    uploaded_files.append(file_val)
                    
            if len(uploaded_files) > 0:
                self.log(f"[{number}] Found {len(uploaded_files)} uploaded file(s). Downloading...")
                folder_id = self.state.get("gdrive_folder_id")
                
                for file_val in uploaded_files:
                    file_url = f"https://hoon.co.in/uploads/documents/{file_val}"
                    filename = file_val
                    
                    # Try downloading and uploading with retries
                    success = self._download_and_upload_with_retry(client, file_url, filename, folder_id)
                    if not success:
                        self.log(f"[{number}] Failed to process file {filename} after all retries.")
                
                with self.lock:
                    self.state["stats"]["success_count"] += 1
                return True
            else:
                # Rule 1 alternative: uploadedfile has no value
                # "store the application_id in a txt file 'not_uploaded.txt'"
                # Use application_id from the JSON if available, otherwise use number
                app_id = str(number)
                if len(data_arr) > 0:
                    app_id = data_arr[0].get("application_id", str(number))
                    
                self.log(f"[{number}] Success status, but no uploaded files. Saving to not_uploaded.txt")
                self._append_to_file("not_uploaded.txt", app_id)
                with self.lock:
                    self.state["stats"]["not_uploaded_count"] += 1
                return True
                
        else:
            self.log(f"[{number}] Unknown status value '{status}'. Skipping.")
            return False

    def _download_and_upload_with_retry(self, client: httpx.Client, url: str, filename: str, folder_id: str) -> bool:
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            if self.stop_event.is_set():
                return False
            try:
                self.log(f"Attempt {attempt}/{max_retries}: Downloading '{filename}'...")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = client.get(url, headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Failed download with HTTP status code {response.status_code}")
                
                file_content = response.content
                with self.lock:
                    self.state["stats"]["files_downloaded"] += 1
                
                self.log(f"Downloaded '{filename}' ({len(file_content)} bytes). Uploading to Google Drive...")
                
                # Determine MIME type from filename or response headers
                import mimetypes
                guessed_type, _ = mimetypes.guess_type(filename)
                if not guessed_type:
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        guessed_type = "image/jpeg"
                    elif filename.lower().endswith('.png'):
                        guessed_type = "image/png"
                    elif filename.lower().endswith('.pdf'):
                        guessed_type = "application/pdf"
                    else:
                        guessed_type = response.headers.get("Content-Type", "application/octet-stream").split(";")[0]

                # Upload to drive
                file_id = self.drive_service.upload_file(
                    file_content=file_content,
                    filename=filename,
                    mime_type=guessed_type,
                    folder_id=folder_id
                )
                
                with self.lock:
                    self.state["stats"]["files_uploaded"] += 1
                
                self.log(f"Uploaded '{filename}' successfully. Drive File ID: {file_id}")
                return True
                
            except Exception as e:
                self.log(f"Attempt {attempt}/{max_retries} failed for '{filename}': {e}")
                if attempt < max_retries:
                    # Random short wait before retrying to prevent hitting limits
                    time.sleep(random.uniform(2, 5))
                else:
                    self.log(f"All {max_retries} attempts failed for '{filename}'.")
                    
        return False

    def _append_to_file(self, filepath: str, text: str):
        try:
            with open(filepath, "a") as f:
                f.write(f"{text}\n")
        except Exception as e:
            self.log(f"Error writing to file '{filepath}': {e}")
