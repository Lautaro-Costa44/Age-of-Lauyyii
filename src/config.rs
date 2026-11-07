//! Preferencias guardadas en `config.json` junto al ejecutable.

use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, PartialEq)]
#[serde(default)]
pub struct Config {
    pub civ: String,
    pub linea: usize,
    pub tecla_siguiente: String,
    pub tecla_anterior: String,
    pub tecla_crono: String,
    pub siempre_arriba: bool,
    pub velocidad: f32,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            civ: "Britons".into(),
            linea: 0,
            tecla_siguiente: "F8".into(),
            tecla_anterior: "F7".into(),
            tecla_crono: "F6".into(),
            siempre_arriba: false,
            velocidad: 1.7,
        }
    }
}

fn ruta() -> Option<std::path::PathBuf> {
    crate::data::carpeta_exe().map(|d| d.join("config.json"))
}

impl Config {
    pub fn cargar() -> Self {
        ruta()
            .and_then(|r| std::fs::read_to_string(r).ok())
            .and_then(|t| serde_json::from_str(&t).ok())
            .unwrap_or_default()
    }

    pub fn guardar(&self) {
        if let (Some(r), Ok(txt)) = (ruta(), serde_json::to_string_pretty(self)) {
            let _ = std::fs::write(r, txt);
        }
    }
}
