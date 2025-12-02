import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import app

class TestSorting(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('routers.sorting.student_col')
    @patch('routers.sorting.gallery_col')
    @patch('routers.sorting.result_col')
    def test_find_student_photos(self, mock_result_col, mock_gallery_col, mock_student_col):
        # Mock Student
        mock_student_col.find_one.return_value = {
            "studentId": "123",
            "schoolId": "SCH-001",
            "vectorEmbedding": [1.0, 0.0]
        }
        
        # Mock Gallery
        # Img1: Perfect match (1.0)
        # Img2: Orthogonal (0.0)
        mock_gallery_cursor = [
            {
                "_id": "img1",
                "schoolId": "SCH-001",
                "vectorgallery": [1.0, 0.0],
                "imageUrl": "http://img1.jpg"
            },
            {
                "_id": "img2",
                "schoolId": "SCH-001",
                "vectorgallery": [0.0, 1.0],
                "imageUrl": "http://img2.jpg"
            }
        ]
        mock_gallery_col.find.return_value = mock_gallery_cursor

        response = self.client.post("/sorting/find", data={"student_id": "123"})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should match img1 but not img2 (threshold 0.5)
        self.assertEqual(len(data['matches']), 1)
        self.assertEqual(data['matches'][0]['imageUrl'], "http://img1.jpg")
        self.assertAlmostEqual(data['matches'][0]['similarity'], 1.0)
        
        # Verify save to embeddedGallery
        mock_result_col.update_one.assert_called_once()
        args, _ = mock_result_col.update_one.call_args
        self.assertEqual(args[0]['studentId'], "123")
        self.assertEqual(args[0]['galleryImageId'], "img1")

    @patch('routers.sorting.student_col')
    def test_student_not_found(self, mock_student_col):
        mock_student_col.find_one.return_value = None
        
        response = self.client.post("/sorting/find", data={"student_id": "999"})
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
