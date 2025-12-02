from dotenv import load_dotenv
import os

# Load env vars before importing other modules that might use them
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import students, photos, enrollment, gallery, sorting
from insightface_engine import InsightFaceEngine

app = FastAPI(title="InsightFace Photo Segregator")

# initialize engine as a singleton
engine = InsightFaceEngine()

app.include_router(students.router, prefix="/students", tags=["students"])
app.include_router(photos.router, prefix="/photos", tags=["photos"])
app.include_router(enrollment.router, prefix="/enroll", tags=["enrollment"])
app.include_router(gallery.router, prefix="/gallery", tags=["gallery"])
app.include_router(sorting.router, prefix="/sorting", tags=["sorting"])

# Mount static files (using local app/static directory)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/enroll/ui")

@app.on_event("startup")
async def startup_event():
    # Warmup model
    engine.prepare()
    print("InsightFace engine prepared.")
