"""
dashboard.py — Práctica 12 · Dashboard interactivo
Universidad Politécnica de Querétaro
API: NASA Near Earth Object Web Service (NeoWs)
Token: se lee desde token.txt (nunca escrito aquí)

Ejecutar con:
    streamlit run dashboard.py
"""

import json
import pathlib
import sys
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta

# ─── Paleta del curso ──────────────────────────────────────────────────────────
GRIS  = "#B9C3D1"
AZUL  = "#1C4C9A"
CMAP  = ["#E69F00", "#56B4E9", "#009E73", "#0072B2"]

# ─── Rutas ─────────────────────────────────────────────────────────────────────
DIR        = pathlib.Path(__file__).parent
TOKEN_FILE = DIR / "token.txt"
JSON_FILE  = DIR / "respuesta.json"


# ══════════════════════════════════════════════════════════════════════════════
# Funciones de datos (reutilizadas de practica12.py)
# ══════════════════════════════════════════════════════════════════════════════
def leer_token() -> str:
    if not TOKEN_FILE.exists():
        st.error("❌ No se encontró `token.txt`. Crea el archivo con tu llave de api.nasa.gov.")
        st.stop()
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token or len(token) < 8:
        st.error("❌ El token en `token.txt` está vacío o incompleto.")
        st.stop()
    return token


