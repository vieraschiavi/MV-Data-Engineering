#!/usr/bin/env python3
# © 2026 Martín Viera. Todos los derechos reservados.
"""
MV Data Engineering · La voz de los dos videos, en los tres idiomas.

Mismo esquema que `daxlingo/media/narracion.py`, que ya está probado en este
monorepo:

  edge        Microsoft Edge TTS. SIN clave y sin costo, con voz neuronal
              ARGENTINA para el español (`es-AR-ElenaNeural`). Es el default.
  elevenlabs  Sólo si hay ELEVENLABS_API_KEY y alguien acepta pagarla.

Se fuerza uno con `MVDE_TTS=edge|elevenlabs`.

Por qué pre-renderizado y no síntesis en vivo
---------------------------------------------
La voz del navegador arranca con latencia y suena distinto en cada máquina.
Acá se sintetiza UNA vez y quedan los MP3 en `assets/video/audio/<idioma>/`.
El montaje los pega: no hay síntesis en tiempo de reproducción, no hay lag.

Cómo se evita el desfasaje
--------------------------
`build_video.py` NO usa una duración fija por placa: mide cada MP3 y le da a la
placa el largo de su locución más un respiro. La imagen dura lo que dura la
voz, por definición.

Hace falta salida a internet
----------------------------
Los dos motores son servicios. **En este entorno de desarrollo el proxy
devuelve 403 por política a `speech.platform.bing.com`**, así que la voz no se
genera acá: para eso está `.github/workflows/voz.yml`, que corre en un runner
de GitHub y sube los MP3 y los videos ya sonorizados. Es la misma solución que
usa `daxlingo`.

Uso:
    python assets/video/narracion.py              # edge, los 3 idiomas
    python assets/video/narracion.py --idioma es
    python assets/video/narracion.py --listar     # ver el guion, sin red
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

AUDIO = Path(__file__).resolve().parent / "audio"

# Voz por idioma. La de español es ARGENTINA a propósito: el guion está escrito
# en rioplatense y una voz «español neutro» le arruina el registro — el «vos»,
# el «tenés» y el «acá» dejan de sonar naturales en una boca que no los usa.
VOCES_EDGE = {
    "es": "es-AR-ElenaNeural",
    "en": "en-US-AndrewNeural",
    "pt": "pt-BR-AntonioNeural",
}
# Apenas más lento que el default: a -8% no se oye «pausado», se oye ARRASTRADO.
RITMO_EDGE = "-2%"

# Las cifras que el video CITA de la demo `cartera`, en un solo lugar.
#
# Acá había un problema de honestidad, no de formato. La locución decía
# «noventa y ocho coma nueve sobre cien, con las seis áreas por encima de
# nueve», y los dos números estaban mal, cada uno a su manera:
#
#   · 98,9 es el `total` de `salud.evaluar()`, y el motor dice POR ESCRITO, en
#     la nota que acompaña a cada corrida, que ese total «sirve para saber qué
#     falta configurar, no para presentarlo como métrica de calidad»: promedia
#     cuatro áreas medidas contra los datos con dos que sólo verifican que el
#     YAML esté completo. Vender en un video el número que el propio programa
#     desaconseja usar es el problema que el programa denuncia.
#   · «por encima de nueve» quedó de una época en que las áreas iban de 0 a 10.
#     Hoy van de 0 a 100 y la más baja de la demo da 96, así que la frase no
#     decía nada: todo está «por encima de nueve».
#
# Ahora el número vive en la PLACA, que se re-renderiza gratis, y la voz dice
# qué ES el número, que es lo que no cambia cuando cambia la fórmula. Si el
# puntaje volviera al guion hablado, cada cambio de fórmula obligaría a
# regrabar los tres MP3 — y mientras no se regraben, el video miente con voz
# propia.
#
# `tests/test_video.py` corre la demo `cartera` y falla si alguna de estas
# cifras dejó de ser la que devuelve el motor. Así, de una fórmula que se
# mueve se entera el CI y no el cliente en la mitad del video.
CIFRAS_CARTERA = {
    "medido": 98.3,          # salud.evaluar()["medido"]["puntaje"]
    "areas_medidas": 4,      # salud.evaluar()["medido"]["areas"]
    "declarados": 2,         # salud.evaluar()["completitud"]["declarados"]
    "posibles": 2,           # salud.evaluar()["completitud"]["posibles"]
}


def cifra(idioma: str, valor: float) -> str:
    """98.3 → «98,3» en español y portugués, «98.3» en inglés.

    La placa se arma con esto: un «98.3» en la versión española se lee como un
    error de la herramienta, no como un decimal.
    """
    txt = f"{valor:.1f}"
    return txt if idioma == "en" else txt.replace(".", ",")


# El guion HABLADO. No es el texto de la placa: en pantalla va un título corto
# y acá va la frase que se escucha. Las claves son las mismas que usa
# `build_video.py`, y un test verifica que no falte ninguna en ningún idioma.
GUION: dict[str, dict[str, str]] = {
    "es": {
        # ---------- video comercial (dos minutos, para vender) ----------
        "com_intro": "MV Data Engineering. Cualquier proyecto de datos, de la fuente al "
                     "reporte final, sin fallas silenciosas.",
        "com_problema": "El problema no es que el pipeline falle. Es que no falle: que corra "
                        "verde con un join que multiplicó filas o una fecha leída como número, "
                        "y que nadie se entere hasta que el gerente pregunta por qué el número "
                        "no cierra.",
        "com_gate": "Acá cada una de las doce etapas tiene un gate. La que falla corta las "
                    "siguientes, y cada una deja escrito qué hizo, sobre cuántas filas y con "
                    "qué resultado.",
        "com_salud": "Al final de cada corrida el motor se puntúa a sí mismo en seis áreas, y "
                     "te dice qué mejorar con un parche que se aplica al proyecto con un clic.",
        "com_local": "Corre en tu máquina. El almacén es un archivo en tu disco y las fuentes "
                     "se abren en sólo lectura: ningún dato sale de ahí.",
        "com_cierre": "Licencia perpetua. Probalo con la demo incluida y después apuntalo a "
                      "tu base.",
        # ---------- video demo end to end (el pipeline entero) ----------
        "demo_intro": "Vamos a correr un proyecto entero, de punta a punta, sobre una cartera "
                      "de cobranzas de treinta y seis meses.",
        "demo_yaml": "Todo el proyecto se declara en un archivo. Las fuentes, las reglas de "
                     "calidad, el modelo estrella y los KPIs. No se programa: se declara.",
        "demo_pipeline": "Doce etapas. Fuentes, bronze, silver, calidad, gold, almacén, "
                         "gobernanza, machine learning, reporte, DAX, Power BI y entrega.",
        "demo_calidad": "La etapa de calidad corre las reglas por dimensión. Si una crítica "
                        "falla, el pipeline se detiene ahí: no se sigue construyendo sobre "
                        "datos rotos.",
        "demo_proyeccion": "La proyección se elige con un backtest de origen móvil: se corta "
                           "la serie en el pasado, se entrena sólo con lo anterior al corte y "
                           "se mide contra lo que realmente pasó. Y se compara contra repetir "
                           "el mismo mes del año anterior: si ningún modelo le gana a eso, se "
                           "proyecta con eso y el informe lo dice.",
        "demo_banda": "La banda de desvío no es una fórmula: son los errores que ESE modelo "
                      "tuvo, paso por paso del horizonte. Por eso se puede planificar con ella.",
        "demo_salud": "Lo que el motor MIDE son las reglas de calidad que pasaron, el backtest "
                      "del modelo y la auditoría del archivo de Power BI. Qué tan completa está "
                      "la declaración se cuenta aparte: no se promedia con lo medido. Es una "
                      "autoevaluación y el informe lo dice con esas palabras. Y el mismo comando "
                      "sobre los mismos datos da siempre el mismo número.",
        "demo_cierre": "De la fuente al tablero de Power BI, con la evidencia de cada paso.",
    },
    "en": {
        "com_intro": "MV Data Engineering. Any data project, from source to final report, "
                     "with no silent failures.",
        "com_problema": "The problem isn't the pipeline failing. It's the pipeline NOT "
                        "failing: running green with a join that multiplied rows or a date "
                        "read as a number, and nobody noticing until the director asks why "
                        "the number doesn't add up.",
        "com_gate": "Here each of the twelve stages has a gate. A failing stage stops the "
                    "rest, and every one records what it did, over how many rows and with "
                    "what result.",
        "com_salud": "At the end of each run the engine scores itself across six areas and "
                     "tells you what to improve, with a patch you apply to the project in "
                     "one click.",
        "com_local": "It runs on your machine. The warehouse is a file on your disk and "
                     "sources are opened read-only: no data leaves it.",
        "com_cierre": "Perpetual licence. Try it with the bundled demo, then point it at "
                      "your own database.",
        "demo_intro": "We're going to run a whole project, end to end, over a thirty-six "
                      "month collections book.",
        "demo_yaml": "The entire project is declared in one file. Sources, quality rules, "
                     "the star schema and the KPIs. You don't program it: you declare it.",
        "demo_pipeline": "Twelve stages. Sources, bronze, silver, quality, gold, warehouse, "
                         "governance, machine learning, report, DAX, Power BI and delivery.",
        "demo_calidad": "The quality stage runs the rules per dimension. If a critical one "
                        "fails, the pipeline stops right there: nothing gets built on top of "
                        "broken data.",
        "demo_proyeccion": "The forecast is chosen with a rolling-origin backtest: the series "
                           "is cut in the past, the model trains only on what came before the "
                           "cut, and it's measured against what actually happened. And it's "
                           "compared against simply repeating the same month a year earlier: "
                           "if no model beats that, that's what forecasts, and the report "
                           "says so.",
        "demo_banda": "The deviation band isn't a formula: it's the errors THAT model made, "
                      "step by step across the horizon. That's why you can plan with it.",
        "demo_salud": "What the engine MEASURES is the quality rules that passed, the model "
                      "backtest and the audit of the Power BI file. How complete the declaration "
                      "is gets counted separately: it is never averaged into what was measured. "
                      "It is a self-assessment and the report says so in those words. And the "
                      "same command over the same data always returns the same number.",
        "demo_cierre": "From the source to the Power BI dashboard, with evidence for every step.",
    },
    "pt": {
        "com_intro": "MV Data Engineering. Qualquer projeto de dados, da fonte ao relatório "
                     "final, sem falhas silenciosas.",
        "com_problema": "O problema não é o pipeline falhar. É ele NÃO falhar: rodar verde com "
                        "um join que multiplicou linhas ou uma data lida como número, e "
                        "ninguém perceber até o diretor perguntar por que o número não fecha.",
        "com_gate": "Aqui cada uma das doze etapas tem um gate. A que falha interrompe as "
                    "seguintes, e cada uma deixa registrado o que fez, sobre quantas linhas e "
                    "com que resultado.",
        "com_salud": "No fim de cada execução o motor se pontua em seis áreas e diz o que "
                     "melhorar, com um patch que se aplica ao projeto com um clique.",
        "com_local": "Roda na sua máquina. O armazém é um arquivo no seu disco e as fontes "
                     "abrem-se somente leitura: nenhum dado sai dali.",
        "com_cierre": "Licença perpétua. Teste com a demo incluída e depois aponte-o para o "
                      "seu banco.",
        "demo_intro": "Vamos rodar um projeto inteiro, de ponta a ponta, sobre uma carteira "
                      "de cobrança de trinta e seis meses.",
        "demo_yaml": "Todo o projeto declara-se num arquivo. As fontes, as regras de "
                     "qualidade, o modelo estrela e os KPIs. Não se programa: declara-se.",
        "demo_pipeline": "Doze etapas. Fontes, bronze, silver, qualidade, gold, armazém, "
                         "governança, machine learning, relatório, DAX, Power BI e entrega.",
        "demo_calidad": "A etapa de qualidade roda as regras por dimensão. Se uma crítica "
                        "falha, o pipeline para ali: não se continua construindo sobre dados "
                        "quebrados.",
        "demo_proyeccion": "A projeção escolhe-se com um backtest de origem móvel: corta-se a "
                           "série no passado, treina-se só com o anterior ao corte e mede-se "
                           "contra o que realmente aconteceu. E compara-se com repetir o mesmo "
                           "mês do ano anterior: se nenhum modelo ganhar disso, projeta-se com "
                           "isso e o relatório diz.",
        "demo_banda": "A faixa de desvio não é uma fórmula: são os erros que AQUELE modelo "
                      "teve, passo a passo do horizonte. Por isso dá para planejar com ela.",
        "demo_salud": "O que o motor MEDE são as regras de qualidade que passaram, o backtest "
                      "do modelo e a auditoria do arquivo do Power BI. Quão completa está a "
                      "declaração conta-se à parte: não se mistura com o medido. É uma "
                      "autoavaliação e o relatório diz isso com essas palavras. E o mesmo "
                      "comando sobre os mesmos dados dá sempre o mesmo número.",
        "demo_cierre": "Da fonte ao painel do Power BI, com a evidência de cada passo.",
    },
}

IDIOMAS = tuple(GUION)
CLAVES = tuple(GUION["es"])


def faltantes() -> dict[str, list[str]]:
    """Claves que le faltan a algún idioma. Un video mudo en el medio de una
    escena es peor que uno sin voz: se nota y parece roto."""
    return {i: [k for k in CLAVES if not GUION[i].get(k)] for i in IDIOMAS
            if [k for k in CLAVES if not GUION[i].get(k)]}


async def _edge(texto: str, voz: str, destino: Path) -> None:
    import edge_tts
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    com = edge_tts.Communicate(texto, voz, rate=RITMO_EDGE, **({"proxy": proxy} if proxy else {}))
    await com.save(str(destino))


def generar(idioma: str, forzar: bool = False) -> list[Path]:
    carpeta = AUDIO / idioma
    carpeta.mkdir(parents=True, exist_ok=True)
    hechos = []
    for clave in CLAVES:
        destino = carpeta / f"{clave}.mp3"
        if destino.exists() and destino.stat().st_size > 0 and not forzar:
            hechos.append(destino)
            continue
        asyncio.run(_edge(GUION[idioma][clave], VOCES_EDGE[idioma], destino))
        if destino.stat().st_size == 0:
            # Un MP3 vacío es peor que ninguno: el montaje le daría duración
            # cero a la placa y la escena pasaría de largo.
            destino.unlink()
            raise RuntimeError(f"{idioma}/{clave}: el servicio devolvió audio vacío")
        hechos.append(destino)
        print(f"  {idioma}/{clave}.mp3  {destino.stat().st_size/1024:.0f} kB")
    return hechos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idioma", choices=IDIOMAS)
    ap.add_argument("--listar", action="store_true", help="mostrar el guion sin tocar la red")
    ap.add_argument("--forzar", action="store_true", help="regenerar aunque el MP3 ya exista")
    a = ap.parse_args()

    if (falta := faltantes()):
        print(f"guion incompleto: {falta}", file=sys.stderr)
        return 1
    if a.listar:
        for i in ([a.idioma] if a.idioma else IDIOMAS):
            print(f"\n=== {i} ({VOCES_EDGE[i]})")
            for k in CLAVES:
                print(f"  {k:18} {GUION[i][k][:96]}…")
        return 0

    for i in ([a.idioma] if a.idioma else IDIOMAS):
        print(f"=== {i} · {VOCES_EDGE[i]}")
        try:
            generar(i, a.forzar)
        except Exception as exc:  # noqa: BLE001 - el motivo se muestra tal cual
            print(f"  falló: {type(exc).__name__}: {exc}", file=sys.stderr)
            print("  (edge-tts necesita salida a internet; en un entorno con proxy cerrado "
                  "usar .github/workflows/voz.yml)", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
