from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app

client = TestClient(app)


def test_health_does_not_expose_api_key():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "gemini_configured" in body
    assert "GEMINI_API_KEY" not in body
    assert "api_key" not in body


def test_home_and_voice_interface_are_served():
    home = client.get("/")
    ui = client.get("/static/index.html")
    assert home.status_code == 200
    assert "/static/index.html" in home.text
    assert ui.status_code == 200
    assert "NESI" in ui.text
    assert "Start voice session" in ui.text


def test_text_chat_reports_unconfigured_provider(monkeypatch):
    monkeypatch.setattr(main_module, "GEMINI_API_KEY", "")
    monkeypatch.setattr(main_module, "OLLAMA_ENABLED", False)
    response = client.post(
        "/chat",
        json={"mode": "owner", "language": "English", "message": "Hello NESI"},
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "unavailable"


def test_live_socket_explains_missing_gemini_key(monkeypatch):
    monkeypatch.setattr(main_module, "GEMINI_API_KEY", "")
    with client.websocket_connect("/ws/live?mode=owner") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "error"
        assert "GEMINI_API_KEY" in message["message"]
