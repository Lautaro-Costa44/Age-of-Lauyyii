# Age of Lauyyii

Guía liviana para Age of Empires II DE, hecha en Rust con [egui](https://github.com/emilk/egui).

- **56 civilizaciones**: bonos, unidades únicas, tecnologías únicas y bono de equipo copiados del texto en español de [aoe2techtree](https://aoe2techtree.net).
- **Línea de tiempo por civ**: dos aperturas por civilización, ajustadas a sus bonos, en un carrusel de tarjetas. La tarjeta actual queda grande en el centro y la anterior y la siguiente más chicas a los costados.
- **Atajos globales**: avanzás de tarjeta sin salir del juego.
- Timings, counters y consejos.

## Uso

```bash
cargo run --release
```

El ejecutable queda en `target/release/age_of_lauyyii.exe` (~4 MB). En reposo usa 0% de CPU y ~90 MB de RAM: egui solo redibuja ante un evento, o cada 0,5 s mientras corre el reloj.

### Mientras jugás

1. Poné AoE2 en **Pantalla completa sin bordes**. En pantalla completa exclusiva ninguna ventana se puede mostrar encima.
2. Elegí la civ y la línea de tiempo, y activá **Siempre arriba** + **Compacto**.
3. Atajos globales (andan aunque el foco esté en el juego):

| Tecla | Acción |
|---|---|
| **F8** | Siguiente tarjeta |
| **F7** | Tarjeta anterior |
| **F6** | Iniciar/pausar el reloj |

Se cambian en el menú **Teclas** (F1-F12, Pausa, Bloq Despl, Insert). Mientras la guía está abierta, Windows le entrega esas teclas a la guía y el juego no las recibe, así que elegí teclas que no uses en AoE2 (revisá Opciones → Teclas de acceso rápido del juego). Con la ventana de la guía enfocada también funcionan `←`, `→` y `Espacio`.

El reloj multiplica por la velocidad del juego (1,7 = normal en DE) para coincidir con el reloj del juego. Iniciálo (F6) cuando arranque la partida.

Las preferencias (civ, línea, teclas, siempre arriba) se guardan en `config.json` junto al `.exe`.

## Datos

- `data/civs.json`: lo genera `tools/generar_civs.py`. Lo podés editar a mano.
- `data/guia.json`: timings, counters y consejos.

Los datos van embebidos en el `.exe`. Si existe una carpeta `data/` junto al ejecutable o en el directorio actual, la app usa esos archivos, así que podés cambiarlos sin recompilar.

### Actualizar las civs después de un parche

```bash
curl -L -o data.json https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/master/data/data.json
curl -L -o strings_es.json https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/master/data/locales/es/strings.json
python tools/generar_civs.py data.json strings_es.json data/civs.json
```

Si sale una civ nueva, el script avisa que no tiene plan y la omite: agregale una entrada en `PLAN` dentro de `tools/generar_civs.py`.

### Qué está verificado y qué no

- **Verificado contra aoe2techtree**: bonos, unidades únicas, tecnologías únicas y bono de equipo de cada civ, y costos y tiempos de Castillos, Imperial y Telar.
- **No viene de aoe2techtree** (aoe2techtree no tiene build orders): las aperturas son las estándar (Scouts 22, Arqueros 23, Hombres de armas, Fast Castle), ajustadas según los bonos de cada civ. Los tiempos son ideales: CU produciendo sin parar, 25 s por aldeano, Telar incluido.
