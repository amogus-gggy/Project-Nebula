import requests
import time
import subprocess
import sys
import websocket

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"





def test_home():
    """Test home page (HTML response)."""
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    assert "Welcome to Nebula!" in resp.text
    assert "text/html" in resp.headers["Content-Type"]
    print("✓ Home page OK")


def test_hello():
    """Test hello endpoint (JSON response)."""
    resp = requests.get(f"{BASE_URL}/api/hello")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"message": "Hello, World!"}
    assert "application/json" in resp.headers["Content-Type"]
    print("✓ Hello endpoint OK")


def test_echo():
    """Test echo endpoint (POST with JSON)."""
    payload = {"name": "Test", "value": 123}
    resp = requests.post(f"{BASE_URL}/api/echo", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"echo": payload}
    print("✓ Echo endpoint OK")


def test_user_by_id():
    """Test user endpoint with typed int path parameter."""
    resp = requests.get(f"{BASE_URL}/api/users/42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 42  # Now it's an int, not string
    assert data["name"] == "User 42"
    print("✓ User by ID endpoint OK")


def test_item_by_name():
    """Test item endpoint with typed str path parameter."""
    resp = requests.get(f"{BASE_URL}/api/items/widget")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "widget"
    assert data["type"] == "item"
    print("✓ Item by name endpoint OK")


def test_score_by_float():
    """Test score endpoint with typed float path parameter."""
    resp = requests.get(f"{BASE_URL}/api/score/3.14")
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 3.14
    assert data["doubled"] == 6.28
    print("✓ Score by float endpoint OK")


def test_sync_handler():
    """Test synchronous handler."""
    resp = requests.get(f"{BASE_URL}/api/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "sync"
    assert "I'm synchronous!" in data["message"]
    print("✓ Sync handler OK")


def test_not_found():
    """Test 404 response."""
    resp = requests.get(f"{BASE_URL}/nonexistent")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "Not Found"
    print("✓ 404 response OK")


def test_websocket_echo():
    """Test WebSocket echo endpoint."""
    ws = websocket.create_connection(f"{WS_URL}/ws/echo")
    try:
        ws.send("Hello")
        result = ws.recv()
        assert result == "Echo: Hello"
        
        ws.send("World")
        result = ws.recv()
        assert result == "Echo: World"
        
        print("✓ WebSocket echo OK")
    finally:
        ws.close()


def test_websocket_chat_with_room():
    """Test WebSocket chat endpoint with room parameter."""
    ws = websocket.create_connection(f"{WS_URL}/ws/chat/general")
    try:
        # First message should be welcome (received immediately after accept)
        result = ws.recv()
        assert result == "Welcome to room: general!"

        # Send a message
        ws.send("Hi everyone!")
        result = ws.recv()
        assert result == "[general] Hi everyone!"

        print("✓ WebSocket chat with room OK")
    finally:
        ws.close()


def test_websocket_json():
    """Test WebSocket JSON endpoint."""
    ws = websocket.create_connection(f"{WS_URL}/ws/json")
    try:
        ws.send('{"name": "test", "value": 42}')
        result = ws.recv()
        import json
        data = json.loads(result)
        assert data["received"] == {"name": "test", "value": 42}
        assert data["status"] == "processed"
        
        print("✓ WebSocket JSON OK")
    finally:
        ws.close()


def main():



    try:
        print("Running tests...\n")

        test_home()
        test_hello()
        test_echo()
        test_user_by_id()
        test_item_by_name()
        test_score_by_float()
        test_sync_handler()
        test_not_found()
        test_websocket_echo()
        test_websocket_chat_with_room()
        test_websocket_json()

        print("\n✅ All tests passed!")


    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server")
        sys.exit(1)





if __name__ == "__main__":
    main()
