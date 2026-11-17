import AISettings from "./AISettings";
import { version as APP_VERSION } from "../../../package.json";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import {
  Plus,
  RotateCw,
  Trash2,
  Folder,
  Monitor,
  Moon,
  Sun,
  ShieldCheck,
  Database,
  HardDrive,
  FileText,
} from "lucide-react";
import PetrusLogo from "./PetrusLogo";
import { label } from "../i18n";
import {
  dateLabel,
  engine,
  errorMessage,
  type Snapshot,
  type Settings as Preferences,
} from "../services/api";

export function About() {
  const { t: tx } = useTranslation();

  return (
    <div className="about">
      <PetrusLogo variant="hero" />
      <span className="eyebrow">
        {tx("copy.your_local_research_companion_07f72")}
      </span>
      <h1>
        {tx("copy.petrus_40fce")}
        <span className="version">{APP_VERSION}</span>
      </h1>
      <p>
        {tx("copy.publication_evidence_tracking_03b31")} <br />
        {tx("copy.retrieval_understanding_amp_synthesis_86877")}{" "}
      </p>
      <h3>
        {tx("copy.follow_the_connections_a317e")} <br />
        {tx("copy.find_the_evidence_175c5")}{" "}
      </h3>
      <div className="privacy-tag">
        <ShieldCheck size={15} />{" "}
        {tx("copy.local_by_design_yours_by_default_9a5e5")}{" "}
      </div>
      <p className="hint">
        {tx("copy.built_for_curious_minds_and_traceable_research_40df1")} <br />
        {tx("copy.no_account_no_telemetry_no_cloud_uploads_1930b")}{" "}
      </p>
    </div>
  );
}

