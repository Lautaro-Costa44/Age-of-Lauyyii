//! Atajos globales: funcionan aunque el foco esté en el juego.
//!
//! Windows entrega la tecla registrada a esta app (el juego no la recibe),
//! por eso conviene elegir teclas que no uses en AoE2.

use eframe::egui;
use global_hotkey::hotkey::{Code, HotKey};
use global_hotkey::{GlobalHotKeyEvent, GlobalHotKeyManager, HotKeyState};
use std::sync::mpsc::{channel, Receiver};

pub const TECLAS: [&str; 15] = [
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "Pausa", "BloqDespl",
    "Insert",
];

fn codigo(nombre: &str) -> Option<Code> {
    Some(match nombre {
        "F1" => Code::F1,
        "F2" => Code::F2,
        "F3" => Code::F3,
        "F4" => Code::F4,
        "F5" => Code::F5,
        "F6" => Code::F6,
        "F7" => Code::F7,
        "F8" => Code::F8,
        "F9" => Code::F9,
        "F10" => Code::F10,
        "F11" => Code::F11,
        "F12" => Code::F12,
        "Pausa" => Code::Pause,
        "BloqDespl" => Code::ScrollLock,
        "Insert" => Code::Insert,
        _ => return None,
    })
}

#[derive(Clone, Copy, PartialEq)]
pub enum Accion {
    Siguiente,
    Anterior,
    Crono,
}

pub struct Atajos {
    manager: Option<GlobalHotKeyManager>,
    registradas: Vec<(HotKey, Accion)>,
    rx: Receiver<u32>,
    pub error: Option<String>,
}

impl Atajos {
    pub fn new(ctx: egui::Context) -> Self {
        let (tx, rx) = channel();
        // Despertamos a egui al recibir la tecla: la app solo redibuja ante eventos.
        GlobalHotKeyEvent::set_event_handler(Some(move |e: GlobalHotKeyEvent| {
            if e.state == HotKeyState::Pressed {
                let _ = tx.send(e.id);
                ctx.request_repaint();
            }
        }));
        let (manager, error) = match GlobalHotKeyManager::new() {
            Ok(m) => (Some(m), None),
            Err(e) => (None, Some(format!("No pude activar los atajos globales: {e}"))),
        };
        Self { manager, registradas: Vec::new(), rx, error }
    }

    pub fn registrar(&mut self, teclas: [(&str, Accion); 3]) {
        let Some(m) = &self.manager else { return };
        for (hk, _) in self.registradas.drain(..) {
            let _ = m.unregister(hk);
        }
        let mut errores = Vec::new();
        for (nombre, accion) in teclas {
            let Some(c) = codigo(nombre) else { continue };
            let hk = HotKey::new(None, c);
            match m.register(hk) {
                Ok(()) => self.registradas.push((hk, accion)),
                Err(_) => errores.push(nombre.to_string()),
            }
        }
        self.error = (!errores.is_empty()).then(|| {
            format!(
                "No pude registrar {} (¿la usa otro programa?). Elegí otra en Teclas.",
                errores.join(", ")
            )
        });
    }

    pub fn pendientes(&self) -> Vec<Accion> {
        self.rx
            .try_iter()
            .filter_map(|id| {
                self.registradas
                    .iter()
                    .find(|(hk, _)| hk.id() == id)
                    .map(|(_, a)| *a)
            })
            .collect()
    }
}
