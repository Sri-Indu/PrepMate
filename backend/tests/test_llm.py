import httpx
import pytest

from app.services.llm import (
    LlmError,
    LlmModelError,
    LlmUnavailableError,
    OllamaClient,
    normalize_ollama_base_url,
)


def test_normalize_strips_openai_v1_suffix() -> None:
    assert (
        normalize_ollama_base_url("http://127.0.0.1:11434/v1/")
        == "http://127.0.0.1:11434"
    )


def test_generate_returns_text_from_ollama_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        body = request.read()
        assert b"gemma2:2b" in body
        assert b"Explain REST" in body
        return httpx.Response(200, json={"model": "gemma2:2b", "response": "REST is ..."})

    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://127.0.0.1:11434",
    )
    client = OllamaClient(model="gemma2:2b", http_client=http_client)
    result = client.generate("Explain REST")
    assert result.model == "gemma2:2b"
    assert result.text == "REST is ..."


def test_connection_error_when_ollama_is_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://127.0.0.1:11434",
    )
    client = OllamaClient(model="gemma2:2b", http_client=http_client)
    with pytest.raises(LlmUnavailableError, match="Ollama is not running"):
        client.generate("hello")


def test_missing_model_returns_clear_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'gemma2:2b' not found"})

    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://127.0.0.1:11434",
    )
    client = OllamaClient(model="gemma2:2b", http_client=http_client)
    with pytest.raises(LlmModelError, match="ollama pull gemma2:2b"):
        client.generate("hello")


def test_empty_prompt_is_rejected() -> None:
    client = OllamaClient(
        http_client=httpx.Client(base_url="http://127.0.0.1:11434"),
        model="gemma2:2b",
    )
    with pytest.raises(LlmError, match="empty"):
        client.generate("   ")
