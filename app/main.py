import os
import logging
import datetime
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.scraper import ScraperWorker

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="PDF Scraper & Google Drive Uploader")

# Initialize central background scraper worker
worker = ScraperWorker()

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Pydantic Schemas
class CheckSessionRequest(BaseModel):
    start_num: int
    end_num: int

class StartRequest(BaseModel):
    start_num: int
    end_num: int
    mode: Optional[str] = "start_fresh" # "start_fresh" or "resume"

class SettingsRequest(BaseModel):
    proxy_url: Optional[str] = None
    min_delay: int
    max_delay: int
    gdrive_folder_id: str
    gdrive_service_account: Optional[Any] = None

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = "app/static/index.html"
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="""
        <html>
            <head><title>Setup Error</title></head>
            <body style="font-family: sans-serif; padding: 50px; background: #121214; color: #fff; text-align: center;">
                <h2>Web UI static files not found!</h2>
                <p>Ensure that app/static/index.html is created successfully.</p>
            </body>
        </html>
    """)

@app.get("/api/ping")
@app.get("/health")
def ping_health():
    try:
        worker.log("[Keep-Alive Ping] Received keep-alive request from Cloudflare Worker")
    except Exception as e:
        logger.error(f"Error logging ping: {e}")
        
    status = "idle"
    current_num = 0
    files_uploaded = 0
    
    if hasattr(worker, "state") and isinstance(worker.state, dict):
        status = str(worker.state.get("status", "idle"))
        current_num = int(worker.state.get("current_num", 0))
        stats = worker.state.get("stats", {})
        if isinstance(stats, dict):
            files_uploaded = int(stats.get("files_uploaded", 0))

    return {
        "status": "ok",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scraper_status": status,
        "current_num": current_num,
        "files_uploaded": files_uploaded
    }

@app.get("/api/status")
def get_status():
    return worker.get_status()

@app.post("/api/check-session")
def check_session(req: CheckSessionRequest):
    session_name = f"{req.start_num}-{req.end_num}"
    
    session = None
    if hasattr(worker, "supabase") and worker.supabase.enabled:
        session = worker.supabase.get_session_by_name(session_name)

    if session:
        status = session.get("status", "not_complete")
        current_num = session.get("current_num", req.start_num)
        end_num = session.get("end_num", req.end_num)
        
        is_completed = (status == "completed" or status == "complete" or current_num > end_num)
        
        return {
            "exists": True,
            "session_name": session_name,
            "status": "completed" if is_completed else "not_complete",
            "current_num": current_num,
            "start_num": session.get("start_num", req.start_num),
            "end_num": end_num,
            "stats": session.get("stats", {})
        }
        
    return {"exists": False, "session_name": session_name}

@app.post("/api/start")
def start_scraper(req: StartRequest):
    try:
        worker.start(start_num=req.start_num, end_num=req.end_num, mode=req.mode)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error starting scraper: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/resume")
def resume_scraper():
    try:
        worker.resume()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error resuming scraper: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/stop")
def stop_scraper():
    try:
        worker.stop()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error stopping scraper: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    try:
        update_data = {
            "proxy_url": req.proxy_url,
            "min_delay": req.min_delay,
            "max_delay": req.max_delay,
            "gdrive_folder_id": req.gdrive_folder_id
        }
        if req.gdrive_service_account is not None:
            # Service account info is passed as raw dict
            update_data["gdrive_service_account"] = req.gdrive_service_account
            
        worker.update_settings(update_data)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/test-drive")
def test_drive():
    try:
        res = worker.test_drive_connection()
        return res
    except Exception as e:
        logger.error(f"Error testing Drive connection: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/files/{filename}")
def read_log_file(filename: str):
    if filename not in ["failed.txt", "not_uploaded.txt", "no_data.txt"]:
        raise HTTPException(status_code=404, detail="Invalid log filename.")
    
    if not os.path.exists(filename):
        return {"content": "", "lines_count": 0}
        
    try:
        with open(filename, "r") as f:
            content = f.read()
        lines = content.strip().split("\n")
        lines_count = len([l for l in lines if l])
        return {"content": content, "lines_count": lines_count}
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/{filename}/clear")
def clear_log_file(filename: str):
    if filename not in ["failed.txt", "not_uploaded.txt", "no_data.txt"]:
        raise HTTPException(status_code=404, detail="Invalid log filename.")
        
    try:
        with open(filename, "w") as f:
            f.write("")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error clearing file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{filename}/download")
def download_log_file(filename: str):
    if filename not in ["failed.txt", "not_uploaded.txt", "no_data.txt"]:
        raise HTTPException(status_code=404, detail="Invalid log filename.")
        
    if not os.path.exists(filename):
        # Create an empty file to download
        with open(filename, "w") as f:
            pass
            
    return FileResponse(path=filename, filename=filename, media_type="text/plain")
