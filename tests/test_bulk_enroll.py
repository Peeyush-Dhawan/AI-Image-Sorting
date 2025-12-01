import sys
import os
import requests
# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bulk_enroll import process_student
from db import SessionLocal, Student

def test_bulk_enrollment_flow():
    print("Testing Bulk Enrollment Flow...")
    
    # 1. Setup Data
    # We need a valid URL. Since the app is running on port 8000, we can use a static file.
    # We previously enrolled 'test_user_01', so 'static/students/test_user_01_test_student.jpg' should exist.
    # Let's check if we can access it.
    base_url = "http://localhost:8000"
    # We need to find the exact filename. The test_app.py output showed:
    # 'reference_image': '/Users/.../static/students/test_user_01_test_student.jpg'
    # The static mount is at /static.
    # So URL should be http://localhost:8000/static/students/test_user_01_test_student.jpg
    
    image_url = f"{base_url}/static/students/test_user_01_test_student.jpg"
    student_id = "bulk_test_user_99"
    student_name = "Bulk Test User"
    
    # Verify URL is accessible
    try:
        resp = requests.head(image_url)
        if resp.status_code != 200:
            print(f"Skipping test: Image URL {image_url} not accessible (Status {resp.status_code}).")
            print("Ensure the server is running and the file exists.")
            return
    except Exception as e:
        print(f"Skipping test: Could not connect to {base_url}. Is the server running?")
        return

    # 2. Run Process
    db = SessionLocal()
    success = process_student(student_id, student_name, image_url, db)
    
    if not success:
        print("FAILED: process_student returned False.")
        return

    # 3. Verify in DB
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if student:
        print(f"SUCCESS: Student {student.student_id} found in DB.")
        print(f"  Name: {student.student_name}")
        print(f"  Ref Image: {student.reference_image}")
        print(f"  Embedding Length: {len(student.embedding_json)}")
    else:
        print("FAILED: Student not found in DB after processing.")
    
    db.close()

if __name__ == "__main__":
    test_bulk_enrollment_flow()
