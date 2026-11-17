import { useTranslation } from "react-i18next";
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { listen } from "@tauri-apps/api/event";
import {
  Home,
  LibraryBig,
  Network,
  Orbit,
  Settings as SettingsIcon,
  Plus,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowUpRight,
  ArrowRight,
  FolderPlus,
  FileText,
  Layers,
  CheckCheck,
  AlertCircle,
  ShieldCheck,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  X,
  RotateCw,
  Sun,
  Moon,
  Monitor,
  Folder,
  ListFilter,
  Check,
  LoaderCircle,
  Clock,
  CircleHelp,
} from "lucide-react";
import PetrusLogo from "./components/PetrusLogo";
import i18n, {
  preferredLocale,
  label,
  numberLabel,
  localizeMessage,
} from "./i18n";
import { invoke } from "@tauri-apps/api/core";
import {
  engine,
  emptySnapshot,
  errorMessage,
  pickLibrary,
  isTauri,
  dateLabel,
  jobLabel,
  type Snapshot,
  type Paper,
  type Settings as Preferences,
  type Session,
} from "./services/api";
const Graph = lazy(() => import("./components/Graph"));
import ResearchSessionWorkspace from "./components/ResearchSessionWorkspace";
import Ask from "./components/Ask";
import PaperPanel from "./components/PaperPanel";
import Settings, { About } from "./components/Settings";

type View =
  "Home" | "Library" | "Explore" | "Research" | "Settings" | "About" | "Ask";
type Filters = {
  year: string;
  author: string;
  journal: string;
  status: string;
  collection: string;
};
const noFilters: Filters = {
  year: "",
  author: "",
  journal: "",
  status: "",
  collection: "",
};

function BrandNetwork() {
  const { t: tx } = useTranslation();

  return (
    <div className="brand-network" aria-hidden="true">
      <svg viewBox="0 0 390 245">
        <defs>
          <radialGradient id="halo">
            <stop stopColor="var(--teal)" stopOpacity=".13" />
            <stop offset="1" stopColor="var(--teal)" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="215" cy="125" r="125" fill="url(#halo)" />
        <g stroke="currentColor" strokeWidth=".8" fill="none">
          <path d="M75 69 150 39 220 90 316 54 345 130 282 200 207 174 122 213 64 154 75 69 207 174 220 90 64 154M150 39 207 174 345 130 220 90 282 200M75 69 220 90 122 213" />
          <circle cx="207" cy="124" r="84" strokeDasharray="2 8" />
          <circle cx="207" cy="124" r="115" strokeDasharray="1 11" />
        </g>
        {[
          [75, 69],
          [150, 39],
          [220, 90],
          [316, 54],
          [345, 130],
          [282, 200],
          [207, 174],
          [122, 213],
          [64, 154],
        ].map(([x, y], i) => (
          <g key={i}>
            <circle
              cx={x}
              cy={y}
              r={i === 2 ? 12 : 6}
              fill={i % 3 === 0 ? "var(--gold)" : "var(--teal)"}
              fillOpacity=".13"
            />
            <circle
              cx={x}
              cy={y}
              r={i === 2 ? 4 : 2.6}
              fill={i % 3 === 0 ? "var(--gold)" : "var(--teal)"}
            />
          </g>
        ))}
      </svg>
      <span className="network-label">
        <span className="dot teal" />{" "}
        {tx("copy.curiosity_connected_1193a")}{" "}
      </span>
    </div>
  );
}

