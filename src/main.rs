#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod atajos;
mod carrusel;
mod config;
mod data;
mod tema;

use atajos::{Accion, Atajos};
use config::Config;
use data::{Civ, Datos};
use eframe::egui::{self, RichText};
use std::time::{Duration, Instant};

const TAMANO_NORMAL: [f32; 2] = [1060.0, 720.0];
const TAMANO_COMPACTO: [f32; 2] = [700.0, 320.0];

fn main() -> eframe::Result {
    let opciones = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Age of Lauyyii")
            .with_inner_size(TAMANO_NORMAL)
            .with_min_inner_size([420.0, 200.0]),
        vsync: true,
        ..Default::default()
    };
    eframe::run_native(
        "Age of Lauyyii",
        opciones,
        Box::new(|cc| Ok(Box::new(App::new(cc)))),
    )
}

#[derive(PartialEq, Clone, Copy)]
enum Tab {
    Partida,
    Civs,
    Tiempos,
    Counters,
    Consejos,
}

#[derive(Default)]
struct Cronometro {
    inicio: Option<Instant>,
    acumulado: Duration,
}

impl Cronometro {
    fn transcurrido(&self) -> Duration {
        self.acumulado + self.inicio.map(|i| i.elapsed()).unwrap_or_default()
    }
    fn alternar(&mut self) {
        match self.inicio.take() {
            Some(i) => self.acumulado += i.elapsed(),
            None => self.inicio = Some(Instant::now()),
        }
    }
    fn reiniciar(&mut self) {
        *self = Self::default();
    }
    fn corriendo(&self) -> bool {
        self.inicio.is_some()
    }
}

struct App {
    datos: Datos,
    cfg: Config,
    cfg_guardada: Config,
    atajos: Atajos,
    tab: Tab,
    civ_sel: usize,
    filtro: String,
    paso: usize,
    compacto: bool,
    crono: Cronometro,
}

