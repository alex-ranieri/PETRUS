import { useState } from "react";
import LocalModelSelect from "./LocalModelSelect";
import { useTranslation } from "react-i18next";
import { engine, errorMessage, type Settings } from "../services/api";

export default function AISettings({
  settings,
  onSave,
  onError,
}: {
  settings: Settings;
  onSave: (s: Partial<Settings>) => Promise<void>;
  onError: (s: string) => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState({
    embedding_provider: settings.embedding_provider,
    embedding_endpoint: settings.embedding_endpoint,
    embedding_model: settings.embedding_model,
    embedding_max_chars: settings.embedding_max_chars,
    llm_provider: settings.llm_provider,
    llm_endpoint: settings.llm_endpoint,
    llm_model: settings.llm_model,
    llm_temperature: settings.llm_temperature,
    llm_max_output_tokens: settings.llm_max_output_tokens ?? 1600,
    llm_timeout_seconds: settings.llm_timeout_seconds ?? 90,
    llm_query_expansion: settings.llm_query_expansion,
  });
  const [embedding, setEmbedding] = useState<{
    state?: string;
    current?: number;
    error?: string;
  }>({});
  const [llm, setLlm] = useState<{ state?: string; error?: string }>({});
  async function check(kind: "embedding" | "llm") {
    try {
      await onSave(draft);
      const result = await engine<{
        state?: string;
        current?: number;
        error?: string;
      }>(
        kind === "llm" ? "llm_status" : "embedding_status",
        kind === "embedding" ? { check_connection: true } : {},
      );
      if (kind === "embedding")
        setEmbedding({ ...result, state: result.state || "available" });
      else setLlm(result);
    } catch (error) {
      onError(errorMessage(error));
    }
  }
  return (
    <>
      <h2>{t("ai.localProviders")}</h2>
      <p className="hint">{t("ai.localOnly")}</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSave(draft);
        }}
      >
        {(["embedding", "llm"] as const).map((kind) => (
          <fieldset key={kind} className="settings-card ai-fields">
            <legend>{t(`ai.${kind}`)}</legend>
            <label>
              {t("ai.provider")}
              <select
                value={draft[`${kind}_provider`]}
                onChange={(e) =>
                  setDraft({ ...draft, [`${kind}_provider`]: e.target.value })
                }
              >
                <option value="none">{t("ai.none")}</option>
                <option value="lmstudio">{t("ai.lmstudio")}</option>
                {kind === "llm" && (
                  <option value="openai_compatible">
                    {t("ai.openaiCompatible")}
                  </option>
                )}
              </select>
            </label>
            <label>
              {t("ai.endpoint")}
              <input
                value={draft[`${kind}_endpoint`]}
                placeholder={
                  kind === "llm" && draft.llm_provider === "lmstudio"
                    ? "http://127.0.0.1:1234"
                    : "http://127.0.0.1:1234/v1"
                }
                onChange={(e) =>
                  setDraft({ ...draft, [`${kind}_endpoint`]: e.target.value })
                }
              />
            </label>
            {draft[`${kind}_provider`] === "lmstudio" ? (
              <LocalModelSelect
                category={kind}
                endpoint={draft[`${kind}_endpoint`]}
                value={draft[`${kind}_model`]}
                onChange={(id) => setDraft({ ...draft, [`${kind}_model`]: id })}
              />
            ) : (
              <label>
                {t("ai.model")}
                <input
                  value={draft[`${kind}_model`]}
                  onChange={(e) =>
                    setDraft({ ...draft, [`${kind}_model`]: e.target.value })
                  }
                />
              </label>
            )}
            {kind === "llm" && (
              <>
                <label>
                  {t("ai.temperature")}
                  <input
                    type="number"
                    min={0}
                    max={draft.llm_provider === "lmstudio" ? 1 : 2}
                    step={0.1}
                    value={draft.llm_temperature}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        llm_temperature: Number(e.target.value),
                      })
                    }
                  />
                </label>
                {draft.llm_provider === "lmstudio" && (
                  <>
                    <label>
                      {t("ai.outputTokens")}
                      <input
                        type="number"
                        min={128}
                        max={8192}
                        step={1}
                        value={draft.llm_max_output_tokens}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            llm_max_output_tokens: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    <label>
                      {t("ai.timeoutSeconds")}
                      <input
                        type="number"
                        min={5}
                        max={600}
                        step={1}
                        value={draft.llm_timeout_seconds}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            llm_timeout_seconds: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    <p className="hint">{t("ai.outputBudgetHint")}</p>
                  </>
                )}
                <label>
                  <input
                    type="checkbox"
                    checked={draft.llm_query_expansion}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        llm_query_expansion: e.target.checked,
                      })
                    }
                  />
                  {t("ai.expandQuery")}
                </label>
              </>
            )}
            {kind === "embedding" && (
              <label>
                {t("ai.maxChars")}
                <input
                  type="number"
                  min={100}
                  max={100000}
                  value={draft.embedding_max_chars}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      embedding_max_chars: Number(e.target.value),
                    })
                  }
                />
              </label>
            )}
            <button type="button" onClick={() => void check(kind)}>
              {t("ai.check")}
            </button>
            {(kind === "llm" ? llm.state : embedding.state) && (
              <p role="status">
                {t("ai.status")}:{" "}
                {t(`ai.state.${kind === "llm" ? llm.state : embedding.state}`)}
              </p>
            )}
            {kind === "embedding" && embedding.current !== undefined && (
              <p>{t("ai.indexStatus", { count: embedding.current })}</p>
            )}
            {(kind === "llm" ? llm.error : embedding.error) && (
              <code>{kind === "llm" ? llm.error : embedding.error}</code>
            )}
          </fieldset>
        ))}
        <button className="primary">{t("ai.save")}</button>
      </form>
    </>
  );
}
