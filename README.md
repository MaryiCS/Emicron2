# Tablero EMICRON y análisis de regresión

Aplicación web estática para explorar archivos CSV y libros Excel de EMICRON y ajustar modelos de regresión lineal simple o múltiple en el navegador. Los datos se procesan localmente y no se envían a un servidor.

## Uso

1. Abre `index.html` en un navegador con conexión a internet.
2. Arrastra un archivo `.csv`, `.xls`, `.xlsx` o `.xlsb` a la zona de carga o selecciónalo desde el equipo. En libros con varias hojas, las hojas índice o portada sin tablas se omiten y se abre la primera hoja utilizable; puedes cambiar de hoja con el selector. El tablero reconoce los archivos CSV del repositorio, como `datos_emicron.csv`, `emicron_2024_economico.csv` y `emicron_2024_frecuencias.csv`.
3. En **Análisis de regresión lineal**, selecciona la variable objetivo (Y), una o más variables explicativas (X) y el porcentaje de prueba.
   - En el selector de X, usa `Ctrl` (Windows/Linux) o `⌘` (macOS) para seleccionar varias columnas.
4. Pulsa **Ajustar modelo** para ver métricas, gráficos y la ecuación estimada.
5. Completa el formulario de predicción con valores nuevos y pulsa **Calcular predicción**.

La regresión admite objetivos numéricos. Los predictores numéricos se centran y escalan durante el ajuste; los categóricos se convierten en variables indicadoras y usan la primera categoría en orden alfabético como referencia. La ecuación presentada se expresa de nuevo en las unidades originales de los predictores.

## Resultados

- **R² de prueba:** proporción de variabilidad explicada en las observaciones reservadas para evaluación. Puede ser negativo si el modelo predice peor que usar el promedio.
- **R² ajustado de prueba:** ajusta el R² por la cantidad de coeficientes; aparece como no disponible cuando la muestra de prueba no permite calcularlo.
- **MAE y RMSE:** errores absolutos y cuadráticos medios, expresados en las unidades de Y.
- **Observado frente a predicho:** compara los resultados con la línea de referencia perfecta.
- **Residuos:** muestra la diferencia entre valor observado y predicho.

La partición de entrenamiento y prueba es reproducible. La evaluación corresponde a una sola partición, no a validación cruzada. El aplicativo avisa sobre muestras pequeñas y no ajusta el modelo cuando detecta redundancia exacta entre predictores.

## Archivos y dependencias

- `index.html`: interfaz, tablero descriptivo y regresión.
- Papa Parse: lectura de archivos CSV.
- SheetJS: lectura de libros Excel y selección de hoja.
- Plotly.js: gráficos interactivos.

Las bibliotecas se cargan desde CDN; se requiere conexión a internet al abrir el aplicativo. En Excel, el sistema busca automáticamente la fila de encabezados entre las primeras 60 filas de cada hoja y omite las hojas sin encabezados o registros tabulares. Si no identifica bien los encabezados, guarda o exporta esa hoja como CSV y cárgala de nuevo.

## Alcance y precauciones

- Se requieren al menos ocho filas completas para formar los conjuntos de entrenamiento y prueba. Los valores ausentes o no numéricos en las columnas seleccionadas se excluyen.
- Las columnas categóricas con más de 40 categorías no se ofrecen como predictor.
- Una regresión describe asociaciones en los datos; no demuestra causalidad.
- Algunos archivos de EMICRON son resúmenes agregados con pocas filas, por ejemplo `emicron_2024_economico.csv`. Sus métricas pueden ser inestables y no equivalen a un análisis de microdatos. Interpreta esos modelos con cautela.

