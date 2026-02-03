"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state after each test"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for name, activity in original_activities.items():
        if name in activities:
            activities[name]["participants"] = activity["participants"].copy()


class TestRoot:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting activities"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        assert "Soccer Team" in data
        
        # Verify structure
        assert "description" in data["Chess Club"]
        assert "schedule" in data["Chess Club"]
        assert "max_participants" in data["Chess Club"]
        assert "participants" in data["Chess Club"]
    
    def test_get_activities_has_correct_structure(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up test@mergington.edu for Chess Club"
        
        # Verify student is added to participants
        assert "test@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_already_registered(self, client, reset_activities):
        """Test signup when student is already registered"""
        # Sign up once
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        # Try to sign up again
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"
    
    def test_signup_multiple_students(self, client, reset_activities):
        """Test multiple students can sign up for the same activity"""
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student1@mergington.edu"}
        )
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student2@mergington.edu"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert "student1@mergington.edu" in activities["Chess Club"]["participants"]
        assert "student2@mergington.edu" in activities["Chess Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for unregistering from activities"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # First sign up
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Unregistered test@mergington.edu from Chess Club"
        
        # Verify student is removed from participants
        assert "test@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregister when student is not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student not registered for this activity"
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregister for an existing participant"""
        # Get initial count
        initial_participants = activities["Chess Club"]["participants"].copy()
        assert "michael@mergington.edu" in initial_participants
        
        # Unregister existing participant
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""
    
    def test_full_signup_unregister_workflow(self, client, reset_activities):
        """Test complete workflow of viewing, signing up, and unregistering"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # 1. Get activities
        response = client.get("/activities")
        assert response.status_code == 200
        assert activity in response.json()
        
        # 2. Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities[activity]["participants"]
        
        # 3. Verify student is registered
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # 4. Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