export default function Settings({
  snapshot,
  initialTab,
  onAddLibrary,
  onRescan,
  onRemove,
  onSave,
  onError,
  onReprocess,
}: {
  snapshot: Snapshot;
  initialTab: string;
  onAddLibrary: () => void;
  onRescan: (id: number) => void;
  onRemove: (id: number) => void;
  onSave: (settings: Partial<Preferences>) => Promise<void>;
  onError: (message: string) => void;
  onReprocess: (id: number) => void;
}) {
  const { t: tx } = useTranslation();

  const [tab, setTab] = useState(initialTab);
  const settings = snapshot.settings;
  const [endpoint, setEndpoint] = useState(settings.grobid_endpoint);
  const [health, setHealth] = useState(snapshot.grobid.state);
  const tabs = [
    "General",
    "Libraries",
    "AI",
    "Indexing",
    "Appearance",
    "About",
  ];
  return (
    <div className="settings-layout">
      <nav
        className="settings-nav"
        aria-label={tx("copy.settings_sections_2e710")}
      >
        {tabs.map((t) => (
          <button
            className={tab === t ? "active" : ""}
            key={label(t)}
            onClick={() => setTab(t)}
          >
            {label(t)}
          </button>
        ))}
      </nav>
      <div className="settings-content">
        {tab === "General" && (
          <>
            <h2>{tx("copy.your_local_workspace_ba6ac")}</h2>
            <p className="subtext">
              {tx("copy.your_library_settings_and_research_stay_on_429ec")}{" "}
            </p>
            <div className="settings-card language-setting">
              <label>
                {tx("general.language")}
                <select
                  aria-label={tx("general.language")}
                  value={settings.language}
                  onChange={(e) =>
                    onSave({
                      language: e.target.value as Preferences["language"],
                    })
                  }
                >
                  <option value="system">{tx("general.systemDefault")}</option>
                  <option value="en" lang="en">
                    {tx("general.english")}
                  </option>
                  <option value="pt-BR" lang="pt-BR">
                    {tx("general.portuguese")}
                  </option>
                </select>
              </label>
              <p className="hint">{tx("general.languageHelp")}</p>
            </div>
            <div className="settings-card">
              <div className="setting-path">
                <Database size={20} />
                <div>
                  <h3>{tx("copy.database_location_db2e3")}</h3>
                  <code>
                    {snapshot.database_path ||
                      tx("copy.connect_the_desktop_engine_to_view_the_0b214")}
                  </code>
                </div>
              </div>
              <div className="setting-path">
                <HardDrive size={20} />
                <div>
                  <h3>{tx("copy.application_data_922d1")}</h3>
                  <code>
                    {snapshot.data_dir ||
                      tx("copy.managed_by_the_desktop_app_a9964")}
                  </code>
                </div>
              </div>
            </div>
            <div className="notice">
              <ShieldCheck size={18} />
              <span>
                {tx(
                  "copy.petrus_stores_references_to_your_original_files_4ebe4",
                )}{" "}
              </span>
            </div>
          </>
        )}
        {tab === "Libraries" && (
          <>
            <div className="section-heading">
              <div>
                <h2>{tx("copy.research_libraries_cf4e5")}</h2>
                <p className="subtext">
                  {tx(
                    "copy.folders_connected_to_your_local_catalog_b241a",
                  )}{" "}
                </p>
              </div>
              <button className="primary" onClick={onAddLibrary}>
                <Plus size={16} /> {tx("copy.add_library_9d612")}{" "}
              </button>
            </div>
            {snapshot.libraries.length ? (
              snapshot.libraries.map((l) => (
                <div className="library-setting" key={l.id}>
                  <Folder size={22} />
                  <div>
                    <h3>{l.name}</h3>
                    <p className="path">{l.root_path}</p>
                    <small>
                      {l.file_count} {tx("copy.files_last_scan_8bfe1")}{" "}
                      {dateLabel(l.last_scan_at)}
                    </small>
                  </div>
                  <button
                    className="icon-button"
                    title={tx("library.rescan", { name: l.name })}
                    onClick={() => onRescan(l.id)}
                  >
                    <RotateCw size={16} />
                  </button>
                  <button
                    className="icon-button"
                    title={tx("scientific.reprocess")}
                    onClick={() => onReprocess(l.id)}
                  >
                    <FileText size={16} />
                  </button>
                  <button
                    className="icon-button danger"
                    title={tx("library.remove", { name: l.name })}
                    onClick={() => onRemove(l.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <Folder size={30} />
                <h3>{tx("copy.no_libraries_connected_cb680")}</h3>
                <p>
                  {tx("copy.choose_a_folder_to_start_cataloging_your_7f94a")}
                </p>
              </div>
            )}
          </>
        )}
        {tab === "AI" && (
          <AISettings settings={settings} onSave={onSave} onError={onError} />
        )}
        {tab === "Indexing" && (
          <>
            <h2>{tx("copy.a_library_that_keeps_up_1932f")}</h2>
            <p className="subtext">
              {tx(
                "copy.control_when_petrus_checks_your_connected_folders_8edb2",
              )}{" "}
            </p>
            <div className="settings-card">
              <label className="toggle-row">
                <span>
                  <strong>{tx("copy.scan_on_launch_0e628")}</strong>
                  <small>
                    {tx("copy.check_all_libraries_when_petrus_starts_120e4")}
                  </small>
                </span>
                <input
                  type="checkbox"
                  role="switch"
                  checked={settings.auto_scan}
                  onChange={(e) => onSave({ auto_scan: e.target.checked })}
                />
              </label>
              <label className="toggle-row">
                <span>
                  <strong>{tx("copy.watch_folders_ba83f")}</strong>
                  <small>
                    {tx("copy.check_every_60_seconds_while_the_app_78a3c")}{" "}
                  </small>
                </span>
                <input
                  type="checkbox"
                  role="switch"
                  checked={settings.watch_folders}
                  onChange={(e) => onSave({ watch_folders: e.target.checked })}
                />
              </label>
            </div>
            <div className="notice">
              {tx("copy.text_is_extracted_from_up_to_300_4112f")}{" "}
            </div>
            <section className="scientific-settings settings-card">
              <h3>{tx("scientific.parser")}</h3>
              <label>
                {tx("scientific.parser")}
                <select
                  value={settings.scientific_parser}
                  onChange={(e) =>
                    onSave({
                      scientific_parser: e.target
                        .value as Preferences["scientific_parser"],
                    })
                  }
                >
                  <option value="simple">{tx("scientific.simple")}</option>
                  <option value="grobid">{tx("scientific.grobid")}</option>
                </select>
              </label>
              <label>
                {tx("scientific.endpoint")}
                <input
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  onBlur={() => onSave({ grobid_endpoint: endpoint })}
                />
              </label>
              <div className="button-row">
                <button
                  className="secondary"
                  onClick={() => {
                    void engine("save_settings", { grobid_endpoint: endpoint })
                      .then(() => engine<{ state: string }>("grobid_health"))
                      .then((result) => setHealth(result.state))
                      .catch((e) => onError(errorMessage(e)));
                  }}
                >
                  {tx("scientific.check")}
                </button>
                <span className={"status " + health}>{label(health)}</span>
              </div>
              <label className="inline-checkbox">
                <input
                  type="checkbox"
                  checked={settings.grobid_fallback}
                  onChange={(e) =>
                    onSave({ grobid_fallback: e.target.checked })
                  }
                />
                {tx("scientific.fallback")}
              </label>
              <p className="hint">{tx("scientific.localOnly")}</p>
            </section>
          </>
        )}
        {tab === "Appearance" && (
          <>
            <h2>{tx("copy.make_room_for_focus_15b53")}</h2>
            <p className="subtext">
              {tx("copy.choose_the_appearance_that_feels_right_for_1f5db")}{" "}
            </p>
            <div className="theme-options">
              {(
                [
                  { value: "system", label: "System", icon: Monitor },
                  { value: "light", label: "Light", icon: Sun },
                  { value: "dark", label: "Dark", icon: Moon },
                ] as const
              ).map((t) => (
                <button
                  key={t.value}
                  className={settings.theme === t.value ? "selected" : ""}
                  onClick={() => onSave({ theme: t.value })}
                >
                  <div className={`theme-preview ${t.value}`}>
                    <i />
                    <span>
                      <b />
                      <b />
                      <b />
                    </span>
                  </div>
                  <span>
                    <t.icon size={17} />
                    {label(t.label)}
                  </span>
                </button>
              ))}
            </div>
            <p className="hint">
              {tx("copy.system_follows_the_appearance_set_in_your_ef4af")}{" "}
            </p>
          </>
        )}
        {tab === "About" && <About />}
      </div>
    </div>
  );
}
