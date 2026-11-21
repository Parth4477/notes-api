# tests/test_app.py - Unit tests that run WITHOUT a database (so CI can run them anywhere).

import os
import sys

# Add the project root to Python's search path so 'import app' works from the tests folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_health():
    # Flask's test client sends fake requests without starting a real server.
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_home_page():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Notes App" in response.data


def test_add_note_requires_title():
    client = app.test_client()
    # No title in the body -> the API must reject it with 400 before using the database.
    response = client.post("/notes", json={"content": "no title here"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "title is required"
