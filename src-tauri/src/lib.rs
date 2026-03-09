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
            // i.e., `context_factory` function of python binding
            |_args, _kwargs| Ok(tauri_generate_context()),
            // i.e., `builder_factory` function of python binding
            |_args, _kwargs| {
                let builder = tauri::Builder::default()
                    .plugin(tauri_plugin_opener::init())
                    .setup(|app| {
                        use tauri::Manager;
                        let app_data_dir = app.path().app_data_dir()?;
                        std::env::set_var("GERA_APP_DATA_DIR", &app_data_dir);
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
