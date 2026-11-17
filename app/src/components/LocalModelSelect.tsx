import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  engine,
  type LocalModelInfo,
  type ModelCatalogResponse,
} from "../services/api";

export default function LocalModelSelect({
  category,
  endpoint,
  value,
  onChange,
}: {
  category: "llm" | "embedding";
  endpoint: string;
  value: string;
  onChange: (id: string) => void;
}) {
  const { t } = useTranslation();
  const [catalog, setCatalog] = useState<LocalModelInfo[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [custom, setCustom] = useState(false);
  const request = useRef(0);
  const invalidateRequests = useCallback(() => {
    request.current++;
  }, []);
  const refresh = useCallback(async () => {
    const ticket = ++request.current;
    setLoading(true);
    setFailed(false);
    try {
      const response = await engine<ModelCatalogResponse>("llm_models", {
        endpoint: endpoint || "http://127.0.0.1:1234",
      });
      if (ticket === request.current) setCatalog(response.models);
    } catch {
      if (ticket === request.current) {
        setCatalog(null);
        setFailed(true);
      }
    } finally {
      if (ticket === request.current) setLoading(false);
    }
  }, [endpoint]);
  useEffect(() => {
    setCatalog(null);
    setFailed(false);
    const timer = setTimeout(() => void refresh(), 150);
    return () => {
      clearTimeout(timer);
      invalidateRequests();
    };
  }, [refresh, invalidateRequests]);
  const available = catalog?.filter((m) => m.category === category) ?? [];
  const unknown = catalog?.filter((m) => m.category === "unknown") ?? [];
  const visible = [...available, ...unknown];
  const configuredOutsideList = !!value && !visible.some((m) => m.id === value);
  const unavailable =
    (catalog !== null || failed) && !catalog?.some((m) => m.id === value);
  function title(model: LocalModelInfo) {
    const name =
      model.display_name && model.display_name !== model.id
        ? `${model.display_name} (${model.id})`
        : model.id;
    const details = [
      model.parameters,
      model.format,
      model.quantization,
      model.loaded === null
        ? null
        : t(model.loaded ? "ai.modelLoaded" : "ai.modelNotLoaded"),
      model.reasoning.can_disable === true
        ? t("ai.reasoningOffSupported")
        : null,
    ].filter(Boolean);
    return details.length ? `${name} — ${details.join(" · ")}` : name;
  }
  return (
    <div className="local-model-select" aria-busy={loading}>
      <label>
        {t(category === "llm" ? "ai.chatModel" : "ai.embeddingModel")}
        <select
          aria-label={t(
            category === "llm" ? "ai.chatModel" : "ai.embeddingModel",
          )}
          value={custom ? "custom" : value ? `model:${value}` : ""}
          onChange={(event) => {
            if (event.target.value === "custom") setCustom(true);
            else {
              setCustom(false);
              onChange(event.target.value.replace(/^model:/, ""));
            }
          }}
        >
          <option value="">{t("ai.selectModel")}</option>
          {configuredOutsideList && (
            <option value={`model:${value}`}>
              {value}
              {unavailable ? ` — ${t("ai.configuredUnavailable")}` : ""}
            </option>
          )}
          {available.map((model) => (
            <option key={model.id} value={`model:${model.id}`}>
              {title(model)}
            </option>
          ))}
          {unknown.length > 0 && (
            <optgroup label={t("ai.unknownModels")}>
              {unknown.map((model) => (
                <option key={model.id} value={`model:${model.id}`}>
                  {title(model)}
                </option>
              ))}
            </optgroup>
          )}
          <option value="custom">{t("ai.customModel")}</option>
        </select>
      </label>
      {custom && (
        <label>
          {t("ai.customModel")}
          <input
            value={value}
            onChange={(event) => onChange(event.target.value)}
          />
        </label>
      )}
      <button type="button" disabled={loading} onClick={() => void refresh()}>
        {t(loading ? "ai.loadingModels" : "ai.refreshModels")}
      </button>
      {failed && (
        <p role="status" className="hint">
          {t("ai.modelsUnavailable")}
        </p>
      )}
      {!failed && catalog !== null && visible.length === 0 && (
        <p role="status" className="hint">
          {t("ai.noModels")}
        </p>
      )}
    </div>
  );
}
