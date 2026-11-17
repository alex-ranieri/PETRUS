"""Stateless LM Studio REST v1 chat; only final message items cross the boundary."""

import http.client
import json

from petrus_engine.llm.catalog import fetch_models, native_endpoint, reasoning_capability
from petrus_engine.llm.local import LLMProviderError, OpenAICompatibleLLMProvider, http_error


class LMStudioNativeLLMProvider(OpenAICompatibleLLMProvider):
    """Reuse the existing evidence prompt/expansion contract, replace HTTP and parsing."""

    def __init__(
        self,
        model_id,
        endpoint="http://127.0.0.1:1234",
        temperature=0.1,
        timeout=90,
        reasoning="off",
        context_length=8192,
        max_output_tokens=1600,
    ):
        host, port = native_endpoint(endpoint)
        address = f"[{host}]" if ":" in host else host
        super().__init__(model_id, f"http://{address}:{port}/v1", temperature, timeout)
        if temperature > 1:
            raise ValueError("llm_invalid_temperature")
        if reasoning not in ("off", "on", "low", "medium", "high"):
            raise ValueError("llm_invalid_reasoning")
        if type(context_length) is not int or not 512 <= context_length <= 262144:
            raise ValueError("llm_invalid_context_length")
        if type(max_output_tokens) is not int or not 128 <= max_output_tokens <= 8192:
            raise ValueError("llm_invalid_output_limit")
        if type(timeout) is not int or not 5 <= timeout <= 600:
            raise ValueError("llm_invalid_timeout")
        self.max_output_tokens = max_output_tokens
        self.provider_id = f"lmstudio-native:{self.host}:{self.port}/api/v1"
        self.reasoning, self.context_length = reasoning, context_length
        self.last_metadata = {}
        self._model = None

    def _get_model(self):
        """Resolve capabilities once per provider, never infer them from a model name."""
        if self._model is not None:
            return self._model
        address = f"[{self.host}]" if ":" in self.host else self.host
        models = fetch_models(f"http://{address}:{self.port}")
        self._model = next(
            (m for m in models if m.get("key") == self.model_id and m.get("type") == "llm"), None
        )
        if self._model is None:
            raise ValueError("llm_model_not_served")
        return self._model

    def complete(self, messages, json_mode=True, *, schema=None):
        # Native chat has no documented response_format. Existing prompts request strict JSON.
        del json_mode, schema
        self.last_metadata = {}
        if any(m.get("role") not in ("system", "user") for m in messages):
            raise ValueError("llm_invalid_messages")
        capability = reasoning_capability(self._get_model())
        present = capability["present"]
        self.last_metadata.update(reasoning_capability_present=present, reasoning_parameter_sent=False)
        if present and capability["can_disable"] is not True:
            raise ValueError("llm_reasoning_cannot_be_disabled")
        body = {
            "model": self.model_id,
            "system_prompt": "\n\n".join(m["content"] for m in messages if m["role"] == "system"),
            "input": [{"type": "text", "content": m["content"]} for m in messages if m["role"] == "user"],
            "temperature": self.temperature,
            "context_length": self.context_length,
            "max_output_tokens": self.max_output_tokens,
            "store": False,
            "stream": False,
        }
        if present:
            body["reasoning"] = "off"
            self.last_metadata["reasoning_parameter_sent"] = True
        c = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            c.request("POST", "/api/v1/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
            r = c.getresponse()
            self.last_metadata["http_status"] = r.status
            if not 200 <= r.status < 300:
                raise http_error(r, messages)
            raw = r.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("llm_response_too_large")
            value = json.loads(raw)
            output = value["output"]
            if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
                raise ValueError("llm_invalid_response")
            stats = value.get("stats", {})
            if not isinstance(stats, dict):
                raise TypeError("llm_invalid_response")
            self.last_metadata.update(
                model_instance_id=value.get("model_instance_id"),
                output_types=[item.get("type") for item in output],
                reasoning_output_items=sum(item.get("type") == "reasoning" for item in output),
                stats={
                    key: stats[key]
                    for key in (
                        "input_tokens",
                        "total_output_tokens",
                        "reasoning_output_tokens",
                        "message_output_tokens",
                        "tokens_per_second",
                        "time_to_first_token_seconds",
                        "model_load_time_seconds",
                    )
                    if isinstance(stats.get(key), (int, float)) and not isinstance(stats[key], bool)
                },
            )
            metrics = self.last_metadata["stats"]
            reasoning_tokens, total_tokens = metrics.get("reasoning_output_tokens"), metrics.get("total_output_tokens")
            if reasoning_tokens is not None and total_tokens is not None and total_tokens > 0:
                metrics["reasoning_fraction"] = reasoning_tokens / total_tokens
            texts = [item["content"] for item in output if item.get("type") == "message"]
            if any(not isinstance(text, str) for text in texts):
                raise ValueError("llm_invalid_response")
            # REST v1 documents multiple message segments; preserve their order, never reasoning.
            content = "\n\n".join(text for text in texts if text.strip())
            self.last_metadata["content_characters"] = len(content)
            if not content.strip():
                raise ValueError("llm_empty_response")
            return content
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("llm_invalid_response") from exc
        finally:
            c.close()

    def status(self):
        try:
            model = self._get_model()
            reply = self.complete([{"role": "user", "content": "Reply only OK."}], json_mode=False)
            return {
                "state": "available",
                "model_id": self.model_id,
                "provider_id": self.provider_id,
                "minimal_response": reply[:80],
                "model_instances_before": model.get("loaded_instances", []),
                "reasoning": "off" if self.last_metadata["reasoning_parameter_sent"] else None,
                "context_length": self.context_length,
                **self.last_metadata,
            }
        except (OSError, ValueError, http.client.HTTPException, KeyError, IndexError, TypeError) as exc:
            result = {"state": "error", "model_id": self.model_id, "error": str(exc), **self.last_metadata}
            if isinstance(exc, LLMProviderError):
                result["provider_error"] = exc.diagnostic()
            return result
