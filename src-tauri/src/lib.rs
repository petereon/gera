use pyo3::prelude::*;
mod oauth;

pub fn tauri_generate_context() -> tauri::Context {
    tauri::generate_context!()
}

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
                    .setup(|app| {
                        use tauri::Manager;

                        let app_data_dir = app.path().app_data_dir()?;
                        std::env::set_var("GERA_APP_DATA_DIR", &app_data_dir);

                        #[cfg(target_os = "macos")]
                        {
                            use objc2::msg_send;
                            use objc2::runtime::AnyObject;
                            use objc2_app_kit::NSColor;

                            if let Some(window) = app.get_webview_window("main") {
                                let ns_window = window.ns_window()? as *mut AnyObject;
                                unsafe {
                                    let bg_color = NSColor::colorWithRed_green_blue_alpha(
                                        232.0 / 255.0,
                                        237.0 / 255.0,
                                        244.0 / 255.0,
                                        1.0,
                                    );
                                    let _: () =
                                        msg_send![ns_window, setBackgroundColor: &*bg_color];
                                }
                            }
                        }

                        Ok(())
                    })
                    .invoke_handler(tauri::generate_handler![
                        oauth::authenticate_google_cmd,
                        oauth::list_google_accounts_cmd,
                        oauth::remove_google_account_cmd,
                    ]);
                Ok(builder)
            },
        )
    }
}
