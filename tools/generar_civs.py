"""Genera data/civs.json a partir de los datos de aoe2techtree + un plan por civ.

Uso:
    python tools/generar_civs.py <data.json> <strings_es.json> data/civs.json

data.json y strings_es.json salen del repo SiegeEngineers/aoe2techtree:
    https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/master/data/data.json
    https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/master/data/locales/es/strings.json

Los bonos, unidades y tecnologías únicas se copian literalmente del techtree
(así quedan verificados). Las líneas de tiempo se arman con plantillas de
apertura estándar + ajustes según los bonos de cada civilización.
"""

import json
import re
import sys

ALDEANO = 25  # segundos de juego por aldeano
FEUDAL, CASTILLOS = 130, 160

# ---------------------------------------------------------------------------
# Plan por civilización.
#   ap: apertura principal, alt: alternativa
#   cas / imp: plan para Castillos / Imperial
#   notas: textos extra que se insertan en etapas concretas
#   mods: ajustes que cambian el cálculo de la línea de tiempo
# ---------------------------------------------------------------------------
PLAN = {
    "Armenians": dict(dif="Media", ap="maa", alt="fc",
        cas="Construí una iglesia fortificada (la primera trae una reliquia gratis). Espadachines + arqueros con arco compuesto.",
        imp="Relicarios para la infantería. Campeones + arqueros con arco compuesto, sacerdotes guerreros para curar.",
        notas=dict(feudal="Bono armenio: Soldado con espada larga y Piquero ya se investigan en Feudal.")),
    "Aztecs": dict(dif="Media", ap="maa", alt="arqueros",
        cas="Monjes + guerreros águila. Atlatl para los guerrilleros. Juntá reliquias (bono de equipo: +33 % de oro).",
        imp="Guerras florales (+4 de ataque a la infantería): jaguares o campeones + águilas de élite.",
        notas=dict(inicio="Empezás con +50 de oro.", madera="Tus aldeanos cargan +3: rinden más por viaje.",
                   feudal="Tus unidades se entrenan 15 % más rápido: el push pega antes.")),
    "Bengalis": dict(dif="Media", ap="fc", alt="arqueros",
        cas="Rathas o arqueros sobre elefante. Investigá Paiks.",
        imp="Mahāyāna (aldeanos y monjes ocupan menos población). Elefantes de combate + rathas.",
        notas=dict(feudal="Al avanzar de edad el CU genera 2 aldeanos gratis: mandalos directo a trabajar."),
        mods=dict(aldeanos_por_edad=2)),
    "Berbers": dict(dif="Fácil", ap="scouts", alt="fc",
        cas="Caballeros (15 % más baratos) y arqueros en camello. Camellos magrebíes.",
        imp="Establos 20 % más baratos: caballeros/camellos + escaramuzadores zenetes.",
        notas=dict(comida="Tus aldeanos se mueven más rápido: los viajes al molino cuestan menos.")),
    "Bohemians": dict(dif="Media", ap="fc", alt="maa",
        cas="Monjes (Fervor y Santidad también aceleran a los aldeanos). Química y artilleros manuales ya en Castillos. Carretas de guerra husitas.",
        imp="Obuses + artilleros manuales + alabarderos (los lanceros pegan 25 % más).",
        notas=dict(oro="Las tecnologías de los campamentos mineros son gratis.")),
    "Britons": dict(dif="Fácil", ap="arqueros", alt="fc",
        cas="Ballesteros con alcance extra o arqueros de arco largo. 2-3 CU más: cuestan 50 % menos de madera. Hidalgo.",
        imp="Arqueros de arco largo de élite + Lobo de guerra para los trebuchets.",
        notas=dict(comida="Tus pastores trabajan 25 % más rápido: estirá las ovejas lo más posible.")),
    "Bulgarians": dict(dif="Media", ap="maa", alt="scouts",
        cas="Konniks o espadachines. El krepost ya se puede construir en Castillos. Estribos.",
        imp="Bagains (+5 de armadura a la milicia): campeones + konniks de élite.",
        notas=dict(feudal="Las mejoras de la milicia son gratis: tus hombres de armas no cuestan investigación.")),
    "Burgundians": dict(dif="Media", ap="fc", alt="scouts",
        cas="Caballeros temprano (la mejora a caballeros está disponible en Castillos). Viñedos de Borgoña para sumar oro.",
        imp="Caballeros + costilleros. La pólvora tiene +25 % de ataque.",
        notas=dict(madera="Hacha de doble filo ya está disponible en la Edad Oscura y cuesta 40 % menos de comida.")),
    "Burmese": dict(dif="Media", ap="maa", alt="fc",
        cas="Arambais o elefantes de combate. Monasterio barato (50 % menos).",
        imp="Howdah. Elefantes de combate de élite + arambais.",
        notas=dict(madera="Las tecnologías del campamento maderero son gratis.",
                   feudal="Tu infantería tiene +1 de ataque en Feudal.")),
    "Byzantines": dict(dif="Fácil", ap="arqueros", alt="fc",
        cas="Caballeros o catafractas + counters baratos (camellos, guerrilleros, lanceros 25 % menos).",
        imp="Imperial cuesta 33 % menos: llegá rápido. Catafractas + Logística.",
        notas=dict(feudal="Guerrilleros y lanceros cuestan 25 % menos: perfectos para defender.")),
    "Celts": dict(dif="Fácil", ap="scouts", alt="maa",
        cas="Mangoneles (el asedio ataca 25 % más rápido) + infantería rápida.",
        imp="Furor celta: onagros y arietes con 40 % más de PR + jinetes celtas.",
        notas=dict(madera="Tus leñadores trabajan 15 % más rápido.")),
    "Chinese": dict(dif="Difícil", ap="scouts", alt="arqueros",
        cas="Chu Ko Nu + monjes o caballeros. Tus tecnologías son más baratas.",
        imp="Cohetería. Chu Ko Nu de élite + escorpiones.",
        notas=dict(inicio="Empezás sin comida (-200): encolá el primer aldeano apenas junten 50."),
        mods=dict(iniciales=6, retraso=25)),
    "Cumans": dict(dif="Media", ap="scouts", alt="fc",
        cas="Kipchaks o caballeros. Ganadería de la estepa (caballería se entrena 100 % más rápido).",
        imp="Caballería rápida + Mercenarios cumanos.",
        notas=dict(feudal="Podés construir un 2do CU en Feudal: es tu gran ventaja económica.")),
    "Danes": dict(dif="Media", ap="maa", alt="fc",
        cas="Vikingos de Jomsborg + mangoneles. Cada edificio enemigo destruido te da 25 % de botín.",
        imp="Hamask + Furia nórdica (asedio +40 % contra edificios).",
        notas=dict(comida="Tus aldeanos dejan 5 % más de comida.",
                   feudal="Las mejoras del cuartel cuestan 66 % menos de oro.")),
    "Dravidians": dict(dif="Media", ap="maa", alt="arqueros",
        cas="Espadachines urumi + guerrilleros. Arqueros sobre elefante.",
        imp="Acero wootz (ignoran armadura). Campeones/urumi + elefantes.",
        notas=dict(feudal="Recibís +200 de madera al llegar a la nueva edad: usala para granjas o galerías.")),
    "Ethiopians": dict(dif="Fácil", ap="arqueros", alt="fc",
        cas="Castillos rápido con el oro extra. Ballesteros (atacan 18 % más rápido) + shotelai.",
        imp="Mecanismos de torsión para el asedio. Arbalesteros + piqueros (mejora gratis).",
        notas=dict(feudal="Recibís +100 de oro y +100 de comida al llegar a la nueva edad.")),
    "Franks": dict(dif="Fácil", ap="scouts", alt="fc",
        cas="Caballeros (+20 % de PR) desde 2-3 establos. Caballería: establos 40 % más rápidos.",
        imp="Paladines + lanzadores de hachas.",
        notas=dict(comida="Tus recolectores de bayas trabajan 15 % más rápido: poné el molino en bayas grandes.",
                   granjas="Las tecnologías del molino son gratis.")),
    "Georgians": dict(dif="Media", ap="scouts", alt="fc",
        cas="Monaspas o caballeros. Iglesias fortificadas cerca de tus aldeanos (+10 % de velocidad de trabajo).",
        imp="Caballería aznauri (ocupa menos población). Monaspas de élite.",
        notas=dict(inicio="Empezás con un carro de mulas: usalo como campamento móvil en el bosque.")),
    "Goths": dict(dif="Fácil", ap="maa", alt="scouts",
        cas="Huscarles contra arqueros. Infantería barata desde varios cuarteles.",
        imp="Anarquía + Movilización: masa de huscarles y campeones.",
        notas=dict(caza="El Telar es instantáneo y tus cazadores cargan +15: atraé jabalíes sin miedo."),
        mods=dict(telar=0)),
    "Gurjaras": dict(dif="Media", ap="scouts", alt="fc",
        cas="Jinetes de shrivamsha o camellos. Chatrias (25 % menos comida).",
        imp="Guardas fronterizos. Camellos + arqueros sobre elefante.",
        notas=dict(inicio="Empezás con 2 arbustos extra.",
                   comida="Podés guarnecer ovejas en el molino para producir comida pasiva.")),
    "Hindustanis": dict(dif="Media", ap="fc", alt="arqueros",
        cas="Boom con aldeanos baratos. Jinetes de camello (atacan 20 % más rápido).",
        imp="Camello imperial + artilleros manuales con Shatagni. Camino del Gran Tronco.",
        notas=dict(inicio="Tus aldeanos cuestan menos comida: el boom es tu fuerte.")),
    "Huns": dict(dif="Media", ap="scouts", alt="fc",
        cas="Arqueros a caballo (10 % más baratos) o caballeros. Razias: tarcanos en los establos.",
        imp="Arqueros a caballo pesados + tarcanos. Ateísmo contra reliquias.",
        notas=dict(inicio="No necesitás casas (empezás con 100 menos de madera)."),
        mods=dict(sin_casas=True)),
    "Incas": dict(dif="Media", ap="maa", alt="arqueros",
        cas="Kamayuks + soldados con honda. Desde Castillos tus aldeanos reciben las mejoras de infantería.",
        imp="Escudos de tela. Guerreros águila de élite + kamayuks.",
        notas=dict(inicio="Tus casas dan 10 de población: con 1 casa alcanza al principio. Empezás con una llama extra."),
        mods=dict(casas_10=True)),
    "Italians": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Ballesteros genoveses contra caballería. Tus arqueros tienen +1/+1 de armadura.",
        imp="Pirotecnia: artilleros manuales. Condotieri contra la pólvora.",
        notas=dict(feudal="Avanzar de edad te cuesta 15 % menos.")),
    "Japanese": dict(dif="Media", ap="maa", alt="arqueros",
        cas="Samuráis o caballeros + ballesteros. Yasama para las torres.",
        imp="Campeones (atacan 33 % más rápido) + arbalesteros. Kataparuto.",
        notas=dict(madera="Molino y campamentos cuestan 50 % menos: poné campamentos bien pegados al recurso.")),
    "Jurchens": dict(dif="Difícil", ap="scouts", alt="fc",
        cas="Pagodas de hierro o caballeros + granaderos. Ingenieros de asedio ya en Castillos.",
        imp="Bombas trueno. Caballería + pólvora.",
        notas=dict(caza="La carne no se descompone: no hace falta apurarse con los jabalíes.",
                   feudal="Tus unidades montadas atacan 25 % más rápido desde Feudal.")),
    "Khitans": dict(dif="Difícil", ap="scouts", alt="fc",
        cas="Arqueros a caballo pesados (mejora ya en Castillos y 50 % más barata) o Liao Dao.",
        imp="Caballería ordo. Trebuchets montados.",
        notas=dict(granjas="Construí pasturas: reemplazan a las granjas.")),
    "Khmer": dict(dif="Media", ap="scouts", alt="fc",
        cas="Elefantes con balista + elefantes de combate. Ballesta doble.",
        imp="Colmillos de acero. Elefantes de combate de élite.",
        notas=dict(feudal="No necesitás edificios para avanzar de edad: podés avanzar sin cuartel.",
                   granjas="Tus granjeros no necesitan molino ni CU para depositar: granjas donde quieras."),
        mods=dict(sin_requisitos=True)),
    "Koreans": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Carromatos de guerra o ballesteros (armaduras gratis). Torres fuertes.",
        imp="Arbalesteros + onagros con Shinkichon. Eupseong.",
        notas=dict(feudal="Tus soldados a distancia cuestan 50 % menos de madera.")),
    "Lithuanians": dict(dif="Media", ap="scouts", alt="fc",
        cas="Caballeros + monjes para juntar reliquias (+1 de ataque por reliquia, hasta +4).",
        imp="Leitis + caballeros con reliquias. Escudo rectangular.",
        notas=dict(inicio="Cada CU te da +100 de comida: tu Edad Oscura arranca más rápido.")),
    "Magyars": dict(dif="Fácil", ap="scouts", alt="fc",
        cas="Caballeros o arqueros a caballo. Huszár magiares.",
        imp="Ejército corviniano (huszár sin oro). Arco recurvo.",
        notas=dict(inicio="Tus aldeanos matan lobos de un golpe.",
                   feudal="Exploradores 15 % más baratos y Forja gratis: ganás las peleas de scouts.")),
    "Malay": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Elefantes de combate baratos o reclutas con karambit + ballesteros.",
        imp="Leva en masa: espadachines sin oro + elefantes de combate.",
        notas=dict(feudal="Avanzás de edad 66 % más rápido: llegás mucho antes."),
        mods=dict(factor_edad=1 / 1.66)),
    "Malians": dict(dif="Media", ap="maa", alt="fc",
        cas="Guardianas gbeto o caballeros con Farimba. Gran asamblea.",
        imp="Campeones + arbalesteros o caballería con Farimba.",
        notas=dict(feudal="Tus unidades de cuartel tienen +1 de armadura antiperforación en Feudal.",
                   oro="Tus aldeanos depositan 10 % más de oro.")),
    "Mapuche": dict(dif="Media", ap="scouts", alt="fc",
        cas="Konas + lanceros/guerrilleros entrenados desde asentamientos.",
        imp="Malón. Jinetes con boleadoras + Butalmapu.",
        notas=dict(comida="Tus recolectores entregan 25 % más de comida.")),
    "Mayans": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Arqueros emplumados + guerreros águila. Tus recursos duran 15 % más.",
        imp="Holcanes para las águilas. Arbalesteros 30 % más baratos.",
        notas=dict(inicio="Empezás con 4 aldeanos (y 50 menos de comida)."),
        mods=dict(iniciales=4)),
    "Mongols": dict(dif="Difícil", ap="scouts", alt="fc",
        cas="Mangudai o arqueros a caballo. Caballería ligera con más PR.",
        imp="Húsares + mangudai. Instrucción militar para el asedio.",
        notas=dict(caza="Tus cazadores trabajan 40 % más rápido: empujá ciervos con el explorador hacia el CU.")),
    "Muisca": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Guerreros guecha + monjes. Tus arqueros tienen armadura cuerpo a cuerpo extra.",
        imp="Herbología y Huaracas. Guardias del templo.",
        notas=dict(feudal="Avanzar de edad cuesta 50 % menos de oro.")),
    "Persians": dict(dif="Media", ap="fc", alt="scouts",
        cas="2-3 CU más (trabajan más rápido). Caballeros o savars. Tácticas de los partias ya en Castillos.",
        imp="Elefantes de guerra o savars. Ciudadelas.",
        notas=dict(inicio="Empezás con +50 de madera y comida, y tu CU trabaja más rápido."),
        mods=dict(velocidad_cu=1.05)),
    "Poles": dict(dif="Media", ap="scouts", alt="fc",
        cas="Caballeros con Privilegios de Szlachta (60 % menos oro). Tus canteros también generan oro.",
        imp="Húsares alados + martillos de guerra. Legado lequítico.",
        notas=dict(comida="El folwark reemplaza al molino.",
                   feudal="Los exploradores cuestan 50 % menos de comida.")),
    "Portuguese": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Ballesteros o caballeros (todo cuesta 20 % menos de oro).",
        imp="Cañones de salvas + arbalesteros. Circunnavegación en mapas de agua.",
        notas=dict(comida="Tus recolectores también generan madera.")),
    "Romans": dict(dif="Media", ap="maa", alt="fc",
        cas="Legionarios/espadachines + escorpiones (50 % menos oro). Centuriones.",
        imp="Comitatenses + Balistas.",
        notas=dict(comida="Tus aldeanos trabajan 5 % más rápido.")),
    "Saracens": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Camellos + arqueros. Usá el mercado (tarifa 5 %) para ajustar recursos.",
        imp="Mamelucos. Contrapesos para el asedio.",
        notas=dict(feudal="El mercado cuesta 100 menos de madera: vendé y comprá sin miedo.")),
    "Saxons": dict(dif="Media", ap="maa", alt="fc",
        cas="Tropas del hogar + torres y castillos con el doble de flechas. Infantería más barata por cada CU/castillo.",
        imp="Muralla escudo. Masa de infantería.",
        notas=dict(madera="Cada molino o campamento te da +50 de comida y +10 de piedra al construirlo.")),
    "Shu": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Ballesteros (tecnologías 25 % más baratas) + carros de guerra.",
        imp="Cargador: proyectiles extra. Guardias de la pluma blanca.",
        notas=dict(madera="Tus leñadores también generan comida.")),
    "Sicilians": dict(dif="Media", ap="fc", alt="scouts",
        cas="Tus CU se construyen 100 % más rápido: boom. Caballeros + serjeants.",
        imp="Primera cruzada. Cota de malla para los caballeros.",
        notas=dict(inicio="Empezás con +100 de piedra. La torre del homenaje ya se construye en la Edad Oscura."),
        mods=dict()),
    "Slavs": dict(dif="Fácil", ap="scouts", alt="fc",
        cas="Boyardos o caballeros + asedio 15 % más barato.",
        imp="Druzhina. Alabarderos + onagros.",
        notas=dict(granjas="Tus granjeros trabajan 15 % más rápido: pasá a granjas sin miedo.")),
    "Spanish": dict(dif="Media", ap="scouts", alt="fc",
        cas="Conquistadores o caballeros. Las mejoras de la herrería no cuestan oro.",
        imp="Supremacía para los aldeanos. Artilleros + paladines.",
        notas=dict(madera="Tus constructores trabajan 30 % más rápido.",
                   feudal="Ganás +20 de oro por cada tecnología investigada.")),
    "Tatars": dict(dif="Media", ap="scouts", alt="fc",
        cas="Arqueros a caballo (Dactilera gratis) o keshiks. Cada CU nuevo trae 2 ovejas.",
        imp="Armadura de seda. Camellos llameantes. Tácticas de asedio timúridas.",
        notas=dict(comida="Tus ovejas duran 50 % más.")),
    "Teutons": dict(dif="Fácil", ap="fc", alt="maa",
        cas="Caballeros con armadura extra. Acorazado primitivo para los arietes.",
        imp="Caballeros de la Orden Teutónica + paladines. Almenas.",
        notas=dict(granjas="Tus granjas cuestan 40 % menos.")),
    "Tupi": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Arqueros de los bosques + guerreros ibirapema.",
        imp="Curare (daño de veneno). Caciques.",
        notas=dict(inicio="Empezás con +25 de cada recurso.",
                   feudal="Las mejoras de galería y cuartel cuestan 50 % menos de comida.")),
    "Turks": dict(dif="Media", ap="scouts", alt="fc",
        cas="Tomá mucho oro (mineros 25 % más rápidos). Química gratis.",
        imp="Jenízaros + cañones de asedio. Artillería. Húsares (mejoras gratis) como unidad sin oro.",
        notas=dict(feudal="Las mejoras de la caballería de exploración son gratis.")),
    "Varangians": dict(dif="Media", ap="scouts", alt="fc",
        cas="Caballeros + guardias varegos. Legado de Vendel.",
        imp="Jarls. Gothikon.",
        notas=dict(comida="Pastoreo, pesca y caza también te dan oro.")),
    "Vietnamese": dict(dif="Media", ap="arqueros", alt="fc",
        cas="Arqueros de ratán + guerrilleros (+20 % de PR). Papel moneda para el oro.",
        imp="Guerrillero imperial. Chatras para los elefantes.",
        notas=dict(inicio="Ves los CU enemigos desde el inicio: mandá el explorador directo.",
                   madera="Las mejoras económicas no cuestan madera y se investigan el doble de rápido.")),
    "Vikings": dict(dif="Fácil", ap="maa", alt="fc",
        cas="Berserkers o espadachines + ballesteros. Carretilla gratis: boom.",
        imp="Jefes. Campeones + arbalesteros (Bogsveigar).",
        notas=dict(feudal="La Carretilla y el Carro de mano son gratis.")),
    "Wei": dict(dif="Difícil", ap="scouts", alt="fc",
        cas="Caballería tigresa o saqueadores xianbei. Mangoneles 25 % más baratos.",
        imp="Armadura de Ming Guang. Tuntian.",
        notas=dict(madera="Cada mejora económica te regala un aldeano: investigalas temprano.")),
    "Wu": dict(dif="Media", ap="maa", alt="fc",
        cas="Espadachines de Jian + arqueros de fuego. Sun Jian.",
        imp="Tácticas de los Acantilados Rojos. Tigre sentado.",
        notas=dict(feudal="Cada edificio militar te da +55 de comida al construirlo.")),
}

