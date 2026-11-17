"""Read-only LM Studio native catalog; no model load, inference, proxy or redirects."""

import http.client
import json
from urllib.parse import urlsplit, urlunsplit

from petrus_engine.llm.local import http_error
from petrus_engine.rag.providers import local_endpoint


def native_endpoint(endpoint):
    if not isinstance(endpoint, str):
        raise ValueError("llm_local_endpoint_required")
    parsed = urlsplit(endpoint)
    if parsed.path.rstrip("/") not in ("", "/v1"):
        raise ValueError("llm_local_endpoint_required")
    try:
        return local_endpoint(urlunsplit(parsed._replace(path="/v1")))
    except ValueError as exc:
        raise ValueError("llm_local_endpoint_required") from exc


def reasoning_capability(model):
    """One interpretation shared by discovery and the inference request policy."""
    capabilities = model.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise ValueError("llm_invalid_response")
    present = "reasoning" in capabilities
    value = capabilities.get("reasoning")
    options = value.get("allowed_options", []) if isinstance(value, dict) else []
    return {"present": present, "can_disable": isinstance(options, list) and "off" in options if present else None}


def fetch_models(endpoint):
    host, port = native_endpoint(endpoint)
    connection = http.client.HTTPConnection(host, port, timeout=3)
    try:
        connection.request("GET", "/api/v1/models")
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise http_error(response)
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("llm_response_too_large")
        models = json.loads(raw)["models"]
        if not isinstance(models, list):
            raise ValueError("llm_invalid_response")
        return [model for model in models if isinstance(model, dict)]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("llm_invalid_response") from exc
    finally:
        connection.close()


def optional_text(value):
    return value if isinstance(value, str) and len(value) <= 4096 else None


def model_catalog(endpoint):
    output, seen = [], set()
    for model in fetch_models(endpoint):
        identifier = model.get("key")
        if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 4096 or identifier in seen:
            continue
        seen.add(identifier)
        kind = optional_text(model.get("type"))
        quantization = model.get("quantization")
        if isinstance(quantization, dict):
            quantization = quantization.get("name")
        instances = model.get("loaded_instances")
        size = model.get("size_bytes")
        try:
            capability = reasoning_capability(model)
            reasoning = {"configurable": True if capability["present"] else None,
                         "can_disable": capability["can_disable"]}
        except ValueError:
            reasoning = {"configurable": None, "can_disable": None}
        output.append({
            "id": identifier,
            "display_name": optional_text(model.get("display_name")),
            "type": kind,
            "category": kind if kind in ("llm", "embedding") else "unknown",
            "architecture": optional_text(model.get("architecture")),
            "format": optional_text(model.get("format")),
            "parameters": optional_text(model.get("params_string")),
            "quantization": optional_text(quantization),
            "size_bytes": size if type(size) is int and size >= 0 else None,
            "loaded": bool(instances) if isinstance(instances, list) else None,
            "reasoning": reasoning,
        })
    return {"models": output}
