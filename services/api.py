# services/api.py
from fastapi import FastAPI, HTTPException, Request, status, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
from contextlib import asynccontextmanager # <<< Thêm dòng này
from pydantic import BaseModel, Field # <<< Thêm BaseModel, Field từ pydantic
from typing import List 

from config import settings
from core import database

templates_dir = os.path.join(settings.BASE_DIR, "templates")
static_dir = os.path.join(settings.BASE_DIR, "static")
snapshot_dir = settings.SNAPSHOT_DIR

templates = Jinja2Templates(directory=templates_dir)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Các tác vụ khi server khởi động
    database.init_db()
    os.makedirs(snapshot_dir, exist_ok=True)
    print("API started via lifespan. Ensuring database and snapshot directory exist.")
    yield
    print("API shutting down via lifespan.")

# Khởi tạo FastAPI app với lifespan handler
app = FastAPI(title="Video Surveillance API & UI", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

class BulkDeleteRequest(BaseModel):
    event_ids: List[int] = Field(..., min_length=1)

# --- Các endpoint còn lại giữ nguyên ---
@app.get("/")
async def read_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/events")
def api_read_events(limit: int = 50):
    if limit <= 0 or limit > 200:
        limit = 50
    try:
        events = database.get_events(limit=limit)
        return {"count": len(events), "events": events}
    except Exception as e:
        print(f"API Error getting events: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve events from database.")

@app.get("/api/snapshots/{filename}")
async def get_snapshot(filename: str):
    try:
        file_path = os.path.abspath(os.path.join(snapshot_dir, filename))
        if not file_path.startswith(os.path.abspath(snapshot_dir)):
            raise HTTPException(status_code=403, detail="Access denied.")
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Snapshot not found.")
    except Exception as e:
        print(f"Error serving snapshot {filename}: {e}")
        raise HTTPException(status_code=500, detail="Could not serve snapshot file.")

@app.get("/api/status")
def get_status():
    return {"status": "API Running"}

@app.delete("/api/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_event(event_id: int):
    print(f"Received request to delete event id: {event_id}")
    deleted = database.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Event with id {event_id} not found or could not be deleted.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/api/events/delete-bulk", status_code=status.HTTP_200_OK)
async def api_delete_bulk_events(delete_request: BulkDeleteRequest):
    event_ids_to_delete = delete_request.event_ids
    print(f"Received request to delete multiple events with IDs: {event_ids_to_delete}")
    try:
        deleted_count = database.delete_multiple_events(event_ids_to_delete)
        if deleted_count > 0:
            return {"message": f"Successfully deleted {deleted_count} event(s)."}
        else:
            # Có thể ID không tồn tại hoặc có lỗi DB (đã log trong hàm DB)
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No events found or deleted for provided IDs: {event_ids_to_delete}")
    except Exception as e:
        print(f"Error during bulk delete API call: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An internal server error occurred during bulk deletion.")

if __name__ == '__main__':
    print(f"Starting FastAPI server on http://{settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT, reload=False) 