def _hacer_peticion(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 401:
        st.error("❌ Token inválido (401). Revisa `token.txt`.")
        st.stop()
    elif r.status_code == 429:
        st.error("⏳ Límite de peticiones alcanzado (429). Espera un momento y recarga.")
        st.stop()
    elif r.status_code != 200:
        st.error(f"❌ Error HTTP {r.status_code} al consultar la API.")
        st.stop()
    ct = r.headers.get("Content-Type") or ""
    if "json" not in ct:
        st.error("❌ La respuesta no es JSON.")
        st.stop()
    return r.json()


@st.cache_data(show_spinner="Consultando NASA NeoWs…")
def cargar_datos_api(token: str, bloques: int = 6) -> dict:
    """Descarga datos de NeoWs o reutiliza respuesta.json cacheada."""
    if JSON_FILE.exists():
        with open(JSON_FILE, encoding="utf-8") as f:
            return json.load(f)

    url = "https://api.nasa.gov/neo/rest/v1/feed"
    todos: dict = {}
    for i in range(bloques):
        fin    = date.today() - timedelta(days=1 + i * 7)
        inicio = fin - timedelta(days=6)
        datos  = _hacer_peticion(url, {
            "start_date": inicio.isoformat(),
            "end_date":   fin.isoformat(),
            "api_key":    token,
        })
        todos.update(datos.get("near_earth_objects", {}))

    resultado = {"near_earth_objects": todos}
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    return resultado


def construir_df(raw: dict) -> pd.DataFrame:
    registros = []
    for fecha, lista in raw["near_earth_objects"].items():
        for neo in lista:
            km_min = neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"]
            km_max = neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
            vel  = float(neo["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"]) \
                   if neo["close_approach_data"] else None
            dist = float(neo["close_approach_data"][0]["miss_distance"]["kilometers"]) \
                   if neo["close_approach_data"] else None
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
    df = df.dropna(subset=["velocidad_kmh", "distancia_km"])
    for col in ["diametro_min_km", "diametro_max_km", "diametro_med_km",
                "velocidad_kmh", "distancia_km"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA PÁGINA
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="🚀 NASA NeoWs Dashboard",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS mínimo ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetric"] { background:#f0f4fa; border-radius:8px; padding:12px; }
    [data-testid="stMetricLabel"] { font-size:.85rem; color:#555; }
    h1 { color: #1C4C9A; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — CONTROLES
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://api.nasa.gov/assets/img/favicons/favicon-192.png", width=60)
    st.title("⚙️ Controles")

    solo_peligrosos = st.toggle("Mostrar solo asteroides peligrosos", value=False)

    st.divider()
    st.markdown("**Rango de fechas**")
    # Se llena después de cargar los datos
    fecha_placeholder = st.empty()

    st.divider()
    st.markdown("**Acerca de**")
    st.markdown(
        "Datos en tiempo real de la API "
        "[NASA NeoWs](https://api.nasa.gov). "
        "Token almacenado en `token.txt` — nunca en el código."
    )
    st.markdown("*Práctica 12 · Herramientas de Visualización*")


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════
token = leer_token()
raw   = cargar_datos_api(token)
df    = construir_df(raw)

# ── Filtro de fechas dinámico ──────────────────────────────────────────────────
fecha_min = df["fecha"].min().date()
fecha_max = df["fecha"].max().date()

with fecha_placeholder:
    rango = st.date_input(
        "Selecciona rango",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
    )

if isinstance(rango, (list, tuple)) and len(rango) == 2:
    f_ini, f_fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
else:
    f_ini, f_fin = pd.Timestamp(fecha_min), pd.Timestamp(fecha_max)

df_f = df[(df["fecha"] >= f_ini) & (df["fecha"] <= f_fin)]
if solo_peligrosos:
    df_f = df_f[df_f["peligroso"]]

# ══════════════════════════════════════════════════════════════════════════════
# ENCABEZADO
# ══════════════════════════════════════════════════════════════════════════════
st.title("☄️ NASA Near Earth Objects — Dashboard")
st.caption(
    f"Datos de **{fecha_min}** a **{fecha_max}** · "
    f"Mostrando **{len(df_f):,}** de {len(df):,} registros"
)

# ══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS RÁPIDAS
# ══════════════════════════════════════════════════════════════════════════════
c1, c2, c3, c4, c5 = st.columns(5)

n_peligrosos = df_f["peligroso"].sum()
pct_pel = n_peligrosos / len(df_f) * 100 if len(df_f) else 0

c1.metric("☄️ Asteroides",        f"{len(df_f):,}")
c2.metric("⚠️ Peligrosos",        f"{n_peligrosos}  ({pct_pel:.1f}%)")
c3.metric("📏 Diám. máx.",        f"{df_f['diametro_max_km'].max():.2f} km")
c4.metric("🚀 Veloc. máx.",       f"{df_f['velocidad_kmh'].max():,.0f} km/h")
c5.metric("🌍 Dist. mín. Tierra", f"{df_f['distancia_km'].min()/1e6:.2f} M km")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICAS — FILA 1
# ══════════════════════════════════════════════════════════════════════════════
col_a, col_b = st.columns(2)

# ── G1 · Distribución ─────────────────────────────────────────────────────────
with col_a:
    st.subheader("📊 Distribución de tamaños")
    st.caption("¿Cómo se reparten los diámetros? ¿Hay casos extremos?")

    fig1 = px.histogram(
        df_f, x="diametro_med_km", nbins=30,
        color_discrete_sequence=[AZUL],
        labels={"diametro_med_km": "Diámetro estimado (km)", "count": "Asteroides"},
        title="La mayoría mide < 0.5 km, pero algunos superan los 2 km",
    )
    fig1.update_traces(marker_line_color="white", marker_line_width=0.5)
    fig1.add_vline(
        x=df_f["diametro_med_km"].max(), line_dash="dash",
        line_color="#E69F00",
        annotation_text=f"Máx: {df_f['diametro_med_km'].max():.2f} km",
        annotation_position="top left",
    )
    fig1.update_layout(showlegend=False, plot_bgcolor="white",
                       paper_bgcolor="white", margin=dict(t=50, b=20))
    st.plotly_chart(fig1, use_container_width=True)

# ── G2 · Comparación ──────────────────────────────────────────────────────────
with col_b:
    st.subheader("📊 Comparación de velocidades")
    st.caption("¿Los peligrosos van más rápido?")

    grupos = df_f.groupby("peligroso")["velocidad_kmh"].median().reset_index()
    grupos["etiqueta"] = grupos["peligroso"].map(
        {True: "Potencialmente peligroso", False: "No peligroso"}
    )
    fig2 = px.bar(
        grupos, x="etiqueta", y="velocidad_kmh",
        color="etiqueta",
        color_discrete_map={
            "Potencialmente peligroso": AZUL,
            "No peligroso":             GRIS,
        },
        labels={"velocidad_kmh": "Velocidad mediana (km/h)", "etiqueta": ""},
        title="Los peligrosos tienen mayor velocidad mediana",
        text_auto=".0f",
    )
    fig2.update_layout(showlegend=False, plot_bgcolor="white",
                       paper_bgcolor="white", margin=dict(t=50, b=20))
    st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICAS — FILA 2
# ══════════════════════════════════════════════════════════════════════════════
col_c, col_d = st.columns(2)

# ── G3 · Relación ─────────────────────────────────────────────────────────────
with col_c:
    st.subheader("📊 Relación tamaño ↔ distancia")
    st.caption("¿Los más grandes pasan más cerca?")

    df_f2 = df_f.copy()
    df_f2["distancia_Mkm"] = df_f2["distancia_km"] / 1e6
    df_f2["peligro_label"] = df_f2["peligroso"].map(
        {True: "Potencialmente peligroso", False: "No peligroso"}
    )
    fig3 = px.scatter(
        df_f2, x="diametro_med_km", y="distancia_Mkm",
        color="peligro_label",
        color_discrete_map={
            "Potencialmente peligroso": AZUL,
            "No peligroso":             GRIS,
        },
        hover_name="nombre",
        hover_data={"velocidad_kmh": ":.0f", "peligro_label": False},
        labels={
            "diametro_med_km": "Diámetro estimado (km)",
            "distancia_Mkm":   "Distancia de acercamiento (M km)",
            "peligro_label":   "",
        },
        title="Tamaño y distancia no están correlacionados",
        opacity=0.75,
    )
    fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                       margin=dict(t=50, b=20),
                       legend=dict(orientation="h", yanchor="bottom",
                                   y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig3, use_container_width=True)

# ── G4 · Evolución ────────────────────────────────────────────────────────────
with col_d:
    st.subheader("📊 Evolución diaria de detecciones")
    st.caption("¿Cuántos asteroides por día?")

    por_dia = df_f.groupby(df_f["fecha"].dt.date).size().reset_index(name="cantidad")
    por_dia.columns = ["fecha", "cantidad"]
    max_dia = por_dia["cantidad"].max()
    por_dia["color"] = por_dia["cantidad"].apply(
        lambda x: "Día pico" if x == max_dia else "Otros días"
    )
    fig4 = px.bar(
        por_dia, x="fecha", y="cantidad",
        color="color",
        color_discrete_map={"Día pico": AZUL, "Otros días": GRIS},
        labels={"fecha": "Fecha", "cantidad": "Asteroides detectados", "color": ""},
        title="El tráfico varía cada día — el pico se destaca en azul",
        text_auto=True,
    )
    fig4.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                       margin=dict(t=50, b=20),
                       legend=dict(orientation="h", yanchor="bottom",
                                   y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABLA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋 Datos crudos (filtrados)")

cols_mostrar = ["fecha", "nombre", "diametro_med_km",
                "velocidad_kmh", "distancia_km", "peligroso"]
df_tabla = df_f[cols_mostrar].sort_values("fecha", ascending=False).copy()
df_tabla.columns = ["Fecha", "Nombre", "Diám. med. (km)",
                    "Veloc. (km/h)", "Distancia (km)", "Peligroso"]

st.dataframe(
    df_tabla.style.format({
        "Diám. med. (km)": "{:.4f}",
        "Veloc. (km/h)":   "{:,.0f}",
        "Distancia (km)":  "{:,.0f}",
    }).applymap(
        lambda v: "background-color: #ffeaea" if v is True else "",
        subset=["Peligroso"]
    ),
    use_container_width=True,
    height=300,
)

st.caption("🔴 Fila sombreada = asteroide potencialmente peligroso")
