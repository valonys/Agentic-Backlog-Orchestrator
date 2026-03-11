"""
Test suite for Backlog Inspector Dashboard backend
Run: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


def test_health_check():
    """Test the root health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "ai_enabled" in data


def test_process_backlog_no_file():
    """Test process endpoint without file"""
    response = client.post("/process-backlog")
    assert response.status_code == 422  # Unprocessable Entity


def test_process_backlog_invalid_extension():
    """Test process endpoint with invalid file type"""
    files = {"database": ("test.txt", b"fake content", "text/plain")}
    response = client.post("/process-backlog", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


# Add more tests as needed
@pytest.mark.asyncio
async def test_excel_parsing():
    """Test Excel parsing utility"""
    from utils import map_headers
    
    headers = ["Tag", "Item Class", "Days in Backlog", "Backlog?"]
    mapped = map_headers(headers)
    
    assert "Tag" in mapped
    assert "Item Class" in mapped
    assert "Days in Backlog" in mapped
    assert "Backlog?" in mapped


def test_rule_based_processing():
    """Test fallback rule-based processing"""
    from utils import process_rule_based
    
    sample_items = [
        {
            "Tag": "TEST-001",
            "Item Class": "Test",
            "Description": "Test item",
            "Days in Backlog": 100,
            "SECE": True,
            "System": "TEST",
            "Location": "FPSOT",
            "Due Date": "2025-01-01"
        }
    ]
    
    result = process_rule_based(sample_items)
    assert len(result) == 1
    assert result[0]["Risk Level"] == "High"
    assert result[0]["Action"] == "Escalate"
