import requests
import cv2
import numpy as np
import json
import os
from db import SessionLocal, Student
from insightface_engine import InsightFaceEngine

# Initialize Engine
print("Initializing InsightFace Engine...")
engine = InsightFaceEngine()
engine.prepare()
print("Engine ready.")

def download_image_from_url(url):
    """
    Downloads an image from a URL and converts it to a numpy array (OpenCV format).
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        # Convert bytes to numpy array
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        # Decode image
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if img is None:
            print(f"Error: Could not decode image from {url}")
            return None
            
        return img
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def process_student(student_id, name, photo_url, db):
    """
    Downloads photo, generates embedding, and saves to DB.
    """
    print(f"Processing Student: {student_id} ({name})...")
    
    # 1. Download Image
    img = download_image_from_url(photo_url)
    if img is None:
        return False

    # 2. Detect Face & Get Embedding
    faces = engine.get_faces(img)
    if len(faces) == 0:
        print(f"  WARNING: No face detected for {student_id}. Skipping.")
        return False
    
    # Use the first face found (largest/most prominent usually)
    embedding = faces[0]['embedding']
    
    # 3. Save to Database
    # Check if exists
    existing = db.query(Student).filter(Student.student_id == student_id).first()
    
    if existing:
        print(f"  Updating existing record for {student_id}.")
        existing.embedding_json = json.dumps(embedding)
        existing.student_name = name
        # We can store the URL as the reference, or leave it as is. 
        # For this use case, let's store the URL so we know where it came from.
        existing.reference_image = photo_url 
    else:
        print(f"  Creating new record for {student_id}.")
        new_student = Student(
            student_id=student_id,
            student_name=name,
            embedding_json=json.dumps(embedding),
            reference_image=photo_url
        )
        db.add(new_student)
    
    db.commit()
    print(f"  SUCCESS: Enrolled {student_id}.")
    return True

def main():
    db = SessionLocal()
    
    # --- EXAMPLE DATA SOURCE ---
    # In a real scenario, you would query your external database here.
    # Example:
    # cursor.execute("SELECT id, name, photo_url FROM students")
    # students_to_enroll = cursor.fetchall()
    
    # For demonstration, we use a list. 
    # NOTE: Ensure the server is running (localhost:8000) if using local static URLs.
    students_to_enroll = [
        # (ID, Name, URL)
        # Using the test image we already have in static/students if available, 
        # or we can use the one we generated in tests.
        # Let's try to use the one from the test setup if possible, or a placeholder.
        # Assuming the user will replace this with their real data query.
    ]
    
    # If list is empty, print instructions
    if not students_to_enroll:
        print("No students in list. Please populate 'students_to_enroll' with real data.")
        print("Example: students_to_enroll = [('101', 'Alice', 'http://example.com/alice.jpg')]")
        
        # Let's add a dummy one for the user to see if they run it immediately with a valid URL
        # We can use a placeholder image service or a local one if we know it exists.
        # Since we ran tests, we know 'test_user_01' exists. Let's try to re-enroll them via URL if we can serve it.
        # But we don't have a public URL for it unless we use localhost.
        print("\nTo test with local server, ensure uvicorn is running and add:")
        print("students_to_enroll = [('test_bulk_01', 'Bulk User', 'http://localhost:8000/static/students/test_user_01_test_student.jpg')]")

    for s_id, s_name, s_url in students_to_enroll:
        process_student(s_id, s_name, s_url, db)
        
    db.close()

if __name__ == "__main__":
    main()