NOMBRES_APERTURA = {
    "scouts": ("Exploradores (Scouts)", "Feudal agresivo", "Caballería ligera en Feudal para molestar la economía rival."),
    "arqueros": ("Arqueros", "Feudal agresivo", "Masa de arqueros en Feudal; necesita oro temprano."),
    "maa": ("Hombres de armas → Arqueros", "Feudal agresivo", "3 milicias que suben a hombres de armas al llegar a Feudal; después arqueros."),
    "fc": ("Castillos rápido (Fast Castle)", "Económico / Boom", "Saltás casi toda la Feudal para llegar rápido a Castillos y hacer boom."),
    "fc_boom": ("Fast Castle + Boom (guía NelsonSKA)", "Económico / Boom",
                "Llegar rápido a Castillos y armar 3 Centros urbanos produciendo aldeanos sin parar. "
                "Ideal en mapas cerrados (Arena, Selva Negra, Túnel Amazónico) o de pocket en equipos."),
}


# Notas propias de cada civ para el boom en Castillos (se suman a la línea "fc_boom").
NOTAS_BOOM = {
    "Britons": "Tus CU cuestan 50 % menos de madera desde Castillos: los 2 CU salen con ~275 de madera.",
    "Vikings": "Carretilla y Carro de mano son gratis: esa comida y madera va directo a más aldeanos.",
    "Persians": "Tus CU trabajan más rápido en cada edad: sacás más aldeanos por minuto.",
    "Teutons": "Tus granjas cuestan 40 % menos: pasá leñadores a granjas más seguido.",
    "Cumans": "Podés construir un 2do CU ya en Feudal: adelantá el boom.",
    "Bulgarians": "Tus CU cuestan 50 % menos de piedra.",
    "Sicilians": "Tus CU se construyen 100 % más rápido.",
    "Hindustanis": "Tus aldeanos cuestan menos comida: el boom rinde más.",
    "Chinese": "Tus CU dan +15 de población: necesitás menos casas.",
    "Incas": "Tus casas dan 10 de población: necesitás menos casas.",
    "Huns": "No necesitás casas: nunca te bloqueás de población.",
    "Lithuanians": "Cada CU nuevo te da +100 de comida.",
    "Tatars": "Cada CU nuevo trae 2 ovejas: ponelas debajo del CU.",
    "Wei": "Cada mejora económica regala un aldeano: Carretilla, Collera y Hacha de doble filo apenas puedas.",
    "Vietnamese": "Tus mejoras económicas no cuestan madera y se investigan el doble de rápido.",
    "Burgundians": "Tus mejoras económicas salen una edad antes y más baratas: Arado pesado y Carretilla ya en Feudal.",
    "Malians": "Tus edificios (CU incluidos) cuestan 15 % menos de madera.",
    "Saxons": "Cada molino o campamento nuevo te da +50 de comida y +10 de piedra.",
    "Khmer": "Tus granjeros no necesitan molino: granjas donde quieras alrededor de los CU nuevos.",
}
# Civs que el video menciona como más cómodas para esta estrategia
RECOMENDADAS_BOOM = {"Britons", "Vikings", "Persians", "Teutons"}


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


