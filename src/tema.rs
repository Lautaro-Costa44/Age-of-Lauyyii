//! Paleta y estilo visual (tonos pergamino/oro sobre fondo oscuro).

use eframe::egui::{self, Color32, CornerRadius, Stroke};

pub const FONDO: Color32 = Color32::from_rgb(17, 15, 12);
pub const PANEL: Color32 = Color32::from_rgb(26, 23, 19);
pub const TARJETA: Color32 = Color32::from_rgb(36, 32, 26);
pub const TARJETA_ACTIVA: Color32 = Color32::from_rgb(47, 41, 32);
pub const BORDE: Color32 = Color32::from_rgb(72, 62, 47);
pub const DORADO: Color32 = Color32::from_rgb(226, 180, 78);
pub const TEXTO: Color32 = Color32::from_rgb(234, 226, 207);
pub const TEXTO_SUAVE: Color32 = Color32::from_rgb(158, 148, 128);

pub const COMIDA: Color32 = Color32::from_rgb(214, 96, 80);
pub const MADERA: Color32 = Color32::from_rgb(170, 122, 72);
pub const ORO: Color32 = Color32::from_rgb(236, 200, 74);
pub const PIEDRA: Color32 = Color32::from_rgb(150, 160, 170);
pub const RECURSOS: [(Color32, &str); 4] = [
    (COMIDA, "Comida"),
    (MADERA, "Madera"),
    (ORO, "Oro"),
    (PIEDRA, "Piedra"),
];

pub const VERDE: Color32 = Color32::from_rgb(130, 196, 120);
pub const ROJO: Color32 = Color32::from_rgb(226, 112, 100);

pub fn color_fase(fase: &str) -> Color32 {
    match fase {
        "Feudal" => Color32::from_rgb(120, 178, 92),
        "Castillos" => Color32::from_rgb(92, 156, 222),
        "Imperial" => Color32::from_rgb(196, 128, 220),
        _ => Color32::from_rgb(150, 146, 170),
    }
}

pub fn nombre_fase(fase: &str) -> &'static str {
    match fase {
        "Feudal" => "FEUDAL",
        "Castillos" => "CASTILLOS",
        "Imperial" => "IMPERIAL",
        _ => "OSCURA",
    }
}

pub fn aplicar(ctx: &egui::Context) {
    let mut v = egui::Visuals::dark();
    v.panel_fill = PANEL;
    v.window_fill = PANEL;
    v.extreme_bg_color = FONDO;
    v.faint_bg_color = TARJETA;
    v.override_text_color = Some(TEXTO);
    v.hyperlink_color = DORADO;
    v.selection.bg_fill = DORADO.gamma_multiply(0.30);
    v.selection.stroke = Stroke::new(1.0_f32, DORADO);
    v.window_stroke = Stroke::new(1.0_f32, BORDE);

    let r = CornerRadius::same(6);
    for w in [
        &mut v.widgets.noninteractive,
        &mut v.widgets.inactive,
        &mut v.widgets.hovered,
        &mut v.widgets.active,
        &mut v.widgets.open,
    ] {
        w.corner_radius = r;
    }
    v.widgets.noninteractive.bg_stroke = Stroke::new(1.0_f32, BORDE);
    v.widgets.inactive.weak_bg_fill = TARJETA;
    v.widgets.inactive.bg_fill = TARJETA;
    v.widgets.hovered.weak_bg_fill = TARJETA_ACTIVA;
    v.widgets.hovered.bg_fill = TARJETA_ACTIVA;
    v.widgets.hovered.bg_stroke = Stroke::new(1.0_f32, DORADO.gamma_multiply(0.6));
    v.widgets.active.weak_bg_fill = DORADO.gamma_multiply(0.4);
    ctx.set_visuals(v);

    ctx.style_mut(|s| {
        s.spacing.item_spacing = egui::vec2(8.0, 6.0);
        s.spacing.button_padding = egui::vec2(10.0, 5.0);
        for (estilo, fuente) in s.text_styles.iter_mut() {
            match estilo {
                egui::TextStyle::Heading => fuente.size = 24.0,
                egui::TextStyle::Small => fuente.size = 12.0,
                _ => fuente.size += 1.5,
            }
        }
    });
}

/// Marco de tarjeta reutilizable.
pub fn marco(color_borde: Color32) -> egui::Frame {
    egui::Frame::new()
        .fill(TARJETA)
        .stroke(Stroke::new(1.0_f32, color_borde))
        .corner_radius(CornerRadius::same(10))
        .inner_margin(egui::Margin::same(12))
}

/// "Pastilla" de texto coloreado (etiquetas tipo FEUDAL, Fácil, etc.).
pub fn pastilla(ui: &mut egui::Ui, texto: &str, color: Color32) {
    egui::Frame::new()
        .fill(color.gamma_multiply(0.18))
        .stroke(Stroke::new(1.0_f32, color.gamma_multiply(0.7)))
        .corner_radius(CornerRadius::same(10))
        .inner_margin(egui::Margin::symmetric(8, 2))
        .show(ui, |ui| {
            ui.label(egui::RichText::new(texto).color(color).small().strong());
        });
}