impl App {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        tema::aplicar(&cc.egui_ctx);
        let datos = Datos::cargar();
        let cfg = Config::cargar();
        let civ_sel = datos
            .civs
            .iter()
            .position(|c| c.clave == cfg.civ)
            .unwrap_or(0);
        if cfg.siempre_arriba {
            cc.egui_ctx
                .send_viewport_cmd(egui::ViewportCommand::WindowLevel(egui::WindowLevel::AlwaysOnTop));
        }
        let mut app = Self {
            datos,
            cfg_guardada: cfg.clone(),
            cfg,
            atajos: Atajos::new(cc.egui_ctx.clone()),
            tab: Tab::Partida,
            civ_sel,
            filtro: String::new(),
            paso: 0,
            compacto: false,
            crono: Cronometro::default(),
        };
        app.registrar_atajos();
        app
    }

    fn registrar_atajos(&mut self) {
        let c = &self.cfg;
        self.atajos.registrar([
            (c.tecla_siguiente.as_str(), Accion::Siguiente),
            (c.tecla_anterior.as_str(), Accion::Anterior),
            (c.tecla_crono.as_str(), Accion::Crono),
        ]);
    }

    fn civ(&self) -> Option<&Civ> {
        self.datos.civs.get(self.civ_sel)
    }

    fn total_pasos(&self) -> usize {
        self.civ()
            .and_then(|c| c.lineas.get(self.cfg.linea))
            .map_or(0, |l| l.pasos.len())
    }

    fn mover_paso(&mut self, delta: i32) {
        let total = self.total_pasos();
        if total > 0 {
            self.paso = (self.paso as i32 + delta).clamp(0, total as i32 - 1) as usize;
        }
    }

    fn elegir_civ(&mut self, i: usize) {
        if self.civ_sel != i {
            self.civ_sel = i;
            self.paso = 0;
            if let Some(c) = self.datos.civs.get(i) {
                self.cfg.civ = c.clave.clone();
                if self.cfg.linea >= c.lineas.len() {
                    self.cfg.linea = 0;
                }
            }
        }
    }

    fn segundos_juego(&self) -> u32 {
        (self.crono.transcurrido().as_secs_f32() * self.cfg.velocidad) as u32
    }

    fn procesar_teclas(&mut self, ctx: &egui::Context) {
        for a in self.atajos.pendientes() {
            match a {
                Accion::Siguiente => self.mover_paso(1),
                Accion::Anterior => self.mover_paso(-1),
                Accion::Crono => self.crono.alternar(),
            }
        }
        if ctx.wants_keyboard_input() || !(self.tab == Tab::Partida || self.compacto) {
            return;
        }
        let (sig, ant) = ctx.input(|i| {
            (
                i.key_pressed(egui::Key::ArrowRight) || i.key_pressed(egui::Key::Space),
                i.key_pressed(egui::Key::ArrowLeft),
            )
        });
        if sig {
            self.mover_paso(1);
        }
        if ant {
            self.mover_paso(-1);
        }
    }

    // ------------------------------------------------------------------ barra

    fn barra_superior(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::top("barra")
            .frame(egui::Frame::new().fill(tema::FONDO).inner_margin(egui::Margin::symmetric(14, 8)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("AGE OF LAUYYII").color(tema::DORADO).strong().size(17.0));
                    ui.add_space(12.0);
                    if !self.compacto {
                        for (t, nombre) in [
                            (Tab::Partida, "Línea de tiempo"),
                            (Tab::Civs, "Civilizaciones"),
                            (Tab::Tiempos, "Timings"),
                            (Tab::Counters, "Counters"),
                            (Tab::Consejos, "Consejos"),
                        ] {
                            let activo = self.tab == t;
                            let txt = RichText::new(nombre).color(if activo { tema::DORADO } else { tema::TEXTO_SUAVE });
                            if ui.add(egui::Button::new(txt).selected(activo).frame(activo)).clicked() {
                                self.tab = t;
                            }
                        }
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let txt = if self.compacto { "Expandir" } else { "Compacto" };
                        if ui.button(txt).clicked() {
                            self.compacto = !self.compacto;
                            let tam = if self.compacto { TAMANO_COMPACTO } else { TAMANO_NORMAL };
                            ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(tam.into()));
                        }
                        if ui.checkbox(&mut self.cfg.siempre_arriba, "Siempre arriba").changed() {
                            let nivel = if self.cfg.siempre_arriba {
                                egui::WindowLevel::AlwaysOnTop
                            } else {
                                egui::WindowLevel::Normal
                            };
                            ctx.send_viewport_cmd(egui::ViewportCommand::WindowLevel(nivel));
                        }
                        if !self.compacto {
                            self.menu_teclas(ui);
                        }
                    });
                });
            });
    }

    fn menu_teclas(&mut self, ui: &mut egui::Ui) {
        let mut cambio = false;
        ui.menu_button("Teclas", |ui| {
            ui.label(RichText::new("Atajos globales (funcionan dentro del juego)").small().color(tema::TEXTO_SUAVE));
            egui::Grid::new("teclas").num_columns(2).show(ui, |ui| {
                for (nombre, valor) in [
                    ("Siguiente tarjeta", &mut self.cfg.tecla_siguiente),
                    ("Tarjeta anterior", &mut self.cfg.tecla_anterior),
                    ("Iniciar/pausar reloj", &mut self.cfg.tecla_crono),
                ] {
                    ui.label(nombre);
                    egui::ComboBox::from_id_salt(nombre)
                        .selected_text(valor.as_str())
                        .show_ui(ui, |ui| {
                            for t in atajos::TECLAS {
                                if ui.selectable_label(valor == t, t).clicked() {
                                    *valor = t.to_string();
                                    cambio = true;
                                }
                            }
                        });
                    ui.end_row();
                }
            });
            ui.label(
                RichText::new("Elegí teclas que no uses en AoE2: mientras la guía\nestá abierta, el juego no las recibe.")
                    .small()
                    .color(tema::TEXTO_SUAVE),
            );
        });
        if cambio {
            self.registrar_atajos();
        }
    }

    // ------------------------------------------------------------- lista civs

    fn lista_civs(&mut self, ui: &mut egui::Ui) {
        egui::SidePanel::left("lista_civs")
            .resizable(false)
            .exact_width(210.0)
            .frame(egui::Frame::new().fill(tema::FONDO).inner_margin(egui::Margin::same(10)))
            .show_inside(ui, |ui| {
                ui.add(
                    egui::TextEdit::singleline(&mut self.filtro)
                        .hint_text("Buscar civ, unidad, bono…")
                        .desired_width(f32::INFINITY),
                );
                ui.label(
                    RichText::new(format!("{} civilizaciones", self.datos.civs.len()))
                        .small()
                        .color(tema::TEXTO_SUAVE),
                );
                ui.add_space(4.0);
                let filtro = self.filtro.to_lowercase();
                let mut elegida = None;
                egui::ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
                    for (i, c) in self.datos.civs.iter().enumerate() {
                        if !filtro.is_empty() && !coincide(c, &filtro) {
                            continue;
                        }
                        let activa = i == self.civ_sel;
                        let resp = egui::Frame::new()
                            .fill(if activa { tema::TARJETA_ACTIVA } else { egui::Color32::TRANSPARENT })
                            .stroke(egui::Stroke::new(1.0_f32, if activa { tema::DORADO } else { egui::Color32::TRANSPARENT }))
                            .corner_radius(egui::CornerRadius::same(6))
                            .inner_margin(egui::Margin::symmetric(8, 4))
                            .show(ui, |ui| {
                                ui.set_width(ui.available_width());
                                ui.label(RichText::new(&c.nombre).strong().color(if activa { tema::DORADO } else { tema::TEXTO }));
                                ui.label(RichText::new(&c.enfoque).small().color(tema::TEXTO_SUAVE));
                            })
                            .response
                            .interact(egui::Sense::click());
                        if resp.clicked() {
                            elegida = Some(i);
                        }
                        if resp.hovered() {
                            ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
                        }
                    }
                });
                if let Some(i) = elegida {
                    self.elegir_civ(i);
                }
            });
    }

    // -------------------------------------------------------------- partida

    fn controles_crono(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            tema::marco(tema::BORDE)
                .inner_margin(egui::Margin::symmetric(12, 4))
                .show(ui, |ui| {
                    ui.label(
                        RichText::new(mmss(self.segundos_juego()))
                            .monospace()
                            .size(if self.compacto { 18.0 } else { 22.0 })
                            .color(if self.crono.corriendo() { tema::DORADO } else { tema::TEXTO }),
                    );
                });
            let txt = if self.crono.corriendo() { "Pausar" } else { "Iniciar" };
            if ui.button(format!("{txt} ({})", self.cfg.tecla_crono)).clicked() {
                self.crono.alternar();
            }
            if ui.button("Reiniciar").clicked() {
                self.crono.reiniciar();
                self.paso = 0;
            }
            if !self.compacto {
                ui.add(
                    egui::DragValue::new(&mut self.cfg.velocidad)
                        .range(1.0..=2.0)
                        .speed(0.05)
                        .prefix("velocidad x"),
                )
                .on_hover_text("1.7 = velocidad normal de AoE2 DE: así el reloj coincide con el del juego");
            }
        });
    }

    fn selector_linea(&mut self, ui: &mut egui::Ui) {
        let Some(civ) = self.datos.civs.get(self.civ_sel) else { return };
        let mut nueva = None;
        ui.horizontal_wrapped(|ui| {
            for (i, l) in civ.lineas.iter().enumerate() {
                let activa = i == self.cfg.linea;
                let txt = RichText::new(&l.nombre).color(if activa { tema::FONDO } else { tema::TEXTO });
                let mut b = egui::Button::new(txt).corner_radius(egui::CornerRadius::same(14));
                if activa {
                    b = b.fill(tema::DORADO);
                }
                if ui.add(b).on_hover_text(format!("{} — {}", l.tipo, l.descripcion)).clicked() {
                    nueva = Some(i);
                }
            }
        });
        if let Some(i) = nueva {
            if i != self.cfg.linea {
                self.cfg.linea = i;
                self.paso = 0;
            }
        }
    }

    fn navegacion(&mut self, ui: &mut egui::Ui) {
        let total = self.total_pasos();
        ui.horizontal(|ui| {
            if ui
                .add_enabled(self.paso > 0, egui::Button::new(format!("◀  Anterior ({})", self.cfg.tecla_anterior)))
                .clicked()
            {
                self.mover_paso(-1);
            }
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui
                    .add_enabled(
                        self.paso + 1 < total,
                        egui::Button::new(
                            RichText::new(format!("Siguiente ({})  ▶", self.cfg.tecla_siguiente)).strong(),
                        )
                        .fill(tema::DORADO.gamma_multiply(0.35)),
                    )
                    .clicked()
                {
                    self.mover_paso(1);
                }
            });
        });
    }

    fn vista_partida(&mut self, ui: &mut egui::Ui) {
        self.lista_civs(ui);
        let Some(civ) = self.datos.civs.get(self.civ_sel).cloned() else {
            ui.label("No hay civilizaciones cargadas.");
            return;
        };
        egui::ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                ui.heading(RichText::new(&civ.nombre).color(tema::DORADO).strong());
                tema::pastilla(ui, &civ.enfoque, tema::TEXTO_SUAVE);
                tema::pastilla(ui, &civ.dificultad, color_dificultad(&civ.dificultad));
            });
            ui.add_space(2.0);
            self.selector_linea(ui);
            if let Some(l) = civ.lineas.get(self.cfg.linea) {
                ui.label(RichText::new(&l.descripcion).color(tema::TEXTO_SUAVE));
            }
            ui.add_space(6.0);
            self.controles_crono(ui);
            ui.add_space(8.0);

            if let Some(l) = civ.lineas.get(self.cfg.linea) {
                carrusel::dibujar(ui, l, &mut self.paso, false);
                ui.add_space(6.0);
                carrusel::puntos(ui, l, &mut self.paso);
                ui.add_space(6.0);
                self.navegacion(ui);
            }
            ui.add_space(12.0);
            ui.columns(2, |cols| {
                tarjeta_texto(&mut cols[0], "Plan en Castillos", tema::color_fase("Castillos"), &civ.castillos);
                tarjeta_texto(&mut cols[1], "Plan en Imperial", tema::color_fase("Imperial"), &civ.imperial);
            });
            ui.add_space(6.0);
            ui.label(
                RichText::new(
                    "Tiempos = ideal con el CU produciendo sin parar (25 s por aldeano, Telar incluido). \
                     Si vas más lento, mirá CU ocioso y bloqueos de casas.",
                )
                .small()
                .color(tema::TEXTO_SUAVE),
            );
        });
    }

    fn vista_compacta(&mut self, ui: &mut egui::Ui) {
        let Some(civ) = self.datos.civs.get(self.civ_sel).cloned() else { return };
        ui.horizontal(|ui| {
            ui.label(RichText::new(&civ.nombre).color(tema::DORADO).strong());
            if let Some(l) = civ.lineas.get(self.cfg.linea) {
                ui.label(RichText::new(&l.nombre).small().color(tema::TEXTO_SUAVE));
            }
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.label(
                    RichText::new(format!(
                        "{} ◀  {} ▶  {} reloj",
                        self.cfg.tecla_anterior, self.cfg.tecla_siguiente, self.cfg.tecla_crono
                    ))
                    .small()
                    .color(tema::TEXTO_SUAVE),
                );
                ui.label(
                    RichText::new(mmss(self.segundos_juego()))
                        .monospace()
                        .size(16.0)
                        .color(if self.crono.corriendo() { tema::DORADO } else { tema::TEXTO }),
                );
            });
        });
        if let Some(l) = civ.lineas.get(self.cfg.linea) {
            carrusel::dibujar(ui, l, &mut self.paso, true);
            carrusel::puntos(ui, l, &mut self.paso);
        }
    }

    // ------------------------------------------------------------------ civs

    fn vista_civs(&mut self, ui: &mut egui::Ui) {
        self.lista_civs(ui);
        let Some(civ) = self.datos.civs.get(self.civ_sel).cloned() else { return };
        let mut ver_linea = None;
        egui::ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                ui.heading(RichText::new(&civ.nombre).color(tema::DORADO).strong());
                tema::pastilla(ui, &civ.enfoque, tema::TEXTO_SUAVE);
                tema::pastilla(ui, &civ.dificultad, color_dificultad(&civ.dificultad));
            });
            ui.add_space(8.0);
            ui.columns(2, |cols| {
                tarjeta_lista(&mut cols[0], "Bonos de la civilización", tema::DORADO, &civ.bonos);
                tarjeta_lista(&mut cols[1], "Unidades únicas", tema::color_fase("Castillos"), &civ.unidades_unicas);
                cols[1].add_space(8.0);
                tarjeta_texto(&mut cols[1], "Bono de equipo", tema::VERDE, &civ.bono_equipo);
            });
            ui.add_space(8.0);
            tarjeta_lista(ui, "Tecnologías únicas", tema::color_fase("Imperial"), &civ.tecnologias_unicas);
            ui.add_space(8.0);
            tema::marco(tema::BORDE).show(ui, |ui| {
                ui.set_width(ui.available_width());
                ui.label(RichText::new("Líneas de tiempo").strong().color(tema::DORADO));
                ui.horizontal_wrapped(|ui| {
                    for (i, l) in civ.lineas.iter().enumerate() {
                        if ui.button(format!("{}  ·  {}", l.nombre, l.tipo)).clicked() {
                            ver_linea = Some(i);
                        }
                    }
                });
            });
            ui.add_space(6.0);
            ui.hyperlink_to(
                RichText::new("Fuente de bonos y unidades: aoe2techtree.net").small(),
                "https://aoe2techtree.net",
            );
        });
        if let Some(i) = ver_linea {
            self.cfg.linea = i;
            self.paso = 0;
            self.tab = Tab::Partida;
        }
    }

    // --------------------------------------------------------------- guía

    fn vista_tiempos(&self, ui: &mut egui::Ui) {
        egui::ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            for d in &self.datos.guia.tiempos {
                tema::marco(tema::BORDE).show(ui, |ui| {
                    ui.set_width(ui.available_width());
                    ui.horizontal(|ui| {
                        ui.label(RichText::new(&d.titulo).strong());
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            ui.label(RichText::new(&d.valor).color(tema::DORADO).monospace());
                        });
                    });
                    if !d.nota.is_empty() {
                        ui.label(RichText::new(&d.nota).color(tema::TEXTO_SUAVE));
                    }
                });
                ui.add_space(4.0);
            }
        });
    }

    fn vista_counters(&self, ui: &mut egui::Ui) {
        egui::ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            for c in &self.datos.guia.counters {
                tema::marco(tema::BORDE).show(ui, |ui| {
                    ui.set_width(ui.available_width());
                    ui.label(RichText::new(&c.unidad).strong().size(16.0));
                    ui.horizontal_wrapped(|ui| {
                        ui.label(RichText::new("La vencen:").color(tema::ROJO).strong());
                        ui.label(c.la_vencen.join(", "));
                    });
                    ui.horizontal_wrapped(|ui| {
                        ui.label(RichText::new("Buena contra:").color(tema::VERDE).strong());
                        ui.label(c.buena_contra.join(", "));
                    });
                });
                ui.add_space(4.0);
            }
        });
    }

    fn vista_consejos(&self, ui: &mut egui::Ui) {
        egui::ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            for cat in &self.datos.guia.consejos {
                tarjeta_lista(ui, &cat.titulo, tema::DORADO, &cat.items);
                ui.add_space(6.0);
            }
        });
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.procesar_teclas(ctx);
        self.barra_superior(ctx);

        let mut avisos = self.datos.avisos.clone();
        if let Some(e) = &self.atajos.error {
            avisos.push(e.clone());
        }
        if !avisos.is_empty() && !self.compacto {
            egui::TopBottomPanel::bottom("avisos").show(ctx, |ui| {
                for a in &avisos {
                    ui.colored_label(tema::ROJO, a);
                }
            });
        }

        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(tema::PANEL).inner_margin(egui::Margin::same(if self.compacto { 8 } else { 12 })))
            .show(ctx, |ui| {
                if self.compacto {
                    self.vista_compacta(ui);
                    return;
                }
                match self.tab {
                    Tab::Partida => self.vista_partida(ui),
                    Tab::Civs => self.vista_civs(ui),
                    Tab::Tiempos => self.vista_tiempos(ui),
                    Tab::Counters => self.vista_counters(ui),
                    Tab::Consejos => self.vista_consejos(ui),
                }
            });

        // Solo con el reloj andando pedimos repintado periódico (bajo consumo).
        if self.crono.corriendo() {
            ctx.request_repaint_after(Duration::from_millis(500));
        }
        if self.cfg != self.cfg_guardada {
            self.cfg.guardar();
            self.cfg_guardada = self.cfg.clone();
        }
    }
}