function PaperTable({
  papers,
  onPaper,
  compact = false,
}: {
  papers: Paper[];
  onPaper: (id: number) => void;
  compact?: boolean;
}) {
  const { t: tx } = useTranslation();

  return (
    <div className="table-scroll">
      <table className={compact ? "compact" : ""}>
        <thead>
          <tr>
            <th>{tx("copy.title_768e0")}</th>
            <th>{tx("copy.authors_d2a52")}</th>
            <th>{tx("copy.year_879e3")}</th>
            {!compact && (
              <>
                <th>{tx("copy.journal_57d7f")}</th>
                <th>{tx("copy.collection_30c54")}</th>
              </>
            )}
            <th>{tx("copy.status_bae7d")}</th>
          </tr>
        </thead>
        <tbody>
          {papers.map((p) => (
            <tr key={p.id}>
              <td>
                <button className="paper-title" onClick={() => onPaper(p.id)}>
                  <span className="pdf-icon">
                    <FileText size={16} />
                  </span>
                  <span>
                    {p.title}
                    <small>{p.doi || p.file_name}</small>
                  </span>
                </button>
              </td>
              <td>
                <span className="cell-truncate" title={p.authors || undefined}>
                  {p.authors || "—"}
                </span>
              </td>
              <td>{p.publication_year || "—"}</td>
              {!compact && (
                <>
                  <td>
                    <span
                      className="cell-truncate"
                      title={p.journal || undefined}
                    >
                      {p.journal || "—"}
                    </span>
                  </td>
                  <td>
                    {p.collections ? (
                      <span className="collection-chip">{p.collections}</span>
                    ) : (
                      "—"
                    )}
                  </td>
                </>
              )}
              <td>
                <div className="table-statuses">
                  <span className={`status ${p.status}`}>
                    {label(p.status)}
                  </span>
                  <span
                    className={`status ${p.scientific_status}`}
                    title={tx("scientific.status")}
                  >
                    {label(p.scientific_status)}
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const { t: tx } = useTranslation();

  const [view, setView] = useState<View>("Home");
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot);
  const [loaded, setLoaded] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [toast, setToast] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [fetching, setFetching] = useState(false);
  const [filters, setFilters] = useState<Filters>(noFilters);
  const [filtersVisible, setFiltersVisible] = useState(false);
  const [paperId, setPaperId] = useState<number | null>(null);
  const [modal, setModal] = useState<"session" | "collection" | null>(null);
  const [session, setSession] = useState<
    | (Session & {
        events: { id: number; event_type: string; created_at: string }[];
      })
    | null
  >(null);
  const [settingsTab, setSettingsTab] = useState("General");
  const [choosing, setChoosing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [systemDark, setSystemDark] = useState(
    window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const searchRef = useRef<HTMLInputElement>(null);
  const showError = useCallback((message: string) => setToast(message), []);
  const refresh = useCallback(async () => {
    try {
      const data = await engine<Snapshot>("snapshot");
      setSnapshot((prior) =>
        JSON.stringify(prior) === JSON.stringify(data) ? prior : data,
      );
      setConnectionError("");
    } catch (error) {
      setConnectionError(errorMessage(error));
    } finally {
      setLoaded(true);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (isTauri()) void refresh();
    }, 1600);
    return () => clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 9000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const change = () => setSystemDark(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    const locale = preferredLocale(
      snapshot.settings.language,
      snapshot.system_locale,
    );
    void i18n.changeLanguage(locale);
    document.documentElement.lang = locale;
    if (isTauri())
      void invoke("set_menu_language", { locale }).catch(() => undefined);
  }, [snapshot.settings.language, snapshot.system_locale]);
  const actualTheme =
    snapshot.settings.theme === "system"
      ? systemDark
        ? "dark"
        : "light"
      : snapshot.settings.theme;
  useEffect(() => {
    document.documentElement.dataset.theme = actualTheme;
  }, [actualTheme]);
  const revision =
    snapshot.jobs.map((j) => `${j.id}:${j.status}:${j.completed}`).join("|") +
    ":" +
    snapshot.collections.map((c) => `${c.id}:${c.paper_count}`).join(",");
  useEffect(() => {
    if (view !== "Home" && view !== "Library") return;
    let active = true;
    const timer = window.setTimeout(() => {
      setFetching(true);
      engine<{ papers: Paper[]; total: number }>(
        "papers",
        view === "Home"
          ? { limit: 5 }
          : { ...filters, query, offset: page * 100, limit: 100 },
      )
        .then((data) => {
          if (active) {
            setPapers(data.papers);
            setTotal(data.total);
          }
        })
        .catch((error) => {
          if (isTauri()) showError(errorMessage(error));
        })
        .finally(() => {
          if (active) setFetching(false);
        });
    }, 160);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [view, filters, query, page, revision, snapshot.stats.papers, showError]);
  const navigate = useCallback((next: View) => {
    setView(next);
    setPaperId(null);
    if (next !== "Ask") setSession(null);
    if (next === "Library") {
      setFilters(noFilters);
      setQuery("");
      setPage(0);
    }
  }, []);
  const addLibrary = useCallback(async () => {
    if (choosing) return;
    setChoosing(true);
    try {
      const path = await pickLibrary();
      if (path) {
        await engine("add_library", { path });
        await refresh();
        setView("Library");
        setQuery("");
        setFilters(noFilters);
        setPage(0);
      }
    } catch (error) {
      showError(errorMessage(error));
    } finally {
      setChoosing(false);
    }
  }, [choosing, refresh, showError]);
  const focusSearch = useCallback(() => {
    setView("Library");
    searchRef.current?.focus();
  }, []);
  const openSettings = useCallback(() => {
    setSettingsTab("General");
    setView("Settings");
    setPaperId(null);
  }, []);
  useEffect(() => {
    if (!isTauri()) return;
    const unlisten = listen<string>("menu-action", (event) => {
      if (event.payload === "add-library") void addLibrary();
      if (event.payload === "search") focusSearch();
      if (event.payload === "settings") openSettings();
      if (event.payload === "about") navigate("About");
    });
    return () => {
      void unlisten.then((fn) => fn());
    };
  }, [addLibrary, focusSearch, openSettings, navigate]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModal(null);
        setSession(null);
      }
      if (isTauri() || !(event.metaKey || event.ctrlKey)) return;
      if (event.key.toLowerCase() === "k") {
        event.preventDefault();
        focusSearch();
      }
      if (event.key.toLowerCase() === "o") {
        event.preventDefault();
        void addLibrary();
      }
      if (event.key === ",") {
        event.preventDefault();
        openSettings();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [addLibrary, focusSearch, openSettings]);
  const saveSettings = async (settings: Partial<Preferences>) => {
    try {
      await engine("save_settings", settings);
      await refresh();
    } catch (error) {
      showError(errorMessage(error));
    }
  };
  const rescan = async (id: number) => {
    try {
      await engine("rescan", { id });
      await refresh();
    } catch (error) {
      showError(errorMessage(error));
    }
  };
  const removeLibrary = async (id: number) => {
    try {
      await engine("remove_library", { id });
      await refresh();
    } catch (error) {
      showError(errorMessage(error));
    }
  };
  const selectPaper = useCallback((id: number) => setPaperId(id), []);
  const closePaper = useCallback(() => setPaperId(null), []);
  const changed = useCallback(() => {
    void refresh();
  }, [refresh]);
  const filter = (key: keyof Filters, value: string) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(0);
  };
  async function submitModal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      if (modal === "session")
        await engine("new_session", {
          title: data.get("title"),
          question: data.get("question"),
          description: data.get("description"),
        });
      else await engine("create_collection", { name: data.get("name") });
      await refresh();
      setModal(null);
    } catch (error) {
      showError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  const running = snapshot.jobs.find((j) =>
    ["running", "queued"].includes(j.status),
  );
  const activeCollection = snapshot.collections.find(
    (c) => String(c.id) === filters.collection,
  );
  const hasFilters = Object.values(filters).some(Boolean);
  const navItems = [
    { name: "Home", icon: Home },
    { name: "Library", icon: LibraryBig },
    { name: "Explore", icon: Network },
    { name: "Research", icon: Orbit },
  ] as const;

  return (
    <div className={`app ${collapsed ? "sidebar-collapsed" : ""}`}>
      <div className="titlebar" data-tauri-drag-region>
        <div className="window-title" data-tauri-drag-region>
          {tx("copy.petrus_40fce")} <span>/</span>{" "}
          {tx("copy.your_research_workspace_370d0")}{" "}
        </div>
        <span className="local-pill">
          <span className="dot teal" /> {tx("copy.local_first_611e2")}{" "}
        </span>
      </div>
      <aside className="sidebar">
        <button
          className="brand"
          title={tx("copy.petrus_home_1050c")}
          onClick={() => navigate("Home")}
        >
          <PetrusLogo variant={collapsed ? "small" : "medium"} />
          <span>
            {tx("copy.petrus_40fce")}
            <small>{tx("copy.follow_your_curiosity_728d8")}</small>
          </span>
        </button>
        <div className="workspace-label">{tx("copy.workspace_70398")}</div>
        <nav aria-label={tx("copy.main_navigation_efd19")}>
          {navItems.map((n) => (
            <button
              key={n.name}
              className={`nav-item ${view === n.name && !activeCollection ? "active" : ""}`}
              onClick={() => navigate(n.name)}
            >
              <n.icon size={18} strokeWidth={1.6} />
              <span>{label(n.name)}</span>
              {n.name === "Library" && <small>{snapshot.stats.papers}</small>}
            </button>
          ))}
        </nav>
        <div className="sidebar-divider" />
        <div className="collection-heading">
          <span>{tx("copy.collections_d938f")}</span>
          <button
            aria-label={tx("copy.new_collection_7c060")}
            title={tx("copy.new_collection_7c060")}
            onClick={() => setModal("collection")}
          >
            <Plus size={15} />
          </button>
        </div>
        <div className="collections-list">
          {snapshot.collections.length ? (
            snapshot.collections.map((c, i) => (
              <button
                key={c.id}
                title={c.name}
                className={`nav-item ${view === "Library" && filters.collection === String(c.id) ? "active" : ""}`}
                onClick={() => {
                  setView("Library");
                  setFilters({ ...noFilters, collection: String(c.id) });
                  setQuery("");
                  setPage(0);
                  setPaperId(null);
                }}
              >
                <span className={`collection-dot color-${i % 4}`} />
                <span>{c.name}</span>
                <small>{c.paper_count}</small>
              </button>
            ))
          ) : (
            <button
              className="create-collection"
              onClick={() => setModal("collection")}
            >
              <Plus size={14} />
              <span>{tx("copy.create_your_first_collection_e3eb6")}</span>
            </button>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="privacy-note">
            <ShieldCheck size={16} />
            <div>
              {tx("copy.your_research_stays_yours_c7edf")}
              <small>{tx("copy.stored_on_this_device_f6997")}</small>
            </div>
          </div>
          <button
            className={`nav-item ${view === "Settings" ? "active" : ""}`}
            onClick={openSettings}
          >
            <SettingsIcon size={18} strokeWidth={1.6} />
            <span>{tx("copy.settings_c7f73")}</span>
            <small>⌘ ,</small>
          </button>
          <div className="sidebar-foot">
            <button
              title={
                collapsed
                  ? tx("copy.expand_sidebar_f462e")
                  : tx("copy.collapse_sidebar_9e687")
              }
              onClick={() => setCollapsed((c) => !c)}
            >
              {collapsed ? (
                <PanelLeftOpen size={17} />
              ) : (
                <PanelLeftClose size={17} />
              )}
            </button>
            <span>{tx("copy.v0_1_0_f053d")}</span>
            <button
              aria-label={tx("copy.about_petrus_f0728")}
              title={tx("copy.about_petrus_f0728")}
              onClick={() => navigate("About")}
            >
              <CircleHelp size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="toolbar">
          <div className="breadcrumb">
            <span>{tx("copy.workspace_4ca0a")}</span>
            <ChevronRight size={13} />
            <strong>
              {activeCollection && view === "Library"
                ? activeCollection.name
                : label(view)}
            </strong>
          </div>
          <div className="search-box">
            <Search size={16} />
            <input
              ref={searchRef}
              aria-label={tx("copy.search_your_library_d9fa3")}
              placeholder={tx("copy.search_your_library_4b07d")}
              value={query}
              onFocus={() => {
                if (view !== "Library") {
                  setView("Library");
                  setPage(0);
                }
              }}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
            />
            {query ? (
              <button
                aria-label={tx("copy.clear_search_67300")}
                onClick={() => setQuery("")}
              >
                <X size={14} />
              </button>
            ) : (
              <kbd>{tx("copy.k_f1f00")}</kbd>
            )}
          </div>
          <button
            className="ask-placeholder"
            onClick={() => navigate("Ask")}
            title={tx("ask.title")}
          >
            <Sparkles size={15} />
            <span>{tx("copy.ask_petrus_878c1")}</span>
          </button>
        </header>
        <main>
          {connectionError && (
            <div className="connection-banner" role="status">
              <AlertCircle size={17} />
              <span>{localizeMessage(connectionError)}</span>
              {isTauri() && (
                <button onClick={() => void refresh()}>
                  {tx("copy.retry_9f5cd")}
                </button>
              )}
            </div>
          )}
          {view === "Home" && (
            <div className="page home-page">
              <div className="page-eyebrow">
                <span className="eyebrow">
                  {tx("copy.a_little_curiosity_a_clearer_picture_f0b63")}{" "}
                </span>
                <span className="home-date">
                  {tx("copy.your_workspace_d60ec")}
                </span>
              </div>
              <section className="hero">
                <div>
                  <div className="hero-brand">
                    <PetrusLogo variant="medium" />
                    {tx("copy.petrus_40fce")}{" "}
                    <span>{tx("copy.research_connected_b9c11")}</span>
                  </div>
                  <h1>
                    {tx("copy.follow_the_connections_a317e")} <br />
                    <em>{tx("copy.find_the_evidence_175c5")}</em>
                  </h1>
                  <p>
                    {tx("copy.a_home_for_your_papers_a_path_1b4b6")} <br />
                    {tx(
                      "copy.turn_your_local_library_into_a_connected_692f6",
                    )}{" "}
                  </p>
                  <button
                    className="primary"
                    disabled={choosing}
                    onClick={() => void addLibrary()}
                  >
                    <Plus size={16} />
                    {choosing
                      ? tx("copy.choosing_folder_34c91")
                      : tx("copy.add_library_9d612")}
                    <span className="button-shortcut">
                      {tx("copy.o_bd554")}
                    </span>
                  </button>
                </div>
                <BrandNetwork />
              </section>
              <div className="stats-grid">
                {[
                  {
                    label: "Papers",
                    value: snapshot.stats.papers,
                    icon: FileText,
                    color: "teal",
                  },
                  {
                    label: "Collections",
                    value: snapshot.stats.collections,
                    icon: Layers,
                    color: "gold",
                  },
                  {
                    label: "Indexed",
                    value: snapshot.stats.indexed,
                    icon: CheckCheck,
                    color: "blue",
                  },
                  {
                    label: "Needs attention",
                    value: snapshot.stats.attention,
                    icon: AlertCircle,
                    color: "peach",
                  },
                ].map((s) => (
                  <button
                    className="stat-card"
                    key={s.label}
                    onClick={() => {
                      navigate("Library");
                      if (s.label === "Needs attention") {
                        setFiltersVisible(true);
                        filter("status", "attention");
                      }
                      if (s.label === "Collections") setModal("collection");
                    }}
                  >
                    <div>
                      <span>{label(s.label)}</span>
                      <strong>{numberLabel(s.value)}</strong>
                    </div>
                    <s.icon size={20} strokeWidth={1.5} className={s.color} />
                  </button>
                ))}
              </div>
              {!snapshot.libraries.length ? (
                <section className="onboarding-card">
                  <PetrusLogo variant="hero" className="onboarding-logo" />
                  <div>
                    <span className="small-label">
                      {tx("copy.start_with_what_you_know_0d571")}{" "}
                    </span>
                    <h2>{tx("copy.choose_your_research_library_1551a")}</h2>
                    <p>
                      {tx("copy.select_a_folder_of_pdfs_petrus_will_56674")}{" "}
                      <br className="wide-only" />{" "}
                      {tx(
                        "copy.catalog_your_papers_and_keep_the_originals_db0c4",
                      )}{" "}
                    </p>
                    <div className="onboarding-trust">
                      <ShieldCheck size={14} /> {tx("copy.no_uploads_b32a9")}{" "}
                      <span>·</span> {tx("copy.no_duplicate_files_f8588")}{" "}
                      <span>·</span> {tx("copy.no_account_needed_997fb")}{" "}
                    </div>
                  </div>
                  <button
                    className="secondary"
                    disabled={choosing}
                    onClick={() => void addLibrary()}
                  >
                    {tx("copy.choose_folder_1838a")} <ArrowRight size={16} />
                  </button>
                </section>
              ) : (
                <section className="recent-section">
                  <div className="section-heading">
                    <h2>
                      {tx("copy.recently_added_53696")}{" "}
                      <span>{snapshot.stats.papers}</span>
                    </h2>
                    <button
                      className="text-button"
                      onClick={() => navigate("Library")}
                    >
                      {tx("copy.view_library_4b882")} <ArrowUpRight size={15} />
                    </button>
                  </div>
                  {papers.length ? (
                    <PaperTable
                      papers={papers.slice(0, 5)}
                      onPaper={selectPaper}
                      compact
                    />
                  ) : (
                    <div className="empty-state">
                      <FileText size={27} />
                      <p>
                        {running
                          ? tx("copy.your_first_papers_are_on_their_way_48c8a")
                          : tx(
                              "copy.no_pdfs_have_been_cataloged_check_your_9aa0f",
                            )}
                      </p>
                    </div>
                  )}
                </section>
              )}
              <div className="home-lower">
                <section>
                  <div className="section-heading">
                    <h2>{tx("copy.recent_activity_72d56")}</h2>
                    <span className="small-label">
                      {tx("copy.local_engine_70211")}
                    </span>
                  </div>
                  {snapshot.jobs.length ? (
                    <div className="activity-list">
                      {snapshot.jobs.slice(0, 3).map((j) => (
                        <div className="activity" key={j.id}>
                          <span
                            className={`activity-icon ${j.status === "completed" ? "teal" : ""}`}
                          >
                            {["running", "queued"].includes(j.status) ? (
                              <LoaderCircle size={16} className="spin" />
                            ) : j.status === "completed" ? (
                              <Check size={16} />
                            ) : (
                              <AlertCircle size={16} />
                            )}
                          </span>
                          <div>
                            <strong>{j.library_name}</strong>
                            <small>
                              {jobLabel(j)} · {j.completed}/{j.total}
                            </small>
                          </div>
                          <span className={`status ${j.status}`}>
                            {label(j.status)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="activity-empty">
                      <Clock size={19} />
                      <p>
                        {tx("copy.your_research_story_starts_here_c512c")}{" "}
                        <small>
                          {tx(
                            "copy.library_scans_and_indexing_activity_will_appear_cfccc",
                          )}{" "}
                        </small>
                      </p>
                    </div>
                  )}
                </section>
                <button
                  className="explore-card"
                  onClick={() => navigate("Explore")}
                >
                  <Network size={24} strokeWidth={1.3} />
                  <h3>{tx("copy.see_the_bigger_picture_307b1")}</h3>
                  <p>
                    {tx("copy.explore_how_your_papers_connect_069f0")} <br />
                    {tx("copy.through_authors_and_collections_6bce7")}{" "}
                  </p>
                  <span>
                    {tx("copy.open_explore_0630f")} <ArrowUpRight size={15} />
                  </span>
                </button>
              </div>
            </div>
          )}
          {view === "Library" && (
            <div className="page library-page">
              <div className="page-heading">
                <div>
                  <span className="eyebrow">
                    {tx("copy.your_knowledge_organized_7c1ca")}
                  </span>
                  <h1>
                    {activeCollection?.name || tx("copy.library_b8100")}
                    <span className="heading-count">{total}</span>
                  </h1>
                  <p className="subtext">
                    {tx("copy.every_paper_is_a_starting_point_find_c33f3")}{" "}
                  </p>
                </div>
                <button
                  className="primary"
                  disabled={choosing}
                  onClick={() => void addLibrary()}
                >
                  <Plus size={16} /> {tx("copy.add_library_9d612")}{" "}
                </button>
              </div>
              <div className="library-tools">
                <div className="view-toggle">
                  <span>
                    <LibraryBig size={15} /> {tx("copy.all_papers_6cacb")}{" "}
                  </span>
                  <span>
                    {fetching
                      ? tx("copy.searching_1a6a5")
                      : tx("library.results", { count: total })}
                  </span>
                </div>
                <button
                  className={`secondary ${filtersVisible || hasFilters ? "selected" : ""}`}
                  onClick={() => setFiltersVisible((v) => !v)}
                >
                  <ListFilter size={15} /> {tx("copy.filters_96e57")}{" "}
                  {hasFilters && (
                    <span className="filter-count">
                      {Object.values(filters).filter(Boolean).length}
                    </span>
                  )}
                </button>
              </div>
              {filtersVisible && (
                <div className="filters">
                  <select
                    aria-label={tx("copy.filter_by_year_5f974")}
                    value={filters.year}
                    onChange={(e) => filter("year", e.target.value)}
                  >
                    <option value="">{tx("copy.all_years_0977c")}</option>
                    {snapshot.facets.years.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                  <select
                    aria-label={tx("copy.filter_by_author_d85ca")}
                    value={filters.author}
                    onChange={(e) => filter("author", e.target.value)}
                  >
                    <option value="">{tx("copy.all_authors_58b0f")}</option>
                    {snapshot.facets.authors.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                  <select
                    aria-label={tx("copy.filter_by_journal_b0ea0")}
                    value={filters.journal}
                    onChange={(e) => filter("journal", e.target.value)}
                  >
                    <option value="">{tx("copy.all_journals_6b847")}</option>
                    {snapshot.facets.journals.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                  <select
                    aria-label={tx("copy.filter_by_collection_fdabb")}
                    value={filters.collection}
                    onChange={(e) => filter("collection", e.target.value)}
                  >
                    <option value="">{tx("copy.all_collections_1e8c0")}</option>
                    {snapshot.collections.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label={tx("copy.filter_by_status_f4365")}
                    value={filters.status}
                    onChange={(e) => filter("status", e.target.value)}
                  >
                    <option value="">{tx("copy.all_statuses_64051")}</option>
                    {[
                      "attention",
                      "ready",
                      "warning",
                      "failed",
                      "unavailable",
                      "processing",
                      "discovered",
                    ].map((v) => (
                      <option key={v} value={v}>
                        {label(v)}
                      </option>
                    ))}
                  </select>
                  {hasFilters && (
                    <button
                      className="text-button"
                      onClick={() => {
                        setFilters(noFilters);
                        setPage(0);
                      }}
                    >
                      {tx("copy.reset_44c57")}{" "}
                    </button>
                  )}
                </div>
              )}
              {running && (
                <div className="scan-banner">
                  <LoaderCircle size={17} className="spin" />
                  <div>
                    <strong>
                      {tx("copy.cataloging_28a37")} {running.library_name}
                    </strong>
                    <span>
                      {label(running.stage)} · {jobLabel(running)}
                    </span>
                  </div>
                  <progress
                    value={running.completed}
                    max={running.total || 1}
                  />
                  <small>
                    {running.completed}/{running.total}
                  </small>
                </div>
              )}
              {papers.length ? (
                <PaperTable papers={papers} onPaper={selectPaper} />
              ) : (
                <div className="library-empty">
                  <div className="empty-orbit">
                    <LibraryBig size={35} strokeWidth={1} />
                  </div>
                  <h2>
                    {query || hasFilters
                      ? tx("copy.no_matching_papers_a9a9d")
                      : running
                        ? tx("copy.discovering_your_library_ec5e2")
                        : tx("copy.make_space_for_your_next_discovery_e7f6c")}
                  </h2>
                  <p>
                    {query || hasFilters
                      ? tx("copy.try_a_different_phrase_or_adjust_your_8defc")
                      : tx("copy.connect_a_folder_of_scientific_pdfs_to_3f3b2")}
                  </p>
                  {!snapshot.libraries.length && (
                    <button
                      className="primary"
                      onClick={() => void addLibrary()}
                    >
                      <FolderPlus size={16} />{" "}
                      {tx("copy.choose_your_research_library_1551a")}{" "}
                    </button>
                  )}
                </div>
              )}
              <div className="table-footer">
                <span>
                  {total
                    ? tx("library.range", {
                        first: numberLabel(page * 100 + 1),
                        last: numberLabel(Math.min((page + 1) * 100, total)),
                        total: numberLabel(total),
                      })
                    : tx("copy.no_papers_to_show_3b755")}
                </span>
                <div>
                  <button
                    aria-label={tx("copy.previous_results_56a2b")}
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    aria-label={tx("copy.next_results_27011")}
                    disabled={(page + 1) * 100 >= total}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
              {!!snapshot.issues.length && (
                <details className="scan-issues">
                  <summary>
                    <AlertCircle size={15} /> {snapshot.issues_total}{" "}
                    {tx("copy.file_locations_need_attention_28ef3")}{" "}
                    {snapshot.issues_total > snapshot.issues.length
                      ? " · " +
                        tx("library.showingIssues", {
                          count: snapshot.issues.length,
                        })
                      : ""}
                  </summary>
                  {snapshot.issues.map((i) => (
                    <div key={i.id}>
                      <strong>{i.file_name}</strong>
                      <span>{localizeMessage(i.error)}</span>
                    </div>
                  ))}
                </details>
              )}
              {!!snapshot.libraries.length && (
                <div className="connected-libraries">
                  <span className="small-label">
                    {tx("copy.connected_folders_c02f1")}
                  </span>
                  {snapshot.libraries.map((l) => (
                    <button
                      key={l.id}
                      title={l.root_path}
                      onClick={() => void rescan(l.id)}
                    >
                      <Folder size={14} />
                      {l.name}
                      <RotateCw size={12} />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {view === "Explore" && (
            <div className="page explore-page">
              <div className="page-heading">
                <div>
                  <span className="eyebrow">
                    {tx("copy.follow_a_different_thread_f025d")}
                  </span>
                  <h1>{tx("copy.explore_b965a")}</h1>
                  <p className="subtext">
                    {tx("copy.a_wider_view_of_the_knowledge_in_94cd3")}{" "}
                  </p>
                </div>
                <span className="outline-label">
                  <span className="dot teal" />{" "}
                  {tx("copy.library_graph_1df55")}{" "}
                </span>
              </div>
              <Suspense
                fallback={
                  <div className="empty-state">
                    {tx("copy.loading_graph_a463e")}
                  </div>
                }
              >
                <Graph
                  onPaper={selectPaper}
                  onError={showError}
                  revision={revision}
                  theme={actualTheme}
                />
              </Suspense>
              <div className="graph-disclaimer">
                <ShieldCheck size={14} />{" "}
                {tx(
                  "copy.connections_show_shared_author_metadata_and_collections_b734b",
                )}{" "}
              </div>
            </div>
          )}
          {view === "Research" && (
            <div className="page research-page">
              <div className="page-heading">
                <div>
                  <span className="eyebrow">
                    {tx("copy.give_your_curiosity_a_direction_74509")}{" "}
                  </span>
                  <h1>{tx("copy.research_be601")}</h1>
                  <p className="subtext">
                    {tx("copy.start_with_a_question_keep_a_trail_31e3d")}{" "}
                  </p>
                </div>
                <button className="primary" onClick={() => setModal("session")}>
                  <Plus size={16} />{" "}
                  {tx("copy.new_research_session_f3a18")}{" "}
                </button>
              </div>
              {session ? (
                <div className="session-detail">
                  <button
                    className="text-button"
                    onClick={() => setSession(null)}
                  >
                    <ChevronLeft size={15} />{" "}
                    {tx("copy.all_sessions_6a5f3")}{" "}
                  </button>
                  <span className="small-label">
                    {tx("copy.research_session_62c0c")}{" "}
                    {dateLabel(session.created_at)}
                  </span>
                  <h2>{session.title}</h2>
                  <h4>{tx("copy.research_question_38b28")}</h4>
                  <p>
                    {session.research_question ||
                      tx("copy.no_question_recorded_yet_a4cb5")}
                  </p>
                  <h4>{tx("copy.description_0ceec")}</h4>
                  <p className="reading">
                    {session.description ||
                      tx("copy.an_open_space_for_your_next_idea_cad68")}
                  </p>
                  <ResearchSessionWorkspace
                    key={session.id}
                    sessionId={session.id}
                    onPaper={selectPaper}
                    onLibrary={(id) => {
                      navigate("Library");
                      selectPaper(id);
                    }}
                    onError={showError}
                    onChanged={async () => {
                      const updated = await engine<typeof session>("session", {
                        id: session.id,
                      });
                      setSession(updated);
                    }}
                  />
                </div>
              ) : snapshot.sessions.length ? (
                <div className="session-grid">
                  {snapshot.sessions.map((s) => (
                    <button
                      className="session-card"
                      key={s.id}
                      onClick={() => {
                        void engine<
                          Session & {
                            events: {
                              id: number;
                              event_type: string;
                              created_at: string;
                            }[];
                          }
                        >("session", { id: s.id })
                          .then(setSession)
                          .catch((e) => showError(errorMessage(e)));
                      }}
                    >
                      <Orbit size={23} />
                      <span className="small-label">
                        {tx("copy.research_session_ea0c6")}
                      </span>
                      <h3>{s.title}</h3>
                      <p>
                        {s.research_question ||
                          s.description ||
                          tx("copy.ready_for_your_next_question_2b1fa")}
                      </p>
                      <footer>
                        {dateLabel(s.created_at)}
                        <ArrowUpRight size={16} />
                      </footer>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="research-empty">
                  <div className="empty-orbit">
                    <Orbit size={40} strokeWidth={1} />
                  </div>
                  <span className="eyebrow">
                    {tx("copy.good_research_begins_with_a_question_70cf2")}{" "}
                  </span>
                  <h2>{tx("copy.what_will_you_explore_2fff9")}</h2>
                  <p>
                    {tx("copy.create_a_session_to_give_your_research_a48b6")}{" "}
                    <br />
                    {tx(
                      "copy.save_your_question_and_the_direction_you_2c4ae",
                    )}{" "}
                  </p>
                  <button
                    className="secondary"
                    onClick={() => setModal("session")}
                  >
                    <Plus size={16} />{" "}
                    {tx("copy.create_your_first_session_72857")}{" "}
                  </button>
                  <span className="hint">
                    {tx(
                      "copy.evidence_cards_and_a_complete_research_trail_e2849",
                    )}{" "}
                  </span>
                </div>
              )}
            </div>
          )}
          {view === "Ask" && (
            <Ask
              onPaper={selectPaper}
              onLibrary={(id) => {
                navigate("Library");
                selectPaper(id);
              }}
              onError={showError}
              sessionId={session?.id}
              sessions={snapshot.sessions}
              onSessionsChanged={refresh}
            />
          )}
          {view === "Settings" && (
            <div className="page">
              <div className="page-heading">
                <div>
                  <span className="eyebrow">
                    {tx("copy.your_workspace_your_way_0663a")}
                  </span>
                  <h1>{tx("copy.settings_c7f73")}</h1>
                </div>
              </div>
              <Settings
                key={settingsTab}
                snapshot={snapshot}
                initialTab={settingsTab}
                onAddLibrary={() => void addLibrary()}
                onRescan={(id) => void rescan(id)}
                onRemove={(id) => void removeLibrary(id)}
                onSave={(s) => saveSettings(s)}
                onError={showError}
                onReprocess={(id) => {
                  void engine("reprocess_scientific", { library_id: id })
                    .then(refresh)
                    .catch((e) => showError(errorMessage(e)));
                }}
              />
            </div>
          )}
          {view === "About" && (
            <div className="page">
              <About />
            </div>
          )}
        </main>
        <footer className="statusbar">
          <div>
            <span className={`dot ${connectionError ? "gold" : "teal"}`} />
            <strong>{tx("copy.petrus_local_engine_43eb8")}</strong>
            <span className="statusbar-divider" />
            {running ? (
              <span>
                {label(running.stage)} · {running.completed}/{running.total}{" "}
                {tx("copy.pdfs_8c85c")}{" "}
              </span>
            ) : (
              <span>
                {connectionError
                  ? tx("copy.disconnected_771e0")
                  : tx("copy.ready_20c7c")}
              </span>
            )}
          </div>
          <div>
            <ShieldCheck size={13} />
            <span>{tx("copy.on_this_device_a7f96")}</span>
            <span className="statusbar-divider" />
            <button
              className="theme-cycle"
              title={tx("appearance.current", {
                theme: label(snapshot.settings.theme),
              })}
              aria-label={tx("appearance.current", {
                theme: label(snapshot.settings.theme),
              })}
              onClick={() =>
                void saveSettings({
                  theme:
                    snapshot.settings.theme === "system"
                      ? "light"
                      : snapshot.settings.theme === "light"
                        ? "dark"
                        : "system",
                })
              }
            >
              {snapshot.settings.theme === "system" ? (
                <Monitor size={14} />
              ) : snapshot.settings.theme === "dark" ? (
                <Moon size={14} />
              ) : (
                <Sun size={14} />
              )}
            </button>
          </div>
        </footer>
      </div>
      {paperId !== null && (
        <PaperPanel
          key={paperId}
          revision={revision}
          id={paperId}
          onClose={closePaper}
          onPaper={selectPaper}
          collections={snapshot.collections}
          onChanged={changed}
          onError={showError}
        />
      )}
      {modal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !busy) setModal(null);
          }}
        >
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <button
              className="modal-close"
              aria-label={tx("copy.close_dialog_7b290")}
              disabled={busy}
              onClick={() => setModal(null)}
            >
              <X size={19} />
            </button>
            <span className="modal-icon">
              {modal === "session" ? <Orbit size={25} /> : <Layers size={25} />}
            </span>
            <h2 id="modal-title">
              {modal === "session"
                ? tx("copy.a_new_research_direction_9fd41")
                : tx("copy.bring_your_papers_together_276e7")}
            </h2>
            <p>
              {modal === "session"
                ? tx("copy.give_your_next_investigation_a_starting_point_e697a")
                : tx("copy.organize_a_topic_project_or_a_promising_f55f0")}
            </p>
            <form onSubmit={(e) => void submitModal(e)}>
              {modal === "session" ? (
                <>
                  <label>
                    {tx("copy.title_768e0")}{" "}
                    <input
                      name="title"
                      placeholder={tx(
                        "copy.e_g_viral_evolution_across_host_populations_85d5c",
                      )}
                      autoFocus
                      required
                      maxLength={300}
                    />
                  </label>
                  <label>
                    {tx("copy.research_question_6597d")}{" "}
                    <textarea
                      name="question"
                      placeholder={tx(
                        "copy.what_do_you_want_to_understand_cd33e",
                      )}
                      maxLength={5000}
                    />
                  </label>
                  <label>
                    {tx("copy.description_55f8e")}{" "}
                    <textarea
                      name="description"
                      placeholder={tx(
                        "copy.scope_context_or_a_few_initial_ideas_47f91",
                      )}
                      maxLength={10000}
                    />
                  </label>
                </>
              ) : (
                <label>
                  {tx("copy.collection_name_79142")}{" "}
                  <input
                    name="name"
                    placeholder={tx("copy.e_g_rsv_chikv_methods_e4785")}
                    autoFocus
                    required
                    maxLength={100}
                  />
                </label>
              )}
              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={() => setModal(null)}
                >
                  {tx("copy.cancel_77dfd")}{" "}
                </button>
                <button type="submit" className="primary" disabled={busy}>
                  {busy
                    ? tx("copy.saving_56a22")
                    : modal === "session"
                      ? tx("copy.create_session_d1df0")
                      : tx("copy.create_collection_be9ad")}
                  <ArrowRight size={15} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {toast && (
        <div className="toast" role="alert">
          <AlertCircle size={18} />
          <span>{localizeMessage(toast)}</span>
          <button
            aria-label={tx("copy.dismiss_notification_dc83c")}
            onClick={() => setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {!loaded && (
        <div className="splash">
          <PetrusLogo variant="hero" />
          <h1>{tx("copy.petrus_40fce")}</h1>
          <p>{tx("copy.follow_the_connections_find_the_evidence_a84d6")}</p>
          <LoaderCircle className="spin" size={20} />
        </div>
      )}
    </div>
  );
}
