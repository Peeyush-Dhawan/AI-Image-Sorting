import os
import numpy as np
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from utils import cosine_similarity

router = APIRouter()

# Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('MONGO_DB_NAME', 'DigitalVidyaSaarthi')

STUDENT_COLLECTION = 'studentEmbedding'
GALLERY_COLLECTION = 'galleryEmbedding'
RESULT_COLLECTION = 'embeddedGallery'

# Templates
templates = Jinja2Templates(directory="templates")

# MongoDB Connection
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    student_col = db[STUDENT_COLLECTION]
    gallery_col = db[GALLERY_COLLECTION]
    result_col = db[RESULT_COLLECTION]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

@router.get("/ui", response_class=HTMLResponse)
async def get_sorting_ui(request: Request):
    return templates.TemplateResponse("sorting.html", {"request": request})

@router.post("/find")
async def find_student_photos(student_id: str = Form(...), threshold: float = 0.1):
    """
    Finds photos of a student in the gallery by comparing embeddings.
    """
    # 1. Fetch Student
    student = student_col.find_one({"studentId": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student_embedding = student.get("vectorEmbedding")
    school_id = student.get("schoolId")
    
    if not student_embedding:
        raise HTTPException(status_code=400, detail="Student has no embedding")

    # 2. Fetch Gallery Images for the same school
    gallery_cursor = gallery_col.find({"schoolId": school_id})
    gallery_list = list(gallery_cursor)
    print(f"DEBUG: Found {len(gallery_list)} images in gallery for school {school_id}")
    
    matches = []
    
    for img in gallery_list:
        gallery_embedding = img.get("vectorgallery")
        if not gallery_embedding:
            print(f"DEBUG: Image {img.get('_id')} has no embedding")
            continue
            
        # 3. Compare Vectors
        sim = cosine_similarity(student_embedding, gallery_embedding)
        print(f"DEBUG: Comparing with {img.get('_id')}, similarity: {sim}")
        
        if sim > threshold:
            match_data = {
                "imageUrl": img.get("imageUrl"),
                "similarity": sim,
                "galleryId": str(img.get("_id"))
            }
            matches.append(match_data)
            
            # 4. Save to embeddedGallery (Optional requirement)
            # We store the match result
            result_doc = {
                "studentId": student_id,
                "schoolId": school_id,
                "galleryImageId": str(img.get("_id")),
                "imageUrl": img.get("imageUrl"),
                "similarity": sim,
                "studentVector": student_embedding,
                "galleryVector": gallery_embedding
            }
            # Upsert to avoid duplicates for same pair? 
            # Or just insert? Let's upsert based on studentId + galleryImageId
            result_col.update_one(
                {"studentId": student_id, "galleryImageId": str(img.get("_id"))},
                {"$set": result_doc},
                upsert=True
            )

    # Sort by similarity descending
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    
    return JSONResponse({
        "student_id": student_id,
        "school_id": school_id,
        "matches": matches,
        "count": len(matches)
    })
