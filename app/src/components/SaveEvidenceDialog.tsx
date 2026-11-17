import { useState } from "react";
import { useTranslation } from "react-i18next";
import { engine, errorMessage, type Session } from "../services/api";

export default function SaveEvidenceDialog({
  sessions,
  initialSession,
  selectOnly,
  onConfirm,
  onCancel,
  onCreated,
  onError,
}: {
  sessions: Session[];
  initialSession: number | "";
  selectOnly: boolean;
  onConfirm: (id: number) => Promise<void>;
  onCancel: () => void;
  onCreated: () => Promise<void>;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation();
  const [available, setAvailable] = useState(sessions);
  const [selected, setSelected] = useState<number | "">(initialSession);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  async function create() {
    if (!title.trim()) return;
    setBusy(true);
    try {
      const result = await engine<{ id: number }>("new_session", {
        title,
        question: "",
        description: "",
      });
      setAvailable([
        ...available,
        {
          id: result.id,
          title: title.trim(),
          research_question: "",
          description: "",
          created_at: "",
        },
      ]);
      setSelected(result.id);
      setTitle("");
      await onCreated();
    } catch (error) {
      onError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={t(
          selectOnly ? "research.chooseTarget" : "research.saveToSession",
        )}
      >
        <h2>
          {t(selectOnly ? "research.chooseTarget" : "research.saveToSession")}
        </h2>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (!selected) return;
            setBusy(true);
            try {
              await onConfirm(selected);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            {t("research.session")}
            <select
              aria-label={t("research.session")}
              value={selected}
              onChange={(e) =>
                setSelected(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">{t("research.selectSession")}</option>
              {available.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("research.newSessionTitle")}
            <input
              value={title}
              maxLength={300}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={busy || !title.trim()}
            onClick={() => void create()}
          >
            {t("research.createSession")}
          </button>
          <div className="modal-actions">
            <button type="button" disabled={busy} onClick={onCancel}>
              {t("research.cancel")}
            </button>
            <button className="primary" disabled={busy || !selected}>
              {t(selectOnly ? "research.useSession" : "research.save")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