class Linea:
    """Arma pasos llevando la cuenta de aldeanos, reparto y tiempo."""

    def __init__(self, civ, plan):
        self.mods = plan.get("mods", {})
        self.notas = dict(plan.get("notas", {}))
        if civ in NOTAS_BOOM:
            self.notas["boom"] = NOTAS_BOOM[civ]
        self.ini = self.mods.get("iniciales", 3)
        self.vel = self.mods.get("velocidad_cu", 1.0)
        self.t = self.mods.get("retraso", 0)
        self.v = self.ini
        self.pasos = []
        self.fase = "Oscura"

    def nota(self, clave):
        n = self.notas.get(clave)
        return f" ★ {n}" if n else ""

    def paso(self, hasta, texto, dist, hito=False):
        nuevos = max(0, hasta - self.v)
        self.t += nuevos * ALDEANO / self.vel
        self.v = max(self.v, hasta)
        c, m, o, p = dist
        self.pasos.append(dict(aldeanos=self.v, texto=texto, comida=c, madera=m, oro=o,
                               piedra=p, tiempo="~" + mmss(self.t), fase=self.fase, hito=hito))

    def durante(self, texto, dist):
        c, m, o, p = dist
        self.pasos.append(dict(aldeanos=self.v, texto=texto, comida=c, madera=m, oro=o, piedra=p,
                               tiempo="durante el avance", fase=self.pasos[-1]["fase"], hito=False))

    def telar(self):
        self.t += self.mods.get("telar", 25)

    def avanzar(self, edad, texto, dist):
        base = FEUDAL if edad == "Feudal" else CASTILLOS
        self.paso(self.v, texto, dist, hito=True)
        self.pasos[-1]["tiempo"] = "clic ~" + mmss(self.t)
        self.t += base * self.mods.get("factor_edad", 1.0)
        self.fase = edad
        self.v += self.mods.get("aldeanos_por_edad", 0)