fn coincide(c: &Civ, filtro: &str) -> bool {
    c.nombre.to_lowercase().contains(filtro)
        || c.enfoque.to_lowercase().contains(filtro)
        || c.unidades_unicas.iter().any(|u| u.to_lowercase().contains(filtro))
        || c.bonos.iter().any(|b| b.to_lowercase().contains(filtro))
}

fn color_dificultad(d: &str) -> egui::Color32 {
    match d {
        "Fácil" => tema::VERDE,
        "Difícil" => tema::ROJO,
        _ => tema::ORO,
    }
}

fn tarjeta_texto(ui: &mut egui::Ui, titulo: &str, color: egui::Color32, texto: &str) {
    tema::marco(color.gamma_multiply(0.6)).show(ui, |ui| {
        ui.set_width(ui.available_width());
        ui.label(RichText::new(titulo).strong().color(color));
        ui.add(egui::Label::new(texto).wrap());
    });
}

fn tarjeta_lista(ui: &mut egui::Ui, titulo: &str, color: egui::Color32, items: &[String]) {
    tema::marco(color.gamma_multiply(0.6)).show(ui, |ui| {
        ui.set_width(ui.available_width());
        ui.label(RichText::new(titulo).strong().color(color));
        for i in items {
            ui.horizontal_top(|ui| {
                ui.label(RichText::new("•").color(color));
                ui.add(egui::Label::new(i).wrap());
            });
        }
    });
}

fn mmss(segundos: u32) -> String {
    format!("{}:{:02}", segundos / 60, segundos % 60)
}
