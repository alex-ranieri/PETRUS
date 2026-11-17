"""Local OpenAI-compatible embeddings; no SDK, redirects, proxies or external endpoints."""

import http.client
import json
from urllib.parse import urlsplit


def local_endpoint(endpoint):
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
        or parsed.username
        or parsed.password
        or parsed.path.rstrip("/") != "/v1"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("embedding_local_endpoint_required")
    host = "127.0.0.1" if parsed.hostname == "localhost" else parsed.hostname
    port = parsed.port or 80
    if not 1 <= port <= 65535:
        raise ValueError("embedding_invalid_port")
    return host, port


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, model_id, endpoint="http://127.0.0.1:1234/v1", max_chars=6000, timeout=30):
        self.host, self.port = local_endpoint(endpoint)
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("embedding_model_required")
        if type(max_chars) is not int or max_chars < 1:
            raise ValueError("embedding_invalid_text_limit")
        self.model_id = model_id
        # Different local services may expose different models under the same name.
        self.provider_id = f"lmstudio:{self.host}:{self.port}/v1"
        self.dimension = None
        self.max_chars, self.timeout = max_chars, timeout

    def embed_documents(self, texts):
        if not texts:
            return []
        if any(not text.strip() or len(text) > self.max_chars for text in texts):
            raise ValueError("embedding_text_limit")
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            body = json.dumps({"model": self.model_id, "input": list(texts), "encoding_format": "float"})
            connection.request("POST", "/v1/embeddings", body.encode(), {"Content-Type": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError("embedding_provider_response")
            raw = response.read(16_000_001)
            if len(raw) > 16_000_000:
                raise ValueError("embedding_response_size_limit")
            data = json.loads(raw)
            if data.get("model") not in (None, self.model_id):
                raise ValueError("embedding_model_mismatch")
            items = data["data"]
            if len(items) != len(texts) or sorted(item["index"] for item in items) != list(range(len(texts))):
                raise ValueError("embedding_response_indices")
            from petrus_engine.rag.index import checked_vector

            vectors = [
                checked_vector(item["embedding"], self.dimension)
                for item in sorted(items, key=lambda item: item["index"])
            ]
            dimension = len(vectors[0])
            if any(len(vector) != dimension for vector in vectors):
                raise ValueError("embedding_dimension_mismatch")
            self.dimension = dimension
            return [vector.tolist() for vector in vectors]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("embedding_invalid_response") from exc
        finally:
            connection.close()

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def configured_provider(settings):
    provider = settings.get("embedding_provider", "none")
    if provider == "none":
        return None
    if provider != "lmstudio":
        raise ValueError("embedding_unsupported_provider")
    return OpenAICompatibleEmbeddingProvider(
        settings.get("embedding_model", ""),
        settings.get("embedding_endpoint") or "http://127.0.0.1:1234/v1",
        settings.get("embedding_max_chars", 6000),
    )
