from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

import numpy as np
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
EXTENSIONES = {".csv", ".xls", ".xlsx", ".xlsb"}
SEMILLA = 20261012

st.set_page_config(page_title="Regresión EMICRON", page_icon="📈", layout="wide")
st.title("Análisis de regresión lineal · EMICRON")
st.write(
    "Explora datos EMICRON, ajusta una regresión simple o múltiple, revisa su desempeño "
    "y calcula predicciones. Los archivos cargados se procesan durante la sesión."
)


def numero(valor):
    """Convierte formatos numéricos comunes en Colombia y Estados Unidos."""
    if pd.isna(valor):
        return np.nan
    if isinstance(valor, (int, float, np.number)) and not isinstance(valor, bool):
        return float(valor)
    texto = str(valor).strip().replace("\u00a0", "").replace(" ", "")
    texto = texto.removeprefix("$").removesuffix("%")
    if not texto:
        return np.nan
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", texto):
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", texto):
        texto = texto.replace(",", "")
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return np.nan


def convertir_columna(columna: pd.Series) -> pd.Series:
    return columna.map(numero)


def fila_encabezado_excel(contenido: bytes, hoja: str) -> int:
    muestra = pd.read_excel(BytesIO(contenido), sheet_name=hoja, header=None, nrows=60)
    mejor_fila, mejor_puntaje = -1, 0
    for indice, fila in muestra.iterrows():
        celdas = [str(v).strip() for v in fila.tolist() if pd.notna(v) and str(v).strip()]
        textos = sum(pd.isna(numero(v)) for v in celdas)
        puntaje = textos * 2 + min(len(celdas), 12) * 0.25
        if len(celdas) >= 2 and puntaje > mejor_puntaje:
            mejor_fila, mejor_puntaje = int(indice), puntaje
    return mejor_fila


def leer_archivo(nombre: str, contenido: bytes, hoja: str | None = None) -> pd.DataFrame:
    extension = Path(nombre).suffix.lower()
    if extension == ".csv":
        try:
            return pd.read_csv(BytesIO(contenido), sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(contenido), sep=None, engine="python", encoding="latin-1")
    if extension in {".xls", ".xlsx", ".xlsb"}:
        engine = {".xls": "xlrd", ".xlsx": "openpyxl", ".xlsb": "pyxlsb"}[extension]
        if hoja is None:
            libro = pd.ExcelFile(BytesIO(contenido), engine=engine)
            hoja = libro.sheet_names[0]
        fila = fila_encabezado_excel(contenido, hoja)
        if fila < 0:
            raise ValueError(f'No se encontró una tabla con encabezados en la hoja "{hoja}".')
        df = pd.read_excel(BytesIO(contenido), sheet_name=hoja, header=fila, engine=engine)
        df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    raise ValueError("Formato no compatible. Usa CSV, XLS, XLSX o XLSB.")


def archivos_repositorio() -> list[Path]:
    return sorted(
        (p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES),
        key=lambda p: p.name.lower(),
    )


archivos = archivos_repositorio()
fuente = st.radio("Fuente de datos", ["Archivo del repositorio", "Subir archivo"], horizontal=True)
contenido: bytes | None = None
nombre_archivo: str | None = None
hoja_excel: str | None = None

if fuente == "Archivo del repositorio":
    if not archivos:
        st.info("No hay archivos CSV o Excel en la raíz del repositorio. Elige **Subir archivo**.")
        st.stop()
    nombres = [p.name for p in archivos]
    predeterminado = nombres.index("datos_emicron.csv") if "datos_emicron.csv" in nombres else 0
    nombre_archivo = st.selectbox("Selecciona un archivo del repositorio", nombres, index=predeterminado)
    ruta = ROOT / nombre_archivo
    contenido = ruta.read_bytes()
else:
    archivo_cargado = st.file_uploader(
        "Carga un CSV o libro Excel", type=["csv", "xls", "xlsx", "xlsb"]
    )
    if archivo_cargado is None:
        st.stop()
    nombre_archivo = archivo_cargado.name
    contenido = archivo_cargado.getvalue()

assert contenido is not None and nombre_archivo is not None

if Path(nombre_archivo).suffix.lower() in {".xls", ".xlsx", ".xlsb"}:
    engine = {".xls": "xlrd", ".xlsx": "openpyxl", ".xlsb": "pyxlsb"}[Path(nombre_archivo).suffix.lower()]
    try:
        libro = pd.ExcelFile(BytesIO(contenido), engine=engine)
        hojas_validas = []
        for nombre in libro.sheet_names:
            if fila_encabezado_excel(contenido, nombre) >= 0:
                hojas_validas.append(nombre)
        if not hojas_validas:
            st.error("No encontré hojas con una tabla y una fila de encabezados en las primeras 60 filas.")
            st.stop()
        hoja_excel = st.selectbox("Hoja de datos", hojas_validas)
        if len(hojas_validas) < len(libro.sheet_names):
            st.caption("Se omitieron hojas índice o portada sin tablas reconocibles.")
    except Exception as exc:
        st.error(f"No pude abrir el libro Excel: {exc}")
        st.stop()

