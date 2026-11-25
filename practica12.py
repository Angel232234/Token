"""
Práctica 12 – Tu API
Herramientas de Visualización · Unidad II
Universidad Politécnica de Querétaro

API elegida: NASA Near Earth Object Web Service (NeoWs)
Endpoint: https://api.nasa.gov/neo/rest/v1/feed
Token: se lee desde token.txt (nunca escrito aquí)
"""

import os
import sys
import json
import pathlib
import requests
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import date, timedelta

# ─── Paleta del curso ──────────────────────────────────────────────────────────
GRIS    = "#B9C3D1"
AZUL    = "#1C4C9A"
CMAP_Q  = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]

# ─── Rutas ─────────────────────────────────────────────────────────────────────
DIR         = pathlib.Path(__file__).parent
TOKEN_FILE  = DIR / "token.txt"
JSON_FILE   = DIR / "respuesta.json"
FIG_DIR     = DIR / "graficas"
FIG_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# 1. LEER Y VALIDAR EL TOKEN
# ══════════════════════════════════════════════════════════════════════════════
def leer_token() -> str:
    """Lee el token desde token.txt y aborta si está vacío o ausente."""
    if not TOKEN_FILE.exists():
        print(f"[ERROR] No se encontró el archivo de token: {TOKEN_FILE}")
        print("  Crea el archivo token.txt y pega tu llave de api.nasa.gov")
        sys.exit(1)

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        print("[ERROR] El archivo token.txt existe pero está vacío.")
        print("  Pega tu llave de NASA API en token.txt y vuelve a ejecutar.")
        sys.exit(1)

    # DEMO_KEY es la clave pública de NASA con límite de 30 req/hora
    if len(token) < 8:
        print(f"[ERROR] El token parece incompleto (sólo {len(token)} caracteres).")
        sys.exit(1)
    if token == "DEMO_KEY":
        print("[AVISO] Usando DEMO_KEY (30 req/hora). Reemplaza por tu llave personal.")


    print(f"[OK] Token leído correctamente ({len(token)} caracteres).")
    return token


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONSULTAR LA API  (o reutilizar respuesta guardada)
# ══════════════════════════════════════════════════════════════════════════════
def _hacer_peticion(url: str, params: dict) -> dict:
    """
    Hace una petición GET, valida código de estado y tipo de contenido,
    y devuelve el JSON.
    """
    respuesta = requests.get(url, params=params, timeout=30)

    if respuesta.status_code == 401:
        print("[ERROR 401] Token inválido o expirado. Revisa token.txt.")
        sys.exit(1)
    elif respuesta.status_code == 400:
        print("[ERROR 400] Petición mal formada. Revisa los parámetros.")
        sys.exit(1)
    elif respuesta.status_code == 429:
        print("[ERROR 429] Límite de peticiones alcanzado. Espera un momento.")
        sys.exit(1)
    elif respuesta.status_code != 200:
        print(f"[ERROR {respuesta.status_code}] Respuesta inesperada del servidor.")
        sys.exit(1)

    content_type = respuesta.headers.get("Content-Type") or ""
    if "json" not in content_type:
        print("[ERROR] La respuesta no es JSON. Primeros 300 caracteres:")
        print(respuesta.text[:300])
        sys.exit(1)

    return respuesta.json()


def consultar_api(token: str) -> dict:
    """
    Consulta NeoWs en bloques de 7 días (máximo permitido) hasta acumular
    al menos 200 registros. Si ya existe respuesta.json, lo reutiliza.
    """
    if JSON_FILE.exists():
        print(f"[INFO] Reutilizando respuesta guardada en {JSON_FILE.name}")
        with open(JSON_FILE, encoding="utf-8") as f:
            return json.load(f)

    url = "https://api.nasa.gov/neo/rest/v1/feed"
    # Recolectamos varios bloques de 7 días (6 bloques ≈ 42 días ≈ 250+ NEOs)
    # Con DEMO_KEY la NASA puede limitar a 30 req/hora; si falla, reduce a 4 bloques.
    bloques = 6
    todos_los_neo: dict = {}

    for i in range(bloques):
        fin    = date.today() - timedelta(days=1 + i * 7)
        inicio = fin - timedelta(days=6)
        params = {
            "start_date": inicio.isoformat(),
            "end_date":   fin.isoformat(),
            "api_key":    token,
        }
        print(f"[INFO] Bloque {i+1}/{bloques}: {inicio} → {fin} ...")
        datos = _hacer_peticion(url, params)
        todos_los_neo.update(datos.get("near_earth_objects", {}))

    resultado = {"near_earth_objects": todos_los_neo}

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"[OK] Respuesta guardada en {JSON_FILE.name}")

    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# 3. LIMPIAR Y DOCUMENTAR LOS DATOS
