import os
import cv2
import numpy as np
import cloudinary
import cloudinary.uploader
from typing import List
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from insightface_engine import InsightFaceEngine
import base64
import json

router = APIRouter()

# Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('MONGO_DB_NAME', 'DigitalVidyaSaarthi')
COLLECTION_NAME = 'galleryEmbedding'

# Cloudinary Config
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# JWT Token (for School ID extraction)
# In a real app, we would parse the JWT. Here we assume it's static or provided.
# The user said: "extract the schoolId from our token(we will provide it static in code for now)"
# Let's try to decode the static token from env if possible, or just use a placeholder if decoding fails.
JWT_TOKEN = os.environ.get('JWT_TOKEN', '')

def get_school_id_from_token():
    try:
        # Simple decode without verification for the static token provided
        # The token is header.payload.signature
        parts = JWT_TOKEN.split('.')
        if len(parts) == 3:
            payload = parts[1]
            # Add padding if needed
            padded = payload + '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            data = json.loads(decoded)
            # Based on the token provided in .env content earlier:
            # "user": { ... "schoolId": "..." }
            return data.get('user', {}).get('schoolId')
    except Exception as e:
        print(f"Error decoding token: {e}")
    return "default_school_id"

# Templates
templates = Jinja2Templates(directory="templates")

# MongoDB Connection
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# InsightFace Engine
engine = InsightFaceEngine()

def get_engine():
    if engine.app is None:
        engine.prepare()
    return engine

@router.get("/ui", response_class=HTMLResponse)
async def get_gallery_ui(request: Request):
    return templates.TemplateResponse("gallery.html", {"request": request})

@router.post("/upload")
async def upload_gallery_images(files: List[UploadFile] = File(...)):
    """
    Uploads images to Cloudinary, generates embeddings, and saves to MongoDB.
    """
    school_id = get_school_id_from_token()
    results = []
    
    eng = get_engine()

    for file in files:
        try:
            # Read file content
            content = await file.read()
            
            # 1. Convert to numpy array for InsightFace
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                results.append({"filename": file.filename, "status": "error", "message": "Invalid image"})
                continue

            # 2. Generate Embedding
            faces = eng.get_faces(img)
            embeddings = []
            if faces:
                # Store all embeddings
                embeddings = [f['embedding'] for f in faces]
            else:
                # If no face, we might still want to upload? Or skip?
                # User said "create vector embedding". If no face, can't create it.
                results.append({"filename": file.filename, "status": "error", "message": "No face detected"})
                continue

            # 3. Upload to Cloudinary
            # Reset pointer or use content
            upload_result = cloudinary.uploader.upload(content, folder=f"gallery/{school_id}")
            image_url = upload_result.get("secure_url")
            public_id = upload_result.get("public_id")

            # 4. Save to MongoDB
            doc = {
                "schoolId": school_id,
                "vectorGallery": embeddings, # List of embeddings
                "imageUrl": image_url,
                "publicId": public_id,
                "filename": file.filename
            }
            collection.insert_one(doc)
            
            results.append({
                "filename": file.filename, 
                "status": "success", 
                "url": image_url
            })

        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "message": str(e)})

    return JSONResponse({"results": results})

@router.get("/list")
async def list_gallery_images():
    """
    Fetches gallery images for the current school.
    """
    school_id = get_school_id_from_token()
    cursor = collection.find({"schoolId": school_id})
    
    images = []
    for doc in cursor:
        images.append({
            "imageUrl": doc.get("imageUrl"),
            "filename": doc.get("filename"),
            "id": str(doc.get("_id"))
        })
        
    return JSONResponse({"images": images})
