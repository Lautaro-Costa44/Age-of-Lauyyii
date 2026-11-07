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
        notas=dict(feudal="Bono armenio: Espadachín de espada larga y Piquero ya se investigan en Feudal.")),
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
        notas=dict(madera="Doble hacha ya está disponible en la Edad Oscura y cuesta 40 % menos de comida.")),
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
}


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


class Linea:
    """Arma pasos llevando la cuenta de aldeanos, reparto y tiempo."""

    def __init__(self, civ, plan):
        self.mods = plan.get("mods", {})
        self.notas = plan.get("notas", {})
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
    edad_oscura(l)
    if nombre == "scouts":
        l.paso(21, "Aldeanos 18-21 a madera (2do campamento si el bosque queda lejos).", (13, 8, 0, 0))
        l.avanzar("Feudal", f"POP 22: clic en Feudal ({subida(l, 'cuartel durante el avance')}). Pasá 2 de ovejas a madera para las granjas.", (11, 10, 0, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: 2 establos (o establo + herrería). Exploradores sin parar. Doble hacha y Collar de caballo." + l.nota("feudal"), (11, 10, 0, 0), hito=True)
        l.paso(l.v + 6, "Aldeanos nuevos a granjas y madera; algo de oro para Linaje o la herrería." + l.nota("granjas"), (15, 10, 2, 0))
        fin(l, plan, (17, 12, 5, 0), l.v + 4)
    elif nombre == "arqueros":
        l.paso(20, "Aldeanos 18-20 a madera.", (13, 7, 0, 0))
        l.paso(22, "Aldeanos 21-22 a oro con campamento minero." + l.nota("oro"), (13, 7, 2, 0))
        l.avanzar("Feudal", f"POP 23: clic en Feudal ({subida(l, 'cuartel durante el avance')}). Pasá 2 de comida a madera.", (11, 9, 2, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: 2 galerías de tiro con arco, arqueros sin parar. Emplumado y Doble hacha." + l.nota("feudal"), (11, 9, 2, 0), hito=True)
        l.paso(l.v + 8, "Aldeanos nuevos: oro hasta 8-10, el resto a madera y granjas. Hostigadores si el rival también va a arqueros." + l.nota("granjas"), (12, 10, 8, 0))
        fin(l, plan, (14, 11, 9, 0), l.v + 4)
    elif nombre == "maa":
        l.paso(19, "Aldeanos 18-19 a madera; uno construye el cuartel.", (13, 6, 0, 0))
        l.paso(21, "Aldeanos 20-21 a oro. Entrená 3 milicias apenas tengas el oro.", (13, 6, 2, 0))
        l.avanzar("Feudal", f"Clic en Feudal ({subida(l, 'cuartel + molino ya cuentan')}). Pasá 2 de comida a madera.", (11, 8, 2, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: investigá Hombres de armas y atacá. Construí 1-2 galerías y pasá a arqueros." + l.nota("feudal"), (11, 8, 2, 0), hito=True)
        l.paso(l.v + 7, "Aldeanos nuevos: oro hasta ~6, granjas y madera. Doble hacha." + l.nota("granjas"), (13, 9, 6, 0))
        fin(l, plan, (15, 10, 7, 0), l.v + 4)
    elif nombre == "fc":
        l.paso(21, "Aldeanos 18-21 a madera.", (13, 8, 0, 0))
        l.paso(23, "Aldeanos 22-23 a comida (ovejas que queden o primeras granjas)." + l.nota("granjas"), (15, 8, 0, 0))
        l.paso(26, "Aldeanos 24-26 a oro." + l.nota("oro"), (15, 8, 3, 0))
        l.avanzar("Feudal", f"POP 27: clic en Feudal ({subida(l, 'herrería o mercado durante el avance')}). 2 aldeanos más a oro.", (14, 7, 5, 0))
        l.paso(l.v, "LLEGADA A FEUDAL: 2do edificio feudal (mercado/herrería). Doble hacha." + l.nota("feudal"), (14, 7, 5, 0), hito=True)
        fin(l, plan, (14, 8, 6, 0), l.v + 2)
    return l.pasos


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
        if low.startswith("unidad"):
            sec = "unidades"
            continue
        if low.startswith("tecnolog") or low.startswith("técnicas"):
            sec = "techs"
            continue
        if low.startswith("bonificación"):
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


def main(data_path, strings_path, salida):
    data = json.load(open(data_path, encoding="utf-8"))
    strings = json.load(open(strings_path, encoding="utf-8"))
    civs = []
    for clave, c in data["civs"].items():
        plan = PLAN.get(clave)
        if plan is None:
            print(f"AVISO: {clave} no tiene plan, se omite", file=sys.stderr)
            continue
        nombre = strings[str(c["name_string_id"])]
        enfoque, bonos, uu, tt, equipo = parsear(strings[str(c["help_string_id"])])
        lineas = []
        for ap in (plan["ap"], plan["alt"]):
            n, tipo, desc = NOMBRES_APERTURA[ap]
            pasos = apertura(ap, Linea(clave, plan), plan)
            lineas.append(dict(id=ap, nombre=n, tipo=tipo, descripcion=desc, pasos=pasos))
        civs.append(dict(nombre=nombre, clave=clave, enfoque=enfoque, dificultad=plan["dif"],
                         unidades_unicas=uu, tecnologias_unicas=tt, bonos=bonos,
                         bono_equipo=equipo, castillos=plan["cas"], imperial=plan["imp"],
                         lineas=lineas))
    civs.sort(key=lambda x: x["nombre"])
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(civs, f, ensure_ascii=False, indent=1)
    print(f"{len(civs)} civilizaciones escritas en {salida}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