def casas(l, normal):
    if l.mods.get("sin_casas"):
        return "Sin casas: "
    if l.mods.get("casas_10"):
        return "1 casa (da 10 de población); "
    return normal


def edad_oscura(l):
    if l.ini == 6:
        ini = "Los 6 aldeanos iniciales: 2 construyen casas, 4 a ovejas bajo el CU."
    elif l.ini == 4:
        ini = "Los 4 aldeanos iniciales: 2 construyen casas, 2 a ovejas. Aldeanos nuevos a ovejas."
    else:
        ini = casas(l, "Los 3 iniciales: 2 construyen una casa cada uno, 1 a ovejas. ") + \
            "Aldeanos 4-6 a ovejas bajo el CU."
    l.paso(6, ini + " El explorador busca ovejas." + l.nota("inicio"), (6, 0, 0, 0))
    l.paso(10, "Aldeanos 7-10 a madera; el 7 construye el campamento maderero." + l.nota("madera"), (6, 4, 0, 0))
    l.telar()
    l.paso(11, "Aldeano 11 a ovejas. Telar y atraé el 1er jabalí al CU con un aldeano de ovejas." + l.nota("caza"), (7, 4, 0, 0))
    molino = "folwark" if "folwark" in l.notas.get("comida", "") else "molino"
    l.paso(15, f"Aldeanos 12-15 a bayas; el 12 construye {'' if l.mods.get('sin_casas') else 'una casa y '}el {molino}." + l.nota("comida"), (11, 4, 0, 0))
    l.paso(17, "Aldeanos 16-17 a ovejas/jabalí. Atraé el 2do jabalí cuando el 1ro esté por terminarse.", (13, 4, 0, 0))


def subida(l, req):
    if l.mods.get("sin_requisitos"):
        return "no necesitás edificios para avanzar"
    return req


