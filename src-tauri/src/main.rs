#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{Arc, Mutex},
};
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder, PredefinedMenuItem, SubmenuBuilder},
    Emitter, Manager,
};

struct EngineProcess {
    child: Child,
    input: Option<ChildStdin>,
    output: BufReader<ChildStdout>,
    sequence: u64,
}

impl EngineProcess {
    fn start(data_dir: PathBuf) -> Result<Self, String> {
        let executable_dir = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .parent()
            .ok_or("Application directory is unavailable")?
            .to_path_buf();
        let sibling = executable_dir.join(if cfg!(windows) {
            "petrus-engine.exe"
        } else {
            "petrus-engine"
        });
        let mut command = if sibling.exists() && std::env::var_os("PETRUS_DEV_ENGINE").is_none() {
            Command::new(sibling)
        } else if cfg!(debug_assertions) {
            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .to_path_buf();
            let python = std::env::var_os("PETRUS_PYTHON")
                .map(PathBuf::from)
                .unwrap_or_else(|| {
                    root.join(if cfg!(windows) {
                        ".venv/Scripts/python.exe"
                    } else {
                        ".venv/bin/python"
                    })
                });
            let mut cmd = Command::new(python);
            cmd.arg("-m")
                .arg("petrus_engine")
                .current_dir(root.join("engine"));
            cmd
        } else {
            return Err("The PETRUS engine is missing from the application bundle.".into());
        };
        // Private pipes: PDF data never crosses a network socket.
        command
            .arg("--data-dir")
            .arg(data_dir)
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONUTF8", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        let mut child = command
            .spawn()
            .map_err(|e| format!("Could not start the local engine: {e}"))?;
        let input = child.stdin.take().ok_or("Engine input unavailable")?;
        let output = BufReader::new(child.stdout.take().ok_or("Engine output unavailable")?);
        Ok(Self {
            child,
            input: Some(input),
            output,
            sequence: 0,
        })
    }

    fn call(&mut self, method: &str, params: Value) -> Result<Value, String> {
        self.sequence += 1;
        let request = json!({ "id": self.sequence, "method": method, "params": params });
        let input = self.input.as_mut().ok_or("Local engine is shutting down")?;
        writeln!(input, "{request}")
            .and_then(|_| input.flush())
            .map_err(|_| "The local engine stopped. Restart PETRUS.".to_string())?;
        let mut line = String::new();
        if self
            .output
            .read_line(&mut line)
            .map_err(|e| e.to_string())?
            == 0
        {
            return Err("The local engine stopped. Restart PETRUS.".into());
        }
        let response: Value =
            serde_json::from_str(&line).map_err(|_| "Invalid local engine response")?;
        if response["id"].as_u64() != Some(self.sequence) {
            return Err("Local engine request mismatch".into());
        }
        if let Some(error) = response["error"].as_str() {
            return Err(error.into());
        }
        Ok(response["result"].clone())
    }

    fn shutdown(&mut self) {
        self.input.take(); // EOF lets the engine terminate its active parser before exiting.
        for _ in 0..20 {
            if matches!(self.child.try_wait(), Ok(Some(_))) {
                return;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Drop for EngineProcess {
    fn drop(&mut self) {
        self.shutdown();
    }
}
struct EngineState(Arc<Mutex<EngineProcess>>);

#[tauri::command]
async fn engine_call(
    method: String,
    params: Value,
    state: tauri::State<'_, EngineState>,
) -> Result<Value, String> {
    const METHODS: &[&str] = &[
        "snapshot",
        "papers",
        "paper",
        "add_library",
        "rescan",
        "remove_library",
        "save_settings",
        "new_session",
        "session",
        "research_claim_create",
        "research_claim_list",
        "research_claim_get",
        "research_claim_update",
        "research_claim_archive",
        "research_claim_restore",
        "research_claim_evidence_link",
        "research_claim_evidence_update",
        "research_claim_evidence_unlink",
        "research_trail_list",
        "research_trail_get",
        "research_evidence_save",
        "research_evidence_list",
        "research_evidence_get",
        "research_evidence_update",
        "research_evidence_remove",

        "create_collection",
        "set_collection",
        "save_notes",
        "content",
        "graph",
        "verify_integrity",
        "reprocess_scientific",
        "grobid_health",
        "semantic_search",
        "hybrid_search",
        "embedding_index",
        "embedding_status",
        "ask",
        "llm_status",
        "llm_models",
        "save_ask_event",
        "embedding_remove_stale",
    ];
    if !METHODS.contains(&method.as_str()) {
        return Err("Unknown operation".into());
    }
    let engine = state.0.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut result = engine
            .lock()
            .map_err(|_| "errors.engineUnavailable".to_string())?
            .call(&method, params)?;
        if method == "snapshot" {
            result["system_locale"] =
                json!(sys_locale::get_locale().unwrap_or_else(|| "en".into()));
        }
        Ok(result)
    })
    .await
    .map_err(|e| e.to_string())?
}

struct OSService;
impl OSService {
    fn open_file(path: &PathBuf, requested_page: Option<u32>) -> Result<Value, String> {
        open::that_detached(path)
            .map_err(|_| "Could not open this PDF in the default application.".to_string())?;
        Ok(json!({"page_requested": requested_page, "page_open_supported": false}))
    }
    fn reveal_file(path: &PathBuf) -> Result<(), String> {
        #[cfg(target_os = "macos")]
        let result = Command::new("open").arg("-R").arg("--").arg(path).spawn();
        #[cfg(target_os = "windows")]
        let result = Command::new("explorer")
            .arg(format!("/select,{}", path.display()))
            .spawn();
        #[cfg(target_os = "linux")]
        return open::that_detached(path.parent().ok_or("File has no parent directory")?)
            .map_err(|_| "Could not reveal this file.".into());
        #[cfg(not(target_os = "linux"))]
        result
            .map(|_| ())
            .map_err(|_| "Could not reveal this file.".into())
    }
}

#[tauri::command]
async fn paper_action(
    id: u64,
    action: String,
    page: Option<u32>,
    state: tauri::State<'_, EngineState>,
) -> Result<Value, String> {
    // The default OS app has no portable page-opening contract. Keep the requested page
    // typed for a future integrated viewer; never synthesize platform-specific keyboard input.
    if page == Some(0) {
        return Err("errors.invalidPage".into());
    }
    let engine = state.0.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value = engine
            .lock()
            .map_err(|_| "Local engine unavailable".to_string())?
            .call("file_path", json!({ "id": id }))?;
        let path = PathBuf::from(value.as_str().ok_or("No PDF location available")?);
        match action.as_str() {
            "open" => OSService::open_file(&path, page),
            "reveal" => OSService::reveal_file(&path).map(|_| json!({"revealed":true})),
            _ => Err("Unknown file action".into()),
        }
    })
    .await
    .map_err(|e| e.to_string())?
}

