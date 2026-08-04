import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from orchestrator.main import app
from monitoring.websocket_manager import WebSocketManager

client = TestClient(app)

# ---------------------------------------------------------------------------
# 1. Test AI Client Token Generator
# ---------------------------------------------------------------------------

def test_chat_completion_streaming():
    from workers.ai_client import chat_completion

    mock_chunk_1 = MagicMock()
    mock_chunk_1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
    
    mock_chunk_2 = MagicMock()
    mock_chunk_2.choices = [MagicMock(delta=MagicMock(content=" World"))]

    with patch("workers.ai_client.openai_client") as mock_openai, \
         patch("workers.ai_client.HAS_OPENAI", True):
        mock_openai.chat.completions.create.return_value = [mock_chunk_1, mock_chunk_2]

        messages = [{"role": "user", "content": "Hi"}]
        gen = chat_completion(messages, stream=True)

        tokens = list(gen)
        assert tokens == ["Hello", " World"]


# ---------------------------------------------------------------------------
# 2. Test SSE Endpoint Response Format
# ---------------------------------------------------------------------------

@patch("orchestrator.main.session_manager.get_session")
@patch("orchestrator.main.chat_completion")
def test_stream_evaluation_sse_endpoint(mock_chat, mock_get_session):
    mock_get_session.return_value = {
        "questions_asked": [{"text": "Explain OOP"}],
        "answers_provided": [{"answer_text": "OOP stands for..."}]
    }
    
    def dummy_generator():
        yield "Evaluation: "
        yield "Good response."

    mock_chat.return_value = dummy_generator()

    response = client.get("/interviews/test-session-123/evaluate/stream")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    body = response.text
    assert '{"token": "Evaluation: "}' in body
    assert '{"token": "Good response."}' in body
    assert '{"status": "DONE"}' in body


# ---------------------------------------------------------------------------
# 3. Test WebSocket Broadcast Helper
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_broadcast_evaluation_token():
    ws_manager = WebSocketManager()
    mock_ws = MagicMock()
    
    async def mock_send_json(data):
        pass

    mock_ws.send_json = mock_send_json
    ws_manager.active_connections.add(mock_ws)

    with patch.object(mock_ws, "send_json") as send_spy:
        await ws_manager.broadcast_evaluation_token("session-1", "token-chunk")
        send_spy.assert_called_once()
        args = send_spy.call_args[0][0]
        assert args["type"] == "evaluation_token"
        assert args["session_id"] == "session-1"
        assert args["token"] == "token-chunk"