try:
    datos = leer_archivo(nombre_archivo, contenido, hoja_excel)
except Exception as exc:
    st.error(f"No pude leer el archivo: {exc}")
    st.stop()

datos = datos.loc[:, ~datos.columns.astype(str).str.match(r"^Unnamed")]
datos.columns = [str(c).strip() for c in datos.columns]
datos = datos.dropna(how="all")
if datos.empty or len(datos.columns) < 2:
    st.error("El archivo debe tener al menos dos columnas y una fila de datos.")
    st.stop()

st.caption(f"Archivo: **{nombre_archivo}**" + (f" · Hoja: **{hoja_excel}**" if hoja_excel else ""))
with st.expander(f"Vista previa · {len(datos):,} filas × {len(datos.columns)} columnas", expanded=False):
    st.dataframe(datos.head(20), use_container_width=True)

numericas: dict[str, pd.Series] = {}
categoricas: list[str] = []
for col in datos.columns:
    valores = convertir_columna(datos[col])
    no_vacios = datos[col].notna().sum()
    proporcion_numerica = valores.notna().sum() / no_vacios if no_vacios else 0
    if proporcion_numerica >= 0.9:
        numericas[col] = valores
    elif datos[col].nunique(dropna=True) <= 40:
        categoricas.append(col)

if not numericas:
    st.error("No identifiqué columnas numéricas que puedan usarse como variable objetivo.")
    st.stop()

st.subheader("Configura el modelo")
col_y, col_x, col_test = st.columns([1, 2, 1])
objetivo_sugerido = next(
    (c for c in ["ventas_mes", "ventas_promedio_mes_millones", "ventas_anual_miles"] if c in numericas),
    list(numericas)[0],
)
with col_y:
    objetivo = st.selectbox("Variable objetivo (Y)", list(numericas), index=list(numericas).index(objetivo_sugerido))
opciones_x = [c for c in datos.columns if c != objetivo and (c in numericas or c in categoricas)]
sugeridos = [c for c in ["meses_antiguedad", "personal_ocupado_promedio", "usa_internet", "sector"] if c in opciones_x]
with col_x:
    predictores = st.multiselect("Variables explicativas (X)", opciones_x, default=sugeridos[:3])
with col_test:
    porcentaje_prueba = st.selectbox("Datos para prueba", [0.2, 0.25, 0.3], format_func=lambda x: f"{x:.0%}")

if st.button("Ajustar modelo", type="primary", use_container_width=False):
    if not predictores:
        st.session_state.pop("modelo_regresion", None)
        st.error("Selecciona al menos una variable explicativa.")
    else:
        marco = pd.DataFrame(index=datos.index)
        marco[objetivo] = numericas[objetivo]
        for col in predictores:
            if col in numericas:
                marco[col] = numericas[col]
            else:
                marco[col] = datos[col].astype("string").str.strip()
        marco = marco.dropna(subset=[objetivo, *predictores]).reset_index(drop=True)
        if len(marco) < 8:
            st.error(f"Solo hay {len(marco)} filas completas; se requieren al menos 8.")
        else:
            codificadas = pd.get_dummies(marco[predictores], columns=[c for c in predictores if c not in numericas], drop_first=True, dtype=float)
            n = len(marco)
            rng = np.random.default_rng(SEMILLA)
            indices = rng.permutation(n)
            n_prueba = max(2, int(round(n * porcentaje_prueba)))
            idx_prueba, idx_entrenamiento = indices[:n_prueba], indices[n_prueba:]
            medias, escalas = {}, {}
            for col in [c for c in predictores if c in numericas]:
                medias[col] = float(codificadas.iloc[idx_entrenamiento][col].mean())
                escala = float(codificadas.iloc[idx_entrenamiento][col].std(ddof=0))
                escalas[col] = escala if escala > 0 else 1.0
                codificadas[col] = (codificadas[col] - medias[col]) / escalas[col]
            X = codificadas.to_numpy(dtype=float)
            y = marco[objetivo].to_numpy(dtype=float)
            if len(idx_entrenamiento) <= X.shape[1] + 1:
                st.error("Hay muy pocas filas de entrenamiento para la cantidad de coeficientes. Reduce predictores o usa más datos.")
            else:
                matriz_train = np.column_stack([np.ones(len(idx_entrenamiento)), X[idx_entrenamiento]])
                matriz_test = np.column_stack([np.ones(len(idx_prueba)), X[idx_prueba]])
                beta, _, rango, _ = np.linalg.lstsq(matriz_train, y[idx_entrenamiento], rcond=None)
                if rango < matriz_train.shape[1]:
                    st.error("El modelo tiene predictores redundantes o categorías sin variación en entrenamiento. Cambia los predictores.")
                else:
                    pred = matriz_test @ beta
                    obs = y[idx_prueba]
                    residuos = obs - pred
                    sse = float(np.sum(residuos**2))
                    sst = float(np.sum((obs - np.mean(obs)) ** 2))
                    r2 = 1 - sse / sst if sst > 0 else np.nan
                    k = X.shape[1]
                    r2_ajustado = 1 - (1 - r2) * (len(obs) - 1) / (len(obs) - k - 1) if len(obs) > k + 1 and np.isfinite(r2) else np.nan
                    modelo = {
                        "objetivo": objetivo,
                        "predictores": predictores,
                        "features": list(codificadas.columns),
                        "categoricas": [c for c in predictores if c not in numericas],
                        "medias": medias,
                        "escalas": escalas,
                        "beta": beta,
                        "obs": obs,
                        "pred": pred,
                        "residuos": residuos,
                        "metricas": (r2, r2_ajustado, float(np.mean(np.abs(residuos))), float(np.sqrt(np.mean(residuos**2)))),
                        "filas": len(marco),
                        "entrenamiento": len(idx_entrenamiento),
                        "prueba": len(idx_prueba),
                        "niveles": {c: sorted(marco[c].astype(str).unique().tolist()) for c in predictores if c in [c for c in predictores if c not in numericas]},
                        "numericas": [c for c in predictores if c in numericas],
                    }
                    st.session_state["modelo_regresion"] = modelo
                    st.session_state["selector_actual"] = (objetivo, tuple(predictores), porcentaje_prueba, nombre_archivo, hoja_excel)

