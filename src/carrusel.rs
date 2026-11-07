//! Línea de tiempo tipo carrusel: tarjeta actual grande en el centro,
//! anterior y siguiente más chicas a los costados, unidas por una línea.

use crate::data::{Linea, Paso};
use crate::tema;
use eframe::egui::{self, pos2, vec2, Align2, Color32, CornerRadius, FontId, Rect, Sense, Stroke, StrokeKind};

pub fn dibujar(ui: &mut egui::Ui, linea: &Linea, paso: &mut usize, compacto: bool) {
    let n = linea.pasos.len();
    if n == 0 {
        return;
    }
    let ancho = ui.available_width();
    let alto = if compacto { 215.0 } else { 290.0 };
    let (rect, _) = ui.allocate_exact_size(vec2(ancho, alto), Sense::hover());
    let id = ui.id().with(("carrusel", &linea.id));

    // Posición animada (fraccionaria) para que las tarjetas se deslicen.
    let pos = ui.ctx().animate_value_with_time(id, *paso as f32, 0.22);

    // Tamaño de las tarjetas laterales respecto de la actual y espacio entre ellas:
    // se calcula para que las laterales entren completas, sin taparse.
    const LADO: f32 = 0.58;
    let hueco = if compacto { 14.0 } else { 26.0 };
    let ancho_actual = (ancho * 0.46)
        .min((ancho / 2.0 - hueco - 4.0) / (0.5 + LADO))
        .clamp(160.0, 540.0);
    let separacion = ancho_actual * (1.0 + LADO) / 2.0 + hueco;
    let painter = ui.painter_at(rect);

    // Línea que une las tarjetas
    let cy = rect.center().y;
    painter.line_segment(
        [pos2(rect.left(), cy), pos2(rect.right(), cy)],
        Stroke::new(2.0_f32, tema::BORDE),
    );

    // Dibujar de la más lejana a la más cercana, así la actual queda arriba.
    let mut indices: Vec<usize> = (0..n)
        .filter(|&i| (i as f32 - pos).abs() < 1.9)
        .collect();
    indices.sort_by(|a, b| {
        let da = (*a as f32 - pos).abs();
        let db = (*b as f32 - pos).abs();
        db.partial_cmp(&da).unwrap()
    });

    for i in indices {
        let d = i as f32 - pos;
        let t = d.abs().min(1.0);
        let escala = 1.0 - (1.0 - LADO) * t;
        let mut alfa = 1.0 - 0.5 * t;
        if d.abs() > 1.0 {
            alfa *= ((1.9 - d.abs()) / 0.9).clamp(0.0, 1.0);
        }
        let centro = pos2(rect.center().x + d * separacion, cy);
        let tam = vec2(ancho_actual * escala, alto * 0.94 * (1.0 - 0.3 * t));
        let r = Rect::from_center_size(centro, tam);
        tarjeta(ui, &painter, r, &linea.pasos[i], i, n, escala, alfa, d.abs() < 0.5, compacto);
        if ui.interact(r, id.with(i), Sense::click()).clicked() {
            *paso = i;
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn tarjeta(
    ui: &egui::Ui,
    painter: &egui::Painter,
    r: Rect,
    p: &Paso,
    i: usize,
    n: usize,
    escala: f32,
    alfa: f32,
    actual: bool,
    compacto: bool,
) {
    let c_fase = tema::color_fase(&p.fase);
    let a = |c: Color32| c.gamma_multiply(alfa);
    let radio = CornerRadius::same((10.0 * escala) as u8);

    // Sombra + fondo
    painter.rect_filled(r.translate(vec2(0.0, 4.0)), radio, Color32::from_black_alpha((70.0 * alfa) as u8));
    painter.rect_filled(r, radio, if actual { tema::TARJETA_ACTIVA } else { tema::TARJETA });
    let borde = if actual {
        Stroke::new(2.0_f32, tema::DORADO)
    } else {
        Stroke::new(1.0_f32, a(tema::BORDE))
    };
    painter.rect_stroke(r, radio, borde, StrokeKind::Inside);
    // Franja de color de la edad arriba
    let franja = Rect::from_min_size(r.min + vec2(1.0, 1.0), vec2(r.width() - 2.0, 4.0 * escala));
    painter.rect_filled(franja, CornerRadius { nw: radio.nw, ne: radio.ne, sw: 0, se: 0 }, a(c_fase));

    let pad = 14.0 * escala;
    let interior = r.shrink(pad);
    let p2 = painter.with_clip_rect(r.shrink(2.0));
    let base = if compacto { 13.5 } else { 16.0 };
    // El texto se achica menos que la tarjeta para que las laterales sigan legibles.
    let escala = 0.55 + 0.45 * escala;
    let f = |tam: f32| FontId::proportional(tam * escala);

    // Encabezado: PASO i/n · edad
    let mut y = interior.top() + 2.0 * escala;
    p2.text(
        pos2(interior.left(), y),
        Align2::LEFT_TOP,
        format!("{}PASO {}/{}", if p.hito { "★ " } else { "" }, i + 1, n),
        f(11.5),
        a(if p.hito { tema::DORADO } else { tema::TEXTO_SUAVE }),
    );
    let fase = tema::nombre_fase(&p.fase);
    let g = ui.painter().layout_no_wrap(fase.into(), f(10.5), a(c_fase));
    let pill = Rect::from_min_size(
        pos2(interior.right() - g.size().x - 12.0 * escala, y - 2.0 * escala),
        g.size() + vec2(12.0 * escala, 4.0 * escala),
    );
    p2.rect_filled(pill, CornerRadius::same(8), a(c_fase.gamma_multiply(0.18)));
    p2.galley(pill.min + vec2(6.0 * escala, 2.0 * escala), g, a(c_fase));
    y += 22.0 * escala;

    // Aldeanos (número grande) + tiempo
    if p.aldeanos > 0 {
        let g = ui.painter().layout_no_wrap(p.aldeanos.to_string(), f(if compacto { 24.0 } else { 32.0 }), a(tema::TEXTO));
        let alto_num = g.size().y;
        let ancho_num = g.size().x;
        p2.galley(pos2(interior.left(), y), g, a(tema::TEXTO));
        p2.text(
            pos2(interior.left() + ancho_num + 6.0 * escala, y + alto_num - 4.0 * escala),
            Align2::LEFT_BOTTOM,
            "aldeanos",
            f(12.0),
            a(tema::TEXTO_SUAVE),
        );
        if let Some(t) = &p.tiempo {
            p2.text(
                pos2(interior.right(), y + alto_num - 4.0 * escala),
                Align2::RIGHT_BOTTOM,
                t,
                FontId::monospace(13.0 * escala),
                a(tema::DORADO),
            );
        }
        y += alto_num + 4.0 * escala;
    }

    // Texto del paso
    let reservado_abajo = if p.recursos().iter().any(|&x| x > 0) { 30.0 * escala } else { 0.0 };
    let g = ui
        .painter()
        .layout(p.texto.clone(), f(base), a(tema::TEXTO), interior.width());
    let max_y = interior.bottom() - reservado_abajo;
    let texto_rect = Rect::from_min_max(pos2(interior.left(), y), pos2(interior.right(), max_y));
    painter.with_clip_rect(texto_rect).galley(pos2(interior.left(), y), g, a(tema::TEXTO));

    // Barra de recursos
    let rec = p.recursos();
    let total: u32 = rec.iter().sum();
    if total > 0 {
        let barra = Rect::from_min_size(
            pos2(interior.left(), interior.bottom() - 26.0 * escala),
            vec2(interior.width(), 7.0 * escala),
        );
        let mut x = barra.left();
        for (k, &cant) in rec.iter().enumerate() {
            if cant == 0 {
                continue;
            }
            let w = barra.width() * cant as f32 / total as f32;
            p2.rect_filled(
                Rect::from_min_size(pos2(x, barra.top()), vec2(w - 1.0, barra.height())),
                CornerRadius::same(2),
                a(tema::RECURSOS[k].0),
            );
            x += w;
        }
        let mut x = interior.left();
        for (k, &cant) in rec.iter().enumerate() {
            if cant == 0 {
                continue;
            }
            let (color, nombre) = tema::RECURSOS[k];
            let r = p2.text(
                pos2(x, barra.bottom() + 4.0 * escala),
                Align2::LEFT_TOP,
                format!("{nombre} {cant}"),
                f(11.5),
                a(color),
            );
            x = r.right() + 12.0 * escala;
        }
    }
}

/// Fila de puntos de progreso (clic para saltar a un paso).
pub fn puntos(ui: &mut egui::Ui, linea: &Linea, paso: &mut usize) {
    let n = linea.pasos.len();
    if n == 0 {
        return;
    }
    let ancho = ui.available_width();
    let (rect, _) = ui.allocate_exact_size(vec2(ancho, 18.0), Sense::hover());
    let painter = ui.painter_at(rect);
    let paso_x = (ancho / n as f32).min(28.0);
    let inicio = rect.center().x - paso_x * (n as f32 - 1.0) / 2.0;
    painter.line_segment(
        [pos2(inicio, rect.center().y), pos2(inicio + paso_x * (n as f32 - 1.0), rect.center().y)],
        Stroke::new(1.0_f32, tema::BORDE),
    );
    for (i, p) in linea.pasos.iter().enumerate() {
        let c = pos2(inicio + paso_x * i as f32, rect.center().y);
        let actual = i == *paso;
        let color = tema::color_fase(&p.fase);
        let radio = if actual { 6.5 } else if p.hito { 4.5 } else { 3.5 };
        if i < *paso {
            painter.circle_filled(c, radio, color.gamma_multiply(0.55));
        } else {
            painter.circle_filled(c, radio, if actual { tema::DORADO } else { tema::FONDO });
            painter.circle_stroke(c, radio, Stroke::new(1.5_f32, if actual { tema::DORADO } else { color }));
        }
        let zona = Rect::from_center_size(c, vec2(paso_x.max(12.0), 18.0));
        let resp = ui.interact(zona, ui.id().with(("punto", i)), Sense::click());
        if resp.clicked() {
            *paso = i;
        }
        resp.on_hover_text(format!("Paso {}: {}", i + 1, recorte(&p.texto, 70)));
    }
}

fn recorte(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        format!("{}…", s.chars().take(max).collect::<String>())
    }
}