def fin(l, plan, dist_cas, v_cas):
    texto = "Con 800 comida y 200 oro: clic en Castillos. Seguí produciendo aldeanos y unidades mientras subís."
    l.avanzar("Castillos", "", dist_cas)  # registra el paso y suma el tiempo de investigación
    clic = l.pasos.pop()
    # el clic se hace recién al llegar a v_cas aldeanos
    extra = max(0, v_cas - clic["aldeanos"]) * ALDEANO / l.vel
    l.t += extra
    c, m, o, p = dist_cas
    t_clic = l.t - CASTILLOS * l.mods.get("factor_edad", 1.0)
    l.pasos.append(dict(aldeanos=max(v_cas, clic["aldeanos"]), texto=texto + l.nota("oro"), comida=c, madera=m,
                        oro=o, piedra=p, tiempo="clic ~" + mmss(t_clic), fase="Feudal", hito=True))
    l.v = max(v_cas, clic["aldeanos"]) + l.mods.get("aldeanos_por_edad", 0)
    l.pasos.append(dict(aldeanos=l.v, texto="LLEGADA A CASTILLOS. " + plan["cas"] + " Carretilla y Arado pesado.",
                        comida=c, madera=m, oro=o, piedra=p, tiempo="~" + mmss(l.t), fase="Castillos", hito=True))
    l.pasos.append(dict(aldeanos=0, texto="IMPERIAL (con ~80-110 aldeanos). " + plan["imp"],
                        comida=0, madera=0, oro=0, piedra=0, tiempo=None, fase="Imperial", hito=True))


