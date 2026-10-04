"""Call a local Ollama server. No cloud LLM APIs.

Ollama is a local process that loads open-weight models (here Gemma 2 2B)
and exposes an HTTP API on port 11434.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings


class LlmError(Exception):
    """Base error for the LLM layer."""

    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


class LlmUnavailableError(LlmError):
    """Ollama is not running or did not respond in time."""


class LlmModelError(LlmError):
    """The configured model is missing or rejected."""


def normalize_ollama_base_url(url: str) -> str:
    """Accept either http://127.0.0.1:11434 or .../v1 from older .env files."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[:-3].rstrip("/")
    return cleaned


@dataclass(frozen=True)
class LlmResult:
    model: str
    text: str


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = normalize_ollama_base_url(base_url or settings.llm_base_url)
        self.model = model or settings.llm_model
        self.timeout = timeout if timeout is not None else settings.llm_timeout_seconds
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def generate(self, prompt: str, *, system: str | None = None) -> LlmResult:
        prompt = prompt.strip()
        if not prompt:
            raise LlmError("Prompt must not be empty.", status_code=400)

        payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system and system.strip():
            payload["system"] = system.strip()

        try:
            response = self._http.post("/api/generate", json=payload)
        except httpx.ConnectError as exc:
            raise LlmUnavailableError(
                "Ollama is not running. Start it locally and pull the model "
                f"with: ollama pull {self.model}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LlmUnavailableError(
                f"Ollama timed out after {self.timeout:.0f}s. "
                "The model may still be loading."
            ) from exc

        return self._parse_generate_response(response)

    def _parse_generate_response(self, response: httpx.Response) -> LlmResult:
        if response.status_code == 404:
            raise LlmModelError(
                f"Ollama could not find model '{self.model}'. "
                f"Run: ollama pull {self.model}",
                status_code=404,
            )

        if response.status_code >= 400:
            detail = _ollama_error_message(response)
            lowered = detail.lower()
            if "not found" in lowered or "pull" in lowered:
                raise LlmModelError(detail, status_code=404)
            raise LlmError(
                f"Ollama returned HTTP {response.status_code}: {detail}",
                status_code=502,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LlmError("Ollama returned a non-JSON response.", status_code=502) from exc

        text = str(body.get("response") or "").strip()
        if not text:
            raise LlmError("Ollama returned an empty response.", status_code=502)

        model_used = str(body.get("model") or self.model)
        return LlmResult(model=model_used, text=text)


def _ollama_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or "unknown error"
    if isinstance(payload, dict) and payload.get("error"):
        return str(payload["error"])
    return response.text.strip() or "unknown error"


def generate_text(prompt: str, *, system: str | None = None) -> LlmResult:
    """Convenience wrapper used by the HTTP route."""
    client = OllamaClient()
    try:
        return client.generate(prompt, system=system)
    finally:
        client.close()
