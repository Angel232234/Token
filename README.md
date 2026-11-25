# NASA Near Earth Objects — Dashboard (Práctica 12)

Dashboard interactivo construido con **Streamlit** y **Plotly** que consume la API **NASA NeoWs** en tiempo real.

## 🚀 Cómo ejecutar

### 1. Clona el repositorio
```bash
git clone https://github.com/TU_USUARIO/practica12-nasa-neo.git
cd practica12-nasa-neo
```

### 2. Instala dependencias
```bash
pip install -r requirements.txt
```

### 3. Configura tu token
Crea un archivo `token.txt` en la raíz del proyecto con tu llave de [api.nasa.gov](https://api.nasa.gov):
```
TU_LLAVE_NASA_AQUI
```
> ⚠️ **Nunca** subas `token.txt` a GitHub. Ya está en `.gitignore`.

### 4. Lanza el dashboard
```bash
streamlit run dashboard.py
```

El navegador se abre automáticamente en `http://localhost:8501`.

---

## 📊 Visualizaciones

| Gráfica | Tipo | Pregunta |
|---------|------|----------|
| Distribución de tamaños | Histograma | ¿Cómo se reparten los diámetros? |
| Comparación de velocidades | Barras | ¿Los peligrosos van más rápido? |
| Relación tamaño ↔ distancia | Dispersión | ¿El tamaño determina qué tan cerca pasan? |
| Evolución diaria | Barras temporales | ¿Cuántos asteroides por día? |

---

## 🗂️ Estructura del proyecto

```
.
├── dashboard.py        # App Streamlit (dashboard interactivo)
├── practica12.py       # Script original con gráficas estáticas
├── requirements.txt    # Dependencias Python
├── respuesta.json      # Caché de la API (se genera automáticamente)
├── graficas/           # Imágenes PNG generadas por practica12.py
├── token.txt           # TU LLAVE — NO SE SUBE (está en .gitignore)
└── .gitignore
```

---

## 🔑 API utilizada

- **Nombre:** NASA Near Earth Object Web Service (NeoWs)
- **Documentación:** https://api.nasa.gov
- **Token:** Gratuito, instantáneo, sin tarjeta de crédito
- **Límite:** 1,000 req/hora con llave personal
- **Datos:** Asteroides y cometas que se acercan a la órbita terrestre

---

*Universidad Politécnica de Querétaro · Herramientas de Visualización · Unidad II*