modelo = st.session_state.get("modelo_regresion")
config_actual = (objetivo, tuple(predictores), porcentaje_prueba, nombre_archivo, hoja_excel)
if modelo and st.session_state.get("selector_actual") == config_actual:
    st.subheader("Desempeño del modelo")
    r2, r2_ajustado, mae, rmse = modelo["metricas"]
    kpi = st.columns(4)
    kpi[0].metric("R² de prueba", f"{r2:.3f}" if np.isfinite(r2) else "N/D")
    kpi[1].metric("R² ajustado de prueba", f"{r2_ajustado:.3f}" if np.isfinite(r2_ajustado) else "N/D")
    kpi[2].metric("MAE", f"{mae:,.3f}", help="Error absoluto medio, en las unidades de Y")
    kpi[3].metric("RMSE", f"{rmse:,.3f}", help="Raíz del error cuadrático medio, en las unidades de Y")
    st.caption(f"Ajustado con {modelo['entrenamiento']:,} filas y evaluado con {modelo['prueba']:,} filas. Semilla reproducible: {SEMILLA}.")
    if modelo["filas"] < 30:
        st.warning("La muestra tiene menos de 30 filas completas; interpreta las métricas con cautela.")

    st.markdown("#### Coeficientes")
    nombres_coef = ["Intercepto", *modelo["features"]]
    tabla_coef = pd.DataFrame({"Término": nombres_coef, "Coeficiente": modelo["beta"]})
    st.dataframe(tabla_coef, hide_index=True, use_container_width=True)
    st.caption("Los coeficientes de predictores numéricos corresponden a variables estandarizadas (media 0 y desviación estándar 1).")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### Observado frente a predicho")
        grafico_obs = pd.DataFrame({"Predicho": modelo["pred"], "Observado": modelo["obs"]})
        st.scatter_chart(grafico_obs, x="Predicho", y="Observado", height=390)
    with col_g2:
        st.markdown("#### Residuos")
        grafico_residuos = pd.DataFrame({"Predicho": modelo["pred"], "Residuo": modelo["residuos"]})
        st.scatter_chart(grafico_residuos, x="Predicho", y="Residuo", height=390)

    st.subheader("Predecir nuevos valores")
    with st.form("formulario_prediccion"):
        columnas = st.columns(min(3, len(modelo["predictores"])))
        valores_nuevos = {}
        for i, col in enumerate(modelo["predictores"]):
            with columnas[i % len(columnas)]:
                if col in modelo["numericas"]:
                    valores_nuevos[col] = st.number_input(col, value=float(modelo["medias"][col]), format="%.6f", key=f"pred_{col}")
                else:
                    niveles = modelo["niveles"][col]
                    valores_nuevos[col] = st.selectbox(col, niveles, key=f"pred_{col}")
        enviar = st.form_submit_button("Calcular predicción", type="primary")
    if enviar:
        fila = pd.DataFrame([valores_nuevos], columns=modelo["predictores"])
        for col in modelo["categoricas"]:
            fila[col] = pd.Categorical(fila[col].astype(str), categories=modelo["niveles"][col])
        codificada = pd.get_dummies(fila, columns=modelo["categoricas"], drop_first=True, dtype=float)
        codificada = codificada.reindex(columns=modelo["features"], fill_value=0)
        for col in modelo["numericas"]:
            codificada[col] = (pd.to_numeric(codificada[col]) - modelo["medias"][col]) / modelo["escalas"][col]
        estimacion = float(np.r_[1.0, codificada.to_numpy(dtype=float).ravel()] @ modelo["beta"])
        st.success(f"Predicción estimada de **{modelo['objetivo']}**: **{estimacion:,.4f}**")
elif modelo:
    st.info("Cambiaste la configuración. Ajusta nuevamente el modelo para actualizar los resultados.")

st.divider()
st.caption("La regresión describe asociaciones en los datos; no demuestra causalidad. Los datos de resumen con pocas filas pueden producir métricas inestables.")