def apertura(nombre, l, plan):
    if nombre == "fc_boom":
        apertura_fc_boom(l, plan)
        return l.pasos
    edad_oscura(l)
    if nombre == "scouts":
        l.paso(21, "Aldeanos 18-21 a madera (2do campamento si el bosque queda lejos).", (13, 8, 0, 0))
        l.avanzar("Feudal", f"POP 22: clic en Feudal ({subida(l, 'cuartel durante el avance')}). Pasá 2 de ovejas a madera para las granjas.", (11, 10, 0, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: 2 establos (o establo + herrería). Exploradores sin parar. Hacha de doble filo y Collera." + l.nota("feudal"), (11, 10, 0, 0), hito=True)
        l.paso(l.v + 6, "Aldeanos nuevos a granjas y madera; algo de oro para la herrería." + l.nota("granjas"), (15, 10, 2, 0))
        fin(l, plan, (17, 12, 5, 0), l.v + 4)
    elif nombre == "arqueros":
        l.paso(20, "Aldeanos 18-20 a madera.", (13, 7, 0, 0))
        l.paso(22, "Aldeanos 21-22 a oro con campamento minero." + l.nota("oro"), (13, 7, 2, 0))
        l.avanzar("Feudal", f"POP 23: clic en Feudal ({subida(l, 'cuartel durante el avance')}). Pasá 2 de comida a madera.", (11, 9, 2, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: 2 galerías de tiro con arco, arqueros sin parar. Emplumado de flechas y Hacha de doble filo." + l.nota("feudal"), (11, 9, 2, 0), hito=True)
        l.paso(l.v + 8, "Aldeanos nuevos: oro hasta 8-10, el resto a madera y granjas. Hostigadores si el rival también va a arqueros." + l.nota("granjas"), (12, 10, 8, 0))
        fin(l, plan, (14, 11, 9, 0), l.v + 4)
    elif nombre == "maa":
        l.paso(19, "Aldeanos 18-19 a madera; uno construye el cuartel.", (13, 6, 0, 0))
        l.paso(21, "Aldeanos 20-21 a oro. Entrená 3 milicias apenas tengas el oro.", (13, 6, 2, 0))
        l.avanzar("Feudal", f"Clic en Feudal ({subida(l, 'cuartel + molino ya cuentan')}). Pasá 2 de comida a madera.", (11, 8, 2, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: investigá Hombres de armas y atacá. Construí 1-2 galerías y pasá a arqueros." + l.nota("feudal"), (11, 8, 2, 0), hito=True)
        l.paso(l.v + 7, "Aldeanos nuevos: oro hasta ~6, granjas y madera. Hacha de doble filo." + l.nota("granjas"), (13, 9, 6, 0))
        fin(l, plan, (15, 10, 7, 0), l.v + 4)
    elif nombre == "fc":
        l.paso(21, "Aldeanos 18-21 a madera.", (13, 8, 0, 0))
        l.paso(23, "Aldeanos 22-23 a comida (ovejas que queden o primeras granjas)." + l.nota("granjas"), (15, 8, 0, 0))
        l.paso(26, "Aldeanos 24-26 a oro." + l.nota("oro"), (15, 8, 3, 0))
        l.avanzar("Feudal", f"POP 27: clic en Feudal ({subida(l, 'herrería o mercado durante el avance')}). 2 aldeanos más a oro.", (14, 7, 5, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: 2do edificio feudal (mercado/herrería). Hacha de doble filo." + l.nota("feudal"), (14, 7, 5, 0), hito=True)
        fin(l, plan, (14, 8, 6, 0), l.v + 2)
    return l.pasos


def apertura_fc_boom(l, plan):
    """Fast Castle + Boom, según la guía paso a paso de NelsonSKA (resumida con palabras propias)."""
    factor = l.mods.get("factor_edad", 1.0)
    if l.ini == 6:
        ini = "Los 6 aldeanos iniciales: 2 construyen casas, 4 a ovejas."
    elif l.ini == 4:
        ini = "Los 4 aldeanos iniciales: 2 construyen casas, 2 a ovejas. Aldeanos nuevos a ovejas."
    else:
        ini = casas(l, "2 casas con los aldeanos iniciales; ") + "aldeanos 1-6 a ovejas bajo el CU."
    l.paso(6, ini + " El CU produce aldeanos sin parar durante toda la partida (regla de oro)." + l.nota("inicio"), (6, 0, 0, 0))
    l.paso(10, "El aldeano 7 construye un campamento maderero; 7-10 a madera (4 leñadores)." + l.nota("madera"), (6, 4, 0, 0))
    l.paso(11, "El aldeano 11 atrae el 1er jabalí al CU." + l.nota("caza"), (7, 4, 0, 0))
    casa = "El 13" if l.mods.get("sin_casas") else "El 12 hace una casa cerca de las bayas y el 13"
    l.paso(16, f"Aldeanos 12-16 a bayas (5 en total). {casa} construye el molino. "
           "Antes de que se acabe el 1er jabalí, un aldeano de comida atrae el 2do." + l.nota("comida"), (12, 4, 0, 0))
    l.paso(18, "Aldeanos 17-18 al jabalí. Quedan 9 cazadores, 5 en bayas y 4 leñadores.", (14, 4, 0, 0))
    l.paso(18, "Antes de que se termine el jabalí, 2 cazadores construyen 2 granjas junto al CU "
           "para aprovechar mejor las ovejas que quedan." + l.nota("granjas"), (14, 4, 0, 0))
    casa2 = "El 20" if l.mods.get("sin_casas") else "El 19 hace una casa junto a otro bosque y el 20"
    l.paso(23, f"{casa2} construye un 2do campamento maderero. Aldeanos 19-23 a madera: "
           "9 leñadores (4 + 5).", (14, 9, 0, 0))
    l.paso(26, "El 24 construye un campamento minero; 24-26 a oro." + l.nota("oro"), (14, 9, 3, 0))
    l.telar()
    l.avanzar("Feudal", "POP 27 (26 aldeanos + explorador): Telar y clic en Feudal (en Arena el Telar puede esperar). "
              "Encolá SOLO 2 aldeanos y poné el punto de reunión en la madera.", (14, 9, 3, 0))
    l.durante("No investigues nada (ni economía ni militar) hasta asegurar Castillos. Revisá aldeanos ociosos y, "
              "cuando se acaben las ovejas, hacé granjas. Guardá 325 de madera. Unos segundos antes de llegar, "
              "separá 3 leñadores.", (14, 9, 3, 0))
    req = ("no necesitás Mercado ni Herrería para avanzar: clic en Castillos apenas tengas 800 comida y 200 oro"
           if l.mods.get("sin_requisitos") else
           "2 de los leñadores separados construyen un Mercado y el 3ro una Herrería")
    l.paso(l.v, f"LLEGADA A FEUDAL: {req}. Los 2 aldeanos encolados van a madera." + l.nota("feudal"),
           (14, 11, 3, 0), hito=True)
    l.t += 2 * ALDEANO / l.vel
    l.v += 2
    l.pasos.append(dict(aldeanos=l.v, texto="Clic en Castillos apenas puedas. Mientras subís: elegí dónde van los 2 CU nuevos "
                        "(también te defienden), juntá 550 de madera y, si sobra, Hacha de doble filo y Collera. "
                        "Cuando se acaben las bayas, esos aldeanos a madera. ¡No te olvides de las casas!",
                        comida=14, madera=11, oro=3, piedra=0, tiempo="clic ~" + mmss(l.t), fase="Feudal", hito=True))
    l.t += CASTILLOS * factor
    l.v += l.mods.get("aldeanos_por_edad", 0)
    l.pasos.append(dict(aldeanos=l.v, texto="LLEGADA A CASTILLOS: 4 leñadores de cada campamento construyen un CU cada grupo. "
                        "Los 3 CU producen aldeanos sin parar con el punto de reunión en la madera; cada vez que alcance "
                        "la madera, pasá un leñador a una granja nueva. Necesitás 18+ granjeros." + l.nota("boom"),
                        comida=14, madera=11, oro=3, piedra=0, tiempo="~" + mmss(l.t), fase="Castillos", hito=True))
    l.pasos.append(dict(aldeanos=0, texto="BOOM LISTO cuando los 3 CU producen sin parar. Según la partida: seguí hasta ~100 "
                        "aldeanos (un 4to CU con piedra juntada o comprada en el mercado), usá lo que sobre para ejército, "
                        "o juntá piedra para un castillo con tu unidad única. " + plan["cas"],
                        comida=0, madera=0, oro=0, piedra=0, tiempo=None, fase="Castillos", hito=True))
    l.pasos.append(dict(aldeanos=0, texto="IMPERIAL (con ~100 aldeanos). " + plan["imp"],
                        comida=0, madera=0, oro=0, piedra=0, tiempo=None, fase="Imperial", hito=True))


# ---------------------------------------------------------------------------
# Parseo del texto del techtree
# ---------------------------------------------------------------------------

def limpiar(h):
    h = re.sub(r"<br>\s*", "\n", h).replace("<b>", "").replace("</b>", "")
    return [x.strip() for x in h.split("\n") if x.strip()]


def parsear(help_text):
    lineas = limpiar(help_text)
    enfoque = lineas[0].replace("Civilización de ", "").replace("Civilización ", "").strip()
    enfoque = enfoque[0].upper() + enfoque[1:]
    sec, bonos, unidades, techs, equipo = "bonos", [], [], [], []
    for ln in lineas[1:]:
        cab = ln.lstrip("• ").strip()
        low = cab.lower()
        es_titulo = low.rstrip().endswith(":")
        if not es_titulo:
            pass
        elif low.startswith("unidad"):
            sec = "unidades"
            continue
        elif low.startswith("tecnolog") or low.startswith("técnicas"):
            sec = "techs"
            continue
        elif low.startswith("bonificación"):
            sec = "equipo"
            continue
        destino = {"bonos": bonos, "unidades": unidades, "techs": techs, "equipo": equipo}[sec]
        if ln.startswith("•"):
            destino.append(cab)
        elif destino and sec in ("bonos", "techs"):
            destino[-1] += " " + cab
        else:
            destino.append(cab)
    uu = []
    for u in unidades:
        for parte in re.split(r"(?<=\))\s*(?:,|\by\b)\s*", u):
            parte = parte.strip(" ,")
            if parte:
                uu.append(parte[0].upper() + parte[1:])
    tt = []
    for i, t in enumerate(techs):
        edad = "Castillos" if i == 0 else "Imperial"
        m = re.match(r"^(.*?)\s*\((.*)\)\s*\.?$", t)
        tt.append(f"{m.group(1)} ({edad}): {m.group(2)}" if m else f"{t} ({edad})")
    return enfoque, [re.sub(r"\s+", " ", b) for b in bonos], uu, tt, " ".join(equipo)


# ---------------------------------------------------------------------------
# Mejoras por paso: "qué investigar/entrenar" + "dónde". Los nombres son los
# oficiales en español (del techtree) y se filtran según lo que tenga la civ.
# Cada casillero es una lista de alternativas: se usa la primera disponible.
# ---------------------------------------------------------------------------

def U(que, donde, interno):
    return ("Unit", que, donde, interno)


def T(que, donde, interno):
    return ("Tech", que, donde, interno)


def B(que, donde):
    return (None, que, donde, None)


ALDEANOS = B("Aldeanos sin parar", "Centro urbano")
CAMP_MAD = B("Campamento maderero", "construir en el bosque")
CAMP_MIN = B("Campamento minero", "construir en el oro")
MOLINO = B("Molino", "construir en las bayas")
TELAR = T("Telar", "Centro urbano", "Loom")
HACHA = T("Hacha de doble filo", "Campamento maderero", "Double Bit Axe")
COLLERA = T("Collera", "Molino", "Horse collar")
CARRETILLA = T("Carretilla", "Centro urbano", "Wheel Barrow")
ARADO = T("Arado pesado", "Molino", "Heavy plow")
SIERRA = T("Sierra de arco", "Campamento maderero", "Bow Saw")
MINERIA = T("Minería aurífera", "Campamento minero", "Gold Mining")
EMPLUMADO = T("Emplumado de flechas", "Herrería", "Fletching")
PUNZON = T("Flecha de punzón", "Herrería", "Bodkin Arrow")
FORJA = T("Forja", "Herrería", "Forging")
ALTO_HORNO = T("Alto horno", "Herrería", "Blast Furnace")
EDAD_F = B("Edad Feudal", "Centro urbano")
EDAD_C = B("Edad de los Castillos", "Centro urbano")
GRANJAS = B("Granjas", "alrededor del molino y el CU")
CUARTEL = B("Cuarteles", "construir durante el avance")
EDIF_FEUDAL = B("Herrería o Mercado", "edificio feudal")
CU_EXTRA = B("2-3 Centros urbanos", "275 madera + 100 piedra c/u")
EXPLORADOR = [U("Caballería de exploración", "Establo", "SCOUT"),
              U("Explorador a camello", "Establo", "CAMELSC"),
              U("Explorador águila", "Cuarteles", "EAGLE")]
ARQUERO = U("Arquero", "Galería de tiro con arco", "ARCHR")
HOSTIGADOR = U("Hostigador", "Galería de tiro con arco", "XBOWM")
LANCERO = U("Lancero", "Cuarteles", "PKEMN")
MILICIA = U("Milicia", "Cuarteles", "SPRMN")
HOMBRE_ARMAS = U("Hombre de armas", "Cuarteles", "SWDMN")
CABALLERO = [U("Caballero", "Establo", "KNGHT"), U("Explorador águila", "Cuarteles", "EAGLE")]
BALLESTERO = U("Ballestero", "Galería de tiro con arco", "CARCH")
ESPADA_LARGA = U("Soldado con espada larga", "Cuarteles", "THSWD")
PIQUERO = U("Piquero", "Cuarteles", "ISPKM")
PALADIN = [U("Paladín", "Establo", "PALDN"), U("Caballero", "Establo", "KNGHT"),
           U("Explorador águila", "Cuarteles", "EAGLE")]
ALABARDERO = U("Alabardero", "Cuarteles", "HLBDM")
ARBALESTERO = U("Arbalestero", "Galería de tiro con arco", "ACOAR")
HOST_ELITE = U("Hostigador de élite", "Galería de tiro con arco", "HXBOW")
CAMPEON = U("Campeón", "Cuarteles", "HEROI")

# Marcadores que se reemplazan por lo propio de cada civ
UU, UT1, UT2 = "UU", "UT1", "UT2"

OSCURA = [[ALDEANOS], [CAMP_MAD], [TELAR], [MOLINO], []]
MEJORAS = {
    "scouts": OSCURA + [
        [], [EDAD_F, CUARTEL], [EXPLORADOR, FORJA, HACHA, COLLERA], [GRANJAS, LANCERO, CARRETILLA],
        [EDAD_C], [CABALLERO, PIQUERO, UU, UT1, ARADO, SIERRA], [PALADIN, ALABARDERO, UT2, ALTO_HORNO]],
    "arqueros": OSCURA + [
        [], [CAMP_MIN], [EDAD_F, CUARTEL], [ARQUERO, EMPLUMADO, HACHA], [HOSTIGADOR, MINERIA, COLLERA],
        [EDAD_C], [BALLESTERO, PUNZON, UU, UT1, ARADO], [ARBALESTERO, HOST_ELITE, UT2]],
    "maa": OSCURA + [
        [B("Cuarteles", "construir con un leñador")], [CAMP_MIN, MILICIA], [EDAD_F],
        [HOMBRE_ARMAS, ARQUERO, EMPLUMADO], [HACHA, COLLERA, MINERIA],
        [EDAD_C], [ESPADA_LARGA, BALLESTERO, UU, UT1, ARADO], [CAMPEON, ARBALESTERO, UT2]],
    "fc": OSCURA + [
        [], [GRANJAS], [CAMP_MIN], [EDAD_F, EDIF_FEUDAL], [EDIF_FEUDAL, HACHA],
        [EDAD_C, COLLERA], [CU_EXTRA, CABALLERO, UU, UT1, ARADO, CARRETILLA], [PALADIN, ARBALESTERO, UT2]],
    "fc_boom": [
        [ALDEANOS, B("2 casas", "al empezar")], [CAMP_MAD], [B("Atraer jabalí", "al Centro urbano")],
        [MOLINO, B("Casa", "cerca de las bayas")], [B("Atraer 2do jabalí", "antes de que se acabe el 1ro")],
        [B("2 granjas", "junto al Centro urbano")],
        [B("Casa", "junto al otro bosque"), B("2do campamento maderero", "en ese bosque")], [CAMP_MIN],
        [TELAR, EDAD_F, B("Encolar solo 2 aldeanos", "punto de reunión en madera")],
        [B("Granjas", "cuando se acaben las ovejas"), B("Guardar 325 de madera", "Herrería 150 + Mercado 175")],
        [B("Mercado", "2 leñadores"), B("Herrería", "1 leñador")],
        [EDAD_C, B("Juntar 550 de madera", "2 CU de 275"), HACHA, COLLERA],
        [B("2 Centros urbanos", "4 leñadores cada uno"), B("Granjas", "1 leñador por granja nueva"), CARRETILLA, ARADO, SIERRA],
        [B("~100 aldeanos", "4to CU si sobra piedra"), UU, UT1, BALLESTERO, CABALLERO],
        [PALADIN, ARBALESTERO, UT2]],
}


def sin_parentesis(s):
    return re.sub(r"\s*\(.*$", "", s).strip()


def resolver_mejoras(apertura_id, pasos, civ_data, ids, uu, tt, mods=None):
    mods = mods or {}
    omitir = set()
    if mods.get("sin_casas"):
        omitir |= {"2 casas", "Casa"}
    if mods.get("sin_requisitos"):
        omitir |= {"Mercado", "Herrería", "Herrería o Mercado"}
    filas = MEJORAS[apertura_id]
    assert len(filas) == len(pasos), (apertura_id, len(filas), len(pasos))

    def disponible(item):
        cat, _, _, interno = item
        if cat is None:
            return True
        i = ids[cat].get(interno)
        return i is not None and int(i) in civ_data[cat]

    for paso, fila in zip(pasos, filas):
        mej = []
        for casillero in fila:
            if casillero == UU:
                if uu:
                    mej.append(dict(que=sin_parentesis(uu[0]), donde="Castillo"))
                continue
            if casillero in (UT1, UT2):
                k = 0 if casillero == UT1 else 1
                if len(tt) > k:
                    mej.append(dict(que=re.sub(r"\s*\((Castillos|Imperial)\).*$", "", tt[k]), donde="Castillo"))
                continue
            opciones = casillero if isinstance(casillero, list) else [casillero]
            for op in opciones:
                if op[1] in omitir:
                    break
                if disponible(op):
                    mej.append(dict(que=op[1], donde=op[2]))
                    break
        paso["mejoras"] = mej


# ---------------------------------------------------------------------------
# Counters de unidades únicas: tipo según el techtree + comportamiento base
# (con ajustes para las unidades únicas conocidas).
# ---------------------------------------------------------------------------

TIPOS = {
    "infantería": ("Infantería", ["Arqueros", "Mangoneles/Onagros", "Artilleros manuales"],
                   ["Lanceros/Piqueros", "Hostigadores", "Edificios"]),
    "caballería": ("Caballería pesada", ["Lanceros/Piqueros", "Camellos", "Monjes"],
                   ["Arqueros", "Hostigadores", "Asedio"]),
    "arquero": ("Arqueros a pie", ["Hostigadores", "Caballeros", "Mangoneles"],
                ["Infantería", "Lanceros"]),
    "arquero montado": ("Arqueros a caballo", ["Hostigadores", "Camellos", "Caballería pesada"],
                        ["Infantería", "Lanceros", "Unidades lentas"]),
    "guerrillero": ("Hostigadores", ["Infantería", "Caballería"],
                    ["Arqueros", "Arqueros a caballo"]),
    "asedio": ("Asedio", ["Caballería", "Infantería cuerpo a cuerpo"],
               ["Edificios", "Unidades agrupadas"]),
    "pólvora": ("Unidades de pólvora", ["Mangoneles/Onagros", "Hostigadores de élite", "Caballería ligera"],
                ["Infantería", "Lanceros", "Caballería pesada"]),
    "barco": ("Barco de guerra (agua)", ["Brulotes", "Galeones con catapulta", "Barcos de demolición"],
              ["Galeras", "Barcos pesqueros", "Edificios costeros"]),
    "monje": ("Monjes", ["Caballería ligera", "Exploradores", "Explorador águila"],
              ["Unidades caras (caballeros, elefantes)"]),
    "héroe": ("Héroe (unidad única de campaña de los Tres Reinos)", ["Monjes", "Unidades de counter de su tipo"],
              ["Unidades comunes"]),
    "camello": ("Camellos", ["Lanceros/Piqueros", "Infantería", "Arqueros"],
                ["Caballería", "Caballeros"]),
    "elefante": ("Elefantes", ["Monjes", "Alabarderos", "Camellos en masa"],
                 ["Unidades cuerpo a cuerpo", "Edificios"]),
}

# Ajustes conocidos: nombre (en minúsculas, comienzo) -> (tipo, débil contra, fuerte contra)
AJUSTES = {
    "huscarle": ("infantería", ["Caballería", "Campeones", "Artilleros manuales"], ["Arqueros", "Edificios", "Hostigadores"]),
    "kamayuk": ("infantería", ["Arqueros", "Infantería pesada"], ["Caballería", "Elefantes", "Camellos"]),
    "mameluco": ("camello", ["Arqueros", "Infantería", "Hostigadores"], ["Caballería", "Elefantes"]),
    "guerrero jaguar": ("infantería", ["Arqueros", "Caballería"], ["Infantería"]),
    "samurái": ("infantería", ["Arqueros", "Caballería"], ["Unidades únicas", "Infantería"]),
    "caballero de la orden": ("infantería", ["Arqueros", "Mangoneles", "Artilleros manuales"], ["Unidades cuerpo a cuerpo"]),
    "catafracta": ("caballería", ["Arqueros", "Monjes", "Camellos"], ["Infantería", "Lanceros/Piqueros"]),
    "leitis": ("caballería", ["Lanceros/Piqueros", "Camellos", "Monjes"], ["Unidades blindadas (caballeros, infantería pesada)"]),
    "tarcano": ("caballería", ["Lanceros/Piqueros", "Camellos"], ["Edificios", "Arqueros"]),
    "ballestero genovés": ("arquero", ["Hostigadores", "Infantería", "Mangoneles"], ["Caballería"]),
    "mangudai": ("arquero montado", ["Hostigadores", "Camellos"], ["Asedio", "Infantería"]),
    "ghulam": ("infantería", ["Caballería", "Infantería pesada"], ["Arqueros", "Lanceros"]),
    "jinete celta": ("infantería", ["Arqueros", "Caballería"], ["Arqueros", "Asedio"]),
    "lanzador de hachas": ("infantería", ["Caballería", "Arqueros"], ["Infantería"]),
    "arquero en camello": ("arquero montado", ["Hostigadores", "Infantería"], ["Arqueros a caballo", "Caballería"]),
    "guardiana gbeto": ("infantería", ["Arqueros", "Caballería ligera"], ["Infantería"]),
    "jinete de shrivamsha": ("caballería", ["Lanceros/Piqueros", "Infantería"], ["Arqueros", "Arqueros a caballo"]),
    "arambai": ("arquero montado", ["Hostigadores", "Caballería"], ["Unidades agrupadas", "Infantería"]),
    "elefante con balista": ("elefante", ["Monjes", "Caballería ligera", "Mangoneles"], ["Infantería agrupada", "Arqueros"]),
    "recluta con karambit": ("infantería", ["Arqueros", "Mangoneles"], ["Infantería en masa"]),
    "carreta de guerra husita": ("asedio", ["Infantería cuerpo a cuerpo", "Caballería"], ["Arqueros", "Unidades a distancia"]),
    "conquistador": ("pólvora", ["Hostigadores", "Lanceros/Piqueros", "Camellos"], ["Infantería", "Arqueros"]),
    "jenízaro": ("pólvora", ["Mangoneles/Onagros", "Hostigadores de élite"], ["Infantería", "Caballería pesada"]),
    "chu ko nu": ("arquero", ["Hostigadores", "Mangoneles", "Caballería"], ["Infantería", "Unidades poco blindadas"]),
    "arquero con arco largo": ("arquero", ["Hostigadores", "Caballería", "Mangoneles"], ["Infantería", "Lanceros"]),
    "arquero emplumado": ("arquero", ["Hostigadores", "Mangoneles", "Caballería"], ["Infantería", "Lanceros"]),
    "elefante de guerra": ("elefante", ["Monjes", "Alabarderos", "Camellos"], ["Cuerpo a cuerpo", "Edificios"]),
    "misionero": ("monje", ["Caballería ligera", "Arqueros"], ["Unidades caras"]),
}


def clasificar(desc):
    d = desc.lower()
    if "héroe" in d:
        return "héroe"
    if "monje" in d:
        return "monje"
    if "barco" in d:
        return "barco"
    if "asedio" in d:
        return "asedio"
    if "pólvora" in d or "artillero" in d:
        return "pólvora"
    if "guerrillero" in d:
        return "guerrillero"
    if "arquero montado" in d or "arquero a caballo" in d or "a distancia" in d:
        return "arquero montado"
    if "arquero" in d:
        return "arquero"
    if "caballería" in d:
        return "caballería"
    return "infantería"


def detalle_unidades(uu):
    salida = []
    for u in uu:
        nombre = sin_parentesis(u)
        m = re.search(r"\((.*)\)", u)
        desc = m.group(1) if m else ""
        low = nombre.lower()
        tipo = clasificar(desc)
        if "camello" in low:
            tipo = "camello"
        if "elefante" in low:
            tipo = "elefante"
        debil, fuerte = TIPOS[tipo][1], TIPOS[tipo][2]
        for clave, (t, d, f) in AJUSTES.items():
            if low.startswith(clave):
                tipo, debil, fuerte = t, d, f
                break
        salida.append(dict(nombre=nombre, clase=desc, como=TIPOS[tipo][0], debil=debil, fuerte=fuerte,
                           ajustado=any(low.startswith(k) for k in AJUSTES)))
    return salida


def main(data_path, strings_path, salida):
    data = json.load(open(data_path, encoding="utf-8"))
    strings = json.load(open(strings_path, encoding="utf-8"))
    ids = {cat: {t["internal_name"]: k for k, t in data["data"][cat].items()} for cat in ("Unit", "Tech")}
    civs = []
    for clave, c in data["civs"].items():
        plan = PLAN.get(clave)
        if plan is None:
            print(f"AVISO: {clave} no tiene plan, se omite", file=sys.stderr)
            continue
        nombre = strings[str(c["name_string_id"])]
        enfoque, bonos, uu, tt, equipo = parsear(strings[str(c["help_string_id"])])
        lineas = []
        for ap in (plan["ap"], plan["alt"], "fc_boom"):
            n, tipo, desc = NOMBRES_APERTURA[ap]
            pasos = apertura(ap, Linea(clave, plan), plan)
            resolver_mejoras(ap, pasos, c, ids, uu, tt, plan.get("mods"))
            linea = dict(id=ap, nombre=n, tipo=tipo, descripcion=desc, pasos=pasos)
            if ap == "fc_boom":
                linea["fuente"] = "https://www.youtube.com/watch?v=7LYPt1NFpbw"
                linea["recomendada"] = clave in RECOMENDADAS_BOOM
            lineas.append(linea)
        civs.append(dict(nombre=nombre, clave=clave, enfoque=enfoque, dificultad=plan["dif"],
                         unidades_unicas=uu, tecnologias_unicas=tt, bonos=bonos,
                         unidades_detalle=detalle_unidades(uu),
                         bono_equipo=equipo, castillos=plan["cas"], imperial=plan["imp"],
                         lineas=lineas))
    civs.sort(key=lambda x: x["nombre"])
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(civs, f, ensure_ascii=False, indent=1)
    print(f"{len(civs)} civilizaciones escritas en {salida}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
