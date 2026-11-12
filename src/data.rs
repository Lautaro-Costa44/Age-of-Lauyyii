//! Modelos de datos y carga de los JSON.
//!
//! Los datos vienen embebidos en el ejecutable, pero si existe una carpeta
//! `data/` junto al .exe (o en el directorio actual) se usan esos archivos:
//! así podés editar civs y líneas de tiempo sin recompilar.
//! `data/civs.json` se genera con `tools/generar_civs.py` a partir de aoe2techtree.

use serde::de::DeserializeOwned;
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize, Clone)]
pub struct Civ {
    pub nombre: String,
    pub clave: String,
    pub enfoque: String,
    pub dificultad: String,
    #[serde(default)]
    pub unidades_unicas: Vec<String>,
    #[serde(default)]
    pub tecnologias_unicas: Vec<String>,
    #[serde(default)]
    pub bonos: Vec<String>,
    #[serde(default)]
    pub bono_equipo: String,
    #[serde(default)]
    pub castillos: String,
    #[serde(default)]
    pub imperial: String,
    #[serde(default)]
    pub lineas: Vec<Linea>,
    #[serde(default)]
    pub unidades_detalle: Vec<UnidadUnica>,
}

#[derive(Deserialize, Clone)]
pub struct Linea {
    pub id: String,
    pub nombre: String,
    pub tipo: String,
    pub descripcion: String,
    pub pasos: Vec<Paso>,
    /// Link a la fuente de la guía (ej. un video), si la hay
    #[serde(default)]
    pub fuente: Option<String>,
    /// Estrategia especialmente cómoda para esta civ
    #[serde(default)]
    pub recomendada: bool,
}

#[derive(Deserialize, Clone)]
pub struct Paso {
    /// Aldeanos totales al terminar el paso (0 = no aplica)
    pub aldeanos: u32,
    pub texto: String,
    #[serde(default)]
    pub comida: u32,
    #[serde(default)]
    pub madera: u32,
    #[serde(default)]
    pub oro: u32,
    #[serde(default)]
    pub piedra: u32,
    /// Tiempo de juego ideal (CU sin parar), opcional
    #[serde(default)]
    pub tiempo: Option<String>,
    #[serde(default = "fase_por_defecto")]
    pub fase: String,
    /// Avance o llegada de edad
    #[serde(default)]
    pub hito: bool,
    /// Qué investigar o entrenar en este paso y dónde
    #[serde(default)]
    pub mejoras: Vec<Mejora>,
}

#[derive(Deserialize, Clone)]
pub struct Mejora {
    pub que: String,
    pub donde: String,
}

#[derive(Deserialize, Clone)]
pub struct UnidadUnica {
    pub nombre: String,
    /// Clase según el techtree (ej. "caballería", "arquero a pie")
    #[serde(default)]
    pub clase: String,
    /// Tipo genérico con el que se la puede comparar
    pub como: String,
    pub debil: Vec<String>,
    pub fuerte: Vec<String>,
    /// true si el counter está ajustado a mano para esta unidad
    #[serde(default)]
    pub ajustado: bool,
}

fn fase_por_defecto() -> String {
    "Oscura".into()
}

impl Paso {
    pub fn recursos(&self) -> [u32; 4] {
        [self.comida, self.madera, self.oro, self.piedra]
    }
}

#[derive(Deserialize, Clone)]
pub struct Dato {
    pub titulo: String,
    pub valor: String,
    #[serde(default)]
    pub nota: String,
}

#[derive(Deserialize, Clone)]
pub struct Counter {
    pub unidad: String,
    pub la_vencen: Vec<String>,
    pub buena_contra: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct Categoria {
    pub titulo: String,
    pub items: Vec<String>,
}

#[derive(Deserialize, Clone)]
pub struct Guia {
    pub tiempos: Vec<Dato>,
    pub counters: Vec<Counter>,
    pub consejos: Vec<Categoria>,
    #[serde(default)]
    pub guias: Vec<GuiaEstrategia>,
}

/// Guía de una estrategia completa (ej. Fast Castle + Boom), con su línea de tiempo por civ.
#[derive(Deserialize, Clone)]
pub struct GuiaEstrategia {
    /// Coincide con el id de la línea de tiempo de cada civ
    pub id: String,
    pub titulo: String,
    pub autor: String,
    pub url: String,
    pub resumen: String,
    pub secciones: Vec<Categoria>,
}

pub struct Datos {
    pub civs: Vec<Civ>,
    pub guia: Guia,
    pub avisos: Vec<String>,
}

impl Datos {
    pub fn cargar() -> Self {
        let mut avisos = Vec::new();
        let civs = cargar("civs.json", include_str!("../data/civs.json"), &mut avisos);
        let guia = cargar("guia.json", include_str!("../data/guia.json"), &mut avisos);
        Self { civs, guia, avisos }
    }
}

pub fn carpeta_exe() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
}

fn carpetas_datos() -> Vec<PathBuf> {
    let mut v = Vec::new();
    if let Some(dir) = carpeta_exe() {
        v.push(dir.join("data"));
    }
    if let Ok(cwd) = std::env::current_dir() {
        v.push(cwd.join("data"));
    }
    v
}

fn cargar<T: DeserializeOwned>(archivo: &str, embebido: &str, avisos: &mut Vec<String>) -> T {
    for dir in carpetas_datos() {
        let ruta = dir.join(archivo);
        if let Ok(txt) = std::fs::read_to_string(&ruta) {
            match serde_json::from_str(&txt) {
                Ok(v) => return v,
                Err(e) => {
                    avisos.push(format!(
                        "Error en {}: {e}. Uso los datos internos.",
                        ruta.display()
                    ));
                    break;
                }
            }
        }
    }
    serde_json::from_str(embebido).expect("datos internos inválidos")
}
