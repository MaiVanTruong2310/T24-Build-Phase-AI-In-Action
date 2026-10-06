"""Google Gemini Embeddings provider for ChromaDB vector store."""

from __future__ import annotations

import logging
import time

import requests

from src.medical_assistant.config import get_settings

logger = logging.getLogger(__name__)


class GeminiEmbeddings:
    """Lightweight embeddings client using Google AI Studio Gemini Embeddings."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "models/gemini-embedding-001",
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.google_ai_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY is required for Gemini embeddings.")
        self.model = model
        self.timeout = timeout
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def embed_documents(self, texts: list[str], batch_size: int = 40) -> list[list[float]]:
        """Embed a list of text strings in batches."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        url = f"{self.base_url}/{self.model}:batchEmbedContents?key={self.api_key}"

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            requests_body = [{"model": self.model, "content": {"parts": [{"text": text}]}} for text in batch]

            # Retry loop with backoff for rate limits (429) and network timeouts
            max_retries = 8
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        url,
                        json={"requests": requests_body},
                        timeout=self.timeout,
                    )
                except requests.exceptions.RequestException as net_err:
                    if attempt < max_retries - 1:
                        wait_net = 5.0 * (attempt + 1)
                        logger.warning("Network/Timeout error (%s). Retrying in %.1fs...", net_err, wait_net)
                        time.sleep(wait_net)
                        continue
                    raise
                if response.status_code == 200:
                    break
                if response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 12.0
                    try:
                        err_data = response.json().get("error", {})
                        for detail in err_data.get("details", []):
                            if detail.get("@type", "").endswith("RetryInfo"):
                                raw_delay = detail.get("retryDelay", "10s").rstrip("s")
                                wait_time = max(float(raw_delay) + 2.0, 5.0)
                                break
                    except Exception:
                        pass
                    logger.info(
                        "Rate limit (429) reached. Waiting %.1fs before retry (attempt %d/%d)...",
                        wait_time,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(wait_time)
                    continue

                logger.error("Gemini embedContent failed [%d]: %s", response.status_code, response.text)
                raise RuntimeError(f"Gemini embeddings API error ({response.status_code}): {response.text}")

            data = response.json()
            embeddings = data.get("embeddings", [])
            for item in embeddings:
                all_embeddings.append(item.get("values", []))

            # Small throttle between batches to stay well within free-tier RPM
            time.sleep(0.5)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        url = f"{self.base_url}/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": self.model,
            "content": {"parts": [{"text": text}]},
        }
        max_retries = 3
        for attempt in range(max_retries):
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding", {}).get("values", [])
            if response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            logger.error("Gemini query embedding failed [%d]: %s", response.status_code, response.text)
            raise RuntimeError(f"Gemini query embedding API error ({response.status_code}): {response.text}")
        return []