# ══════════════════════════════════════════════════════════════════════════════
def limpiar_datos(raw: dict) -> pd.DataFrame:
    """
    Aplana la estructura anidada de NeoWs y construye un DataFrame limpio.
    Imprime tipos, faltantes y registros utilizables.
    """
    registros = []
    for fecha, lista in raw["near_earth_objects"].items():
        for neo in lista:
            km_min = neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"]
            km_max = neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
            vel    = float(
                neo["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"]
            ) if neo["close_approach_data"] else None
            dist   = float(
                neo["close_approach_data"][0]["miss_distance"]["kilometers"]
            ) if neo["close_approach_data"] else None

            registros.append({
                "fecha":          fecha,
                "nombre":         neo["name"],
                "diametro_min_km": km_min,
                "diametro_max_km": km_max,
                "diametro_med_km": (km_min + km_max) / 2,
                "velocidad_kmh":  vel,
                "distancia_km":   dist,
                "peligroso":      neo["is_potentially_hazardous_asteroid"],
            })

    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha"])

    print("\n─── Tipos de dato al cargar ───────────────────────────────")
    print(df.dtypes.to_string())

    print("\n─── Valores faltantes por columna ─────────────────────────")
    print(df.isnull().sum().to_string())

    filas_antes = len(df)
    df = df.dropna(subset=["velocidad_kmh", "distancia_km"])
    filas_despues = len(df)
    perdidos = filas_antes - filas_despues

    if perdidos:
        print(f"\n[INFO] Se eliminaron {perdidos} registros sin datos de acercamiento.")

    # Convertir columnas numéricas (ya son float, pero lo forzamos)
    for col in ["diametro_min_km", "diametro_max_km", "diametro_med_km",
                "velocidad_kmh", "distancia_km"]:
        antes = df[col].isnull().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        despues = df[col].isnull().sum()
        if despues > antes:
            print(f"[WARN] {col}: {despues - antes} valores no convertibles a número.")

    print(f"\n[OK] Registros utilizables: {len(df)}")
    print("─" * 55)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 4. GRÁFICAS
# ══════════════════════════════════════════════════════════════════════════════
matplotlib.rcParams["axes.spines.top"]   = False
matplotlib.rcParams["axes.spines.right"] = False
matplotlib.rcParams["font.family"]       = "sans-serif"


def guardar(fig: plt.Figure, nombre: str) -> None:
    ruta = FIG_DIR / nombre
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    print(f"[OK] Gráfica guardada: {ruta}")
    plt.close(fig)


