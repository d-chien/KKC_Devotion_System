import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Firebase/Firestore BEFORE importing backend modules
sys.modules["firebase_admin"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.firestore"] = MagicMock()

from fastapi.testclient import TestClient
from backend.main import app
from backend.api import deps

class TestBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    def test_read_main(self):
        """Test that the frontend static files are served (or at least 200 OK/404 handling)."""
        # Since we mounted static files at root, checking index.html functionality
        # Note: In a test environment without the actual built frontend files, this might fail or return 404 
        # unless we mocked the static file mounting or ensured files exist.
        # We did create frontend/index.html, so it should work.
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("KKC", response.text)

    def test_auth_redirect(self):
        """Test that the LINE login endpoint redirects correctly."""
        response = self.client.get("/api/auth/line/login", allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertIn("access.line.me", response.headers["location"])

    def test_get_user_me_unauthorized(self):
        """Test logic for unauthorized access."""
        # We need to reset dependency overrides to ensure we test the failing case
        app.dependency_overrides = {}
        response = self.client.get("/api/user/me")
        self.assertEqual(response.status_code, 401)

    def test_get_user_me_authorized(self):
        """Test getting user profile with mocked authentication."""
        # Mock the current user dependency
        mock_user = {
            "LineId": "test_line_id",
            "LineName": "Test User",
            "MemberId": "123456",
            "MemberName": "Test Member",
            "IsBound": True
        }
        
        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[deps.get_current_user] = override_get_current_user
        
        response = self.client.get("/api/user/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["LineId"], "test_line_id")
        self.assertEqual(response.json()["MemberId"], "123456")

    @patch("backend.api.users.get_db")
    def test_dashboard_data(self, mock_get_db):
        """Test dashboard data retrieval."""
        # Mock Authentication
        async def override_get_current_user():
            return {
                "LineId": "test_line_id",
                "MemberId": "123456",
                "MemberName": "Test Member"
            }
        app.dependency_overrides[deps.get_current_user] = override_get_current_user

        # Mock Firestore DB response
        mock_db = MagicMock()
        mock_coll = MagicMock()
        mock_query = MagicMock()
        
        # Setup Devotion Data
        devotion_data = {
            "MemberId": "123456",
            "Amount": 1000,
            "CategoryId": "cat_1",
            "CategoryName": "Tithe",
            "DevotionDate": "2025-01-01T00:00:00"
        }
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = devotion_data
        mock_doc.id = "doc_1"
        
        # Chain functionality: db.collection().where().stream()
        mock_get_db.return_value = mock_db
        mock_db.collection.return_value = mock_coll
        mock_coll.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        response = self.client.get("/api/user/dashboard")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_amount"], 1000)
        self.assertEqual(data["total_count"], 1)
        self.assertEqual(data["category_distribution"]["Tithe"], 1000)

if __name__ == "__main__":
    unittest.main()
