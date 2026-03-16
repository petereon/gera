use pyo3::prelude::*;
mod oauth;

pub fn tauri_generate_context() -> tauri::Context {
    tauri::generate_context!()
}

#[cfg(target_os = "macos")]
fn set_window_bg_color(window: &tauri::WebviewWindow, r: f64, g: f64, b: f64) {
    use objc2::msg_send;
    use objc2::runtime::AnyObject;
    use objc2_app_kit::NSColor;

    if let Ok(ns_window) = window.ns_window() {
        let ns_window = ns_window as *mut AnyObject;
        unsafe {
            let bg_color = NSColor::colorWithRed_green_blue_alpha(r, g, b, 1.0);
            let _: () = msg_send![ns_window, setBackgroundColor: &*bg_color];
        }
    }
}

#[tauri::command]
fn set_theme(window: tauri::WebviewWindow, dark: bool) {
    #[cfg(target_os = "macos")]
    {
        if dark {
            set_window_bg_color(&window, 11.0 / 255.0, 15.0 / 255.0, 22.0 / 255.0);
        } else {
            set_window_bg_color(&window, 232.0 / 255.0, 237.0 / 255.0, 244.0 / 255.0);
        }
    }
}

/// Load the list of recent vaults from $GERA_APP_DATA_DIR/vaults.json.
fn load_recent_vaults(app_data_dir: &std::path::Path) -> Vec<String> {
    let path = app_data_dir.join("vaults.json");
    let Ok(content) = std::fs::read_to_string(&path) else {
        return vec![];
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&content) else {
        return vec![];
    };
    value["recent"]
        .as_array()
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .take(10)
                .collect()
        })
        .unwrap_or_default()
}

/// Build and register the application menu, including the vault File menu.
fn setup_menu(app: &tauri::App) -> tauri::Result<()> {
    use tauri::Manager;
    use tauri::menu::{Menu, MenuItem, Submenu};

    let app_data_dir = app.path().app_data_dir()?;
    let recent_vaults = load_recent_vaults(&app_data_dir);

    // Recent sub-menu items
    let mut recent_menu_items: Vec<MenuItem<tauri::Wry>> = Vec::new();
    for (i, path) in recent_vaults.iter().enumerate() {
        let label = std::path::Path::new(path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or(path.as_str())
            .to_string();
        let item = MenuItem::with_id(
            app,
            format!("vault:recent:{}", i),
            label,
            true,
            None::<&str>,
        )?;
        recent_menu_items.push(item);
    }

    let recent_refs: Vec<&dyn tauri::menu::IsMenuItem<tauri::Wry>> = recent_menu_items
        .iter()
        .map(|item| item as &dyn tauri::menu::IsMenuItem<tauri::Wry>)
        .collect();

    let recent_submenu = Submenu::with_id_and_items(
        app,
        "vault:recent-menu",
        "Recent",
        !recent_refs.is_empty(),
        &recent_refs,
    )?;

    let new_vault_item = MenuItem::with_id(
        app,
        "vault:new",
        "New Vault…",
        true,
        Some("CmdOrCtrl+Shift+N"),
    )?;
    let open_vault_item = MenuItem::with_id(
        app,
        "vault:open",
        "Open Vault…",
        true,
        Some("CmdOrCtrl+Shift+O"),
    )?;
    let separator = tauri::menu::PredefinedMenuItem::separator(app)?;

    let file_submenu = Submenu::with_id_and_items(
        app,
        "file",
        "File",
        true,
        &[
            &new_vault_item,
            &open_vault_item,
            &separator,
            &recent_submenu,
        ],
    )?;

    // Store recent vault paths in app state for lookup in menu event handler
    app.manage(RecentVaultPaths(recent_vaults));

    let menu = Menu::with_items(app, &[&file_submenu])?;
    app.set_menu(menu)?;

    Ok(())
}

/// App state carrying recent vault paths so the menu event handler can look them up.
struct RecentVaultPaths(Vec<String>);

#[pymodule(gil_used = false)]
#[pyo3(name = "ext_mod")]
pub mod ext_mod {
    use super::*;

    #[pymodule_init]
    fn init(module: &Bound<'_, PyModule>) -> PyResult<()> {
        pytauri::pymodule_export(
            module,
            |_args, _kwargs| Ok(tauri_generate_context()),
            |_args, _kwargs| {
                let builder = tauri::Builder::default()
                    .plugin(tauri_plugin_opener::init())
                    .plugin(tauri_plugin_dialog::init())
                    .setup(|app| {
                        use tauri::{Emitter, Manager};

                        let app_data_dir = app.path().app_data_dir()?;
                        std::env::set_var("GERA_APP_DATA_DIR", &app_data_dir);

                        #[cfg(target_os = "macos")]
                        if let Some(window) = app.get_webview_window("main") {
                            let dark = window.theme().map(|t| t == tauri::Theme::Dark).unwrap_or(false);
                            if dark {
                                set_window_bg_color(&window, 11.0 / 255.0, 15.0 / 255.0, 22.0 / 255.0);
                            } else {
                                set_window_bg_color(&window, 232.0 / 255.0, 237.0 / 255.0, 244.0 / 255.0);
                            }

                            // Size the window to fill the full screen height at 16:9.
                            if let Ok(Some(monitor)) = window.primary_monitor() {
                                use tauri::{LogicalPosition, LogicalSize};
                                let scale = monitor.scale_factor();
                                let phys = monitor.size();
                                let screen_w = phys.width as f64 / scale;
                                let screen_h = phys.height as f64 / scale;
                                let desired_w = screen_h * 16.0 / 9.0;
                                let (win_w, win_h) = if desired_w <= screen_w {
                                    (desired_w, screen_h)
                                } else {
                                    (screen_w, screen_w * 9.0 / 16.0)
                                };
                                let _ = window.set_size(LogicalSize::new(win_w, win_h));
                                let _ = window.set_position(LogicalPosition::new(
                                    (screen_w - win_w) / 2.0,
                                    0.0,
                                ));
                            }
                        }

                        setup_menu(app)?;

                        app.on_menu_event(|app, event| {
                            let id = event.id().as_ref();
                            match id {
                                "vault:new" => {
                                    let _ = app.emit("vault:new", ());
                                }
                                "vault:open" => {
                                    let _ = app.emit("vault:open", ());
                                }
                                id if id.starts_with("vault:recent:") => {
                                    if let Ok(idx) = id["vault:recent:".len()..].parse::<usize>() {
                                        if let Some(paths) = app.try_state::<RecentVaultPaths>() {
                                            if let Some(path) = paths.0.get(idx) {
                                                let _ = app.emit("vault:open-path", path.clone());
                                            }
                                        }
                                    }
                                }
                                _ => {}
                            }
                        });

                        Ok(())
                    })
                    .invoke_handler(tauri::generate_handler![
                        set_theme,
                        oauth::authenticate_google_cmd,
                        oauth::list_google_accounts_cmd,
                        oauth::remove_google_account_cmd,
                    ]);
                Ok(builder)
            },
        )
    }
}