# ── Gráfica 1 · DISTRIBUCIÓN ──────────────────────────────────────────────────
def grafica_distribucion(df: pd.DataFrame) -> None:
    """
    Pregunta: ¿Cómo se distribuyen los tamaños de los asteroides que se
              acercaron esta semana? ¿Hay casos extremadamente grandes?
    """
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.hist(df["diametro_med_km"], bins=25, color=AZUL, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Diámetro estimado (km)", labelpad=8)
    ax.set_ylabel("Número de asteroides", labelpad=8)
    ax.set_title(
        "La mayoría de los asteroides que nos rozaron esta semana\n"
        "miden menos de 0.5 km — pero algunos superan 2 km",
        fontsize=11, fontweight="bold", pad=12
    )

    # Anotar la barra del máximo
    maximo = df["diametro_med_km"].max()
    ax.axvline(maximo, color="#E69F00", linewidth=1.5, linestyle="--",
               label=f"Máximo: {maximo:.2f} km")
    ax.legend(frameon=False, fontsize=9)

    guardar(fig, "g1_distribucion_diametros.png")


# ── Gráfica 2 · COMPARACIÓN ───────────────────────────────────────────────────
def grafica_comparacion(df: pd.DataFrame) -> None:
    """
    Pregunta: ¿Los asteroides potencialmente peligrosos se mueven más rápido
              que los que no representan peligro?
    """
    grupos = df.groupby("peligroso")["velocidad_kmh"].median().reset_index()
    grupos["etiqueta"] = grupos["peligroso"].map(
        {True: "Potencialmente\npeligroso", False: "No peligroso"}
    )
    colores = [GRIS, AZUL]

    fig, ax = plt.subplots(figsize=(6, 4))
    barras = ax.bar(grupos["etiqueta"], grupos["velocidad_kmh"],
                    color=colores, width=0.5, edgecolor="white")

    for barra, val in zip(barras, grupos["velocidad_kmh"]):
        ax.text(barra.get_x() + barra.get_width() / 2,
                val + 500, f"{val:,.0f}", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Velocidad mediana (km/h)", labelpad=8)
    ax.set_title(
        "Los asteroides peligrosos viajan más rápido:\n"
        "su velocidad mediana supera a la de los no peligrosos",
        fontsize=11, fontweight="bold", pad=12
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f}k"))
    ax.set_ylim(0, grupos["velocidad_kmh"].max() * 1.25)

    guardar(fig, "g2_comparacion_velocidad.png")


# ── Gráfica 3 · RELACIÓN ──────────────────────────────────────────────────────
def grafica_relacion(df: pd.DataFrame) -> None:
    """
    Pregunta: ¿Los asteroides más grandes pasan más cerca de la Tierra,
              o el tamaño y la distancia son independientes?
    """
    colores_puntos = df["peligroso"].map({True: AZUL, False: GRIS})

    fig, ax = plt.subplots(figsize=(8, 5))
    scatter = ax.scatter(
        df["diametro_med_km"], df["distancia_km"] / 1e6,
        c=colores_puntos, alpha=0.75, s=40, edgecolors="none"
    )

    # Leyenda manual
    from matplotlib.lines import Line2D
    leyenda = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=AZUL,
               markersize=8, label="Potencialmente peligroso"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GRIS,
               markersize=8, label="No peligroso"),
    ]
    ax.legend(handles=leyenda, frameon=False, fontsize=9)

    ax.set_xlabel("Diámetro estimado (km)", labelpad=8)
    ax.set_ylabel("Distancia de acercamiento (millones de km)", labelpad=8)
    ax.set_title(
        "Tamaño y distancia no van de la mano:\n"
        "asteroides grandes pueden acercarse tanto como los pequeños",
        fontsize=11, fontweight="bold", pad=12
    )

    guardar(fig, "g3_relacion_diametro_distancia.png")


# ── Gráfica 4 · EVOLUCIÓN ─────────────────────────────────────────────────────
def grafica_evolucion(df: pd.DataFrame) -> None:
    """
    Pregunta: ¿Cómo varió la cantidad de asteroides detectados por día y cuál
              fue el día más activo de la semana?
    """
    por_dia = df.groupby("fecha").size().reset_index(name="cantidad")
    colores_dia = [AZUL if c == por_dia["cantidad"].max() else GRIS
                   for c in por_dia["cantidad"]]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(por_dia["fecha"].dt.strftime("%d %b"),
           por_dia["cantidad"], color=colores_dia, edgecolor="white")

    for i, (_, row) in enumerate(por_dia.iterrows()):
        ax.text(i, row["cantidad"] + 0.2, str(int(row["cantidad"])),
                ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Fecha", labelpad=8)
    ax.set_ylabel("Número de asteroides detectados", labelpad=8)
    ax.set_title(
        "El tráfico de asteroides varía cada día:\n"
        "el día con más detecciones se destaca en azul",
        fontsize=11, fontweight="bold", pad=12
    )
    ax.set_ylim(0, por_dia["cantidad"].max() * 1.25)

    guardar(fig, "g4_evolucion_por_dia.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  Práctica 12 – NASA Near Earth Objects (NeoWs)")
    print("=" * 55)

    token = leer_token()
    raw   = consultar_api(token)
    df    = limpiar_datos(raw)

    print("\n─── Generando gráficas ────────────────────────────────────")
    grafica_distribucion(df)
    grafica_comparacion(df)
    grafica_relacion(df)
    grafica_evolucion(df)

    print("\n[LISTO] Todas las gráficas se guardaron en la carpeta 'graficas/'")


if __name__ == "__main__":
    main()