fn native_menu(app: &tauri::AppHandle, locale: &str) -> tauri::Result<()> {
    let json = if locale.to_lowercase().starts_with("pt") {
        include_str!("../../app/src/i18n/locales/pt-BR.json")
    } else {
        include_str!("../../app/src/i18n/locales/en.json")
    };
    let catalog: Value =
        serde_json::from_str(json).expect("Bundled translations must be valid JSON");
    let text = |key: &str| catalog.get(key).and_then(Value::as_str).unwrap_or("");
    let about = MenuItemBuilder::with_id("about", text("menus.about")).build(app)?;
    let settings = MenuItemBuilder::with_id("settings", text("menus.settings"))
        .accelerator("CmdOrCtrl+,")
        .build(app)?;
    let add = MenuItemBuilder::with_id("add-library", text("menus.add"))
        .accelerator("CmdOrCtrl+O")
        .build(app)?;
    let search = MenuItemBuilder::with_id("search", text("menus.search"))
        .accelerator("CmdOrCtrl+K")
        .build(app)?;
    macro_rules! predefined {
        ($method:ident,$key:literal) => {
            &PredefinedMenuItem::$method(app, Some(text($key)))?
        };
    }
    let app_menu = SubmenuBuilder::new(app, "PETRUS")
        .items(&[&about, &settings])
        .separator()
        .items(&[
            predefined!(hide, "menus.hide"),
            predefined!(hide_others, "menus.hideOthers"),
            predefined!(show_all, "menus.showAll"),
        ])
        .separator()
        .item(predefined!(quit, "menus.quit"))
        .build()?;
    let file_menu = SubmenuBuilder::new(app, text("menus.file"))
        .items(&[&add, &search])
        .separator()
        .item(predefined!(close_window, "menus.close"))
        .build()?;
    let edit_menu = SubmenuBuilder::new(app, text("menus.edit"))
        .items(&[
            predefined!(undo, "menus.undo"),
            predefined!(redo, "menus.redo"),
        ])
        .separator()
        .items(&[
            predefined!(cut, "menus.cut"),
            predefined!(copy, "menus.copy"),
            predefined!(paste, "menus.paste"),
            predefined!(select_all, "menus.selectAll"),
        ])
        .build()?;
    let window_menu = SubmenuBuilder::new(app, text("menus.window"))
        .items(&[
            predefined!(minimize, "menus.minimize"),
            predefined!(maximize, "menus.maximize"),
        ])
        .build()?;
    app.set_menu(
        MenuBuilder::new(app)
            .items(&[&app_menu, &file_menu, &edit_menu, &window_menu])
            .build()?,
    )?;
    Ok(())
}
#[tauri::command]
fn set_menu_language(app: tauri::AppHandle, locale: String) -> Result<(), String> {
    native_menu(&app, &locale).map_err(|_| "errors.generic".into())
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let data_dir = std::env::var_os("PETRUS_DATA_DIR")
                .map(PathBuf::from)
                .unwrap_or(app.path().app_data_dir()?);
            std::fs::create_dir_all(&data_dir)?;
            let process = EngineProcess::start(data_dir).map_err(std::io::Error::other)?;
            app.manage(EngineState(Arc::new(Mutex::new(process))));
            let state = app.state::<EngineState>();
            let initial = state
                .0
                .lock()
                .map_err(|_| std::io::Error::other("Engine unavailable"))?
                .call("snapshot", json!({}))
                .map_err(std::io::Error::other)?;
            let system = sys_locale::get_locale().unwrap_or_else(|| "en".into());
            let preferred = initial["settings"]["language"].as_str().unwrap_or("system");
            native_menu(
                app.handle(),
                if preferred == "system" {
                    &system
                } else {
                    preferred
                },
            )?;
            app.on_menu_event(|app, event| {
                let _ = app.emit("menu-action", event.id().as_ref());
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            engine_call,
            paper_action,
            set_menu_language
        ])
        .build(tauri::generate_context!())
        .expect("Could not launch PETRUS");
    app.run(|handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(state) = handle.try_state::<EngineState>() {
                if let Ok(mut process) = state.0.lock() {
                    process.shutdown();
                }
            }
        }
    });
}
