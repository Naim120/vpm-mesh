import os
import json
import logging
import datetime
import httpx

logger = logging.getLogger("supabase_service")

class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
        self.enabled = bool(self.url and self.key)
        
        if self.enabled:
            logger.info("Supabase service initialized successfully.")
        else:
            logger.info("Supabase URL or Key not set. Running in local state fallback mode.")

    def _get_headers(self) -> dict:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation"
        }

    def upsert_session(self, session_name: str, start_num: int, end_num: int, current_num: int, status: str, stats: dict, error_message: str = "") -> bool:
        if not self.enabled:
            return False
            
        endpoint = f"{self.url}/rest/v1/scraper_sessions"
        payload = {
            "session_name": session_name,
            "start_num": start_num,
            "end_num": end_num,
            "current_num": current_num,
            "status": status,
            "stats": stats,
            "error_message": error_message,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(endpoint, headers=self._get_headers(), json=payload)
                if res.status_code in [200, 201]:
                    logger.debug(f"Successfully upserted session '{session_name}' to Supabase.")
                    return True
                else:
                    logger.error(f"Failed to upsert session to Supabase ({res.status_code}): {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error communicating with Supabase: {e}")
            return False

    def get_latest_session(self) -> dict:
        if not self.enabled:
            return None
            
        endpoint = f"{self.url}/rest/v1/scraper_sessions?order=updated_at.desc&limit=1"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json"
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(endpoint, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
        except Exception as e:
            logger.error(f"Error fetching latest session from Supabase: {e}")
            
    def get_session_by_name(self, session_name: str) -> dict:
        if not self.enabled:
            return None
            
        endpoint = f"{self.url}/rest/v1/scraper_sessions?session_name=eq.{session_name}&limit=1"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json"
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(endpoint, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
        except Exception as e:
            logger.error(f"Error fetching session '{session_name}' from Supabase: {e}")
            
        return None
