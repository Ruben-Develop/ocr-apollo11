# Informe de la práctica: extracción de texto mediante OCR

## 1. Introducción

En esta práctica se convierte información no estructurada contenida en imágenes en un conjunto de datos estructurado. Para ello se utiliza OpenCV en el preprocesamiento y Tesseract OCR, a través de PyTesseract, para reconocer los caracteres.

El archivo entregado contiene 23 imágenes de varios tipos: cronogramas y tablas de Apollo 11, documentos fotografiados y capturas de pantalla. Se procesan todas para conservar el contenido disponible.

## 2. Objetivos

- Comprender cómo extraer texto de imágenes y almacenarlo en un formato estructurado.
- Aplicar operaciones de preprocesamiento con OpenCV.
- Utilizar PyTesseract para reconocer texto.
- Exportar las líneas reconocidas a CSV y TXT.
- Identificar las limitaciones del OCR y la necesidad de validar manualmente los resultados.

## 3. Herramientas

- Python 3.
- OpenCV (`opencv-python`).
- PyTesseract (`pytesseract`).
- Tesseract OCR, instalado como programa independiente.
- Pillow (`PIL`) para convertir la matriz procesada en una imagen compatible con el OCR.
- NumPy para operaciones con matrices.

## 4. Procedimiento realizado

1. Se descomprimieron las imágenes y se guardaron en `imagenes_originales/`.
2. OpenCV cargó cada imagen y, cuando fue necesario, se redujo su tamaño manteniendo la proporción.
3. Se detectó la orientación. Si el resultado de OSD no era suficientemente fiable, se probaron las cuatro rotaciones posibles sobre una miniatura y se seleccionó la opción con mejor puntuación OCR.
4. Para las imágenes generales se convirtió la imagen a escala de grises, se mejoró el contraste local con CLAHE, se redujo el ruido con un filtro de mediana y se aplicó un umbral adaptativo.
5. En las tres tablas escaneadas de Apollo 11 se aplicó un tratamiento específico: ampliación al doble, desenfoque gaussiano suave y umbral de Otsu. Para estas tablas se utilizó PSM 6, que agrupa el texto como un bloque; para las demás imágenes se utilizó PSM 11, adecuado para localizar bloques de texto dispersos.
6. Se convirtió la matriz procesada a una imagen PIL y se envió a Tesseract mediante PyTesseract.
7. La salida TSV de Tesseract se agrupó por líneas. Para cada línea se guardaron el texto, la confianza media y las coordenadas aproximadas.
8. Se guardó una imagen procesada, un TXT individual por imagen y un CSV conjunto.

## 5. Resultados

- Imágenes procesadas correctamente: **23 de 23**.
- Líneas reconocidas y exportadas: **1.712**.
- Confianza media agregada de los resúmenes por imagen: **67,83/100**.
- Las tres tablas Apollo 11 obtuvieron confianzas medias de **86,41**, **85,76** y **80,65**.

La confianza de Tesseract es una medida interna de la calidad estimada del reconocimiento; no debe interpretarse como una probabilidad de que el texto sea correcto. Algunas fotografías de documentos obtuvieron valores más bajos por el tamaño de letra, la perspectiva, la iluminación o las líneas de las tablas.

## 6. Archivos generados

- `resultados/imagenes_procesadas/`: versiones de las imágenes después del preprocesamiento.
- `resultados/textos/`: texto OCR separado para cada imagen.
- `resultados/ocr_lineas.csv`: conjunto principal, una fila por línea reconocida, con texto, confianza y coordenadas.
- `resultados/resumen_imagenes.csv`: resumen del proceso para cada imagen.
- `resultados/resultado_completo.txt`: todos los textos OCR concatenados.

El CSV principal estructura el reconocimiento por líneas, no reconstruye automáticamente cada celda de una tabla. Para obtener una tabla semántica con columnas como tiempo, evento, actitud o velocidad habría que aplicar reglas específicas y revisar las celdas manualmente.

## 7. Problemas y limitaciones

- Las fotografías pueden estar giradas y el detector automático puede equivocarse.
- Las sombras, el desenfoque y la perspectiva reducen la calidad del texto.
- Las líneas de las tablas pueden confundirse con caracteres o separar incorrectamente las palabras.
- Algunos caracteres parecidos (por ejemplo, `0` y `O`, o `1` y `I`) pueden intercambiarse.
- Los números, las abreviaturas, las fechas y los nombres propios requieren especial revisión.
- No se espera una precisión del 100 % con OCR generalista.

## 8. Conclusión

La práctica demuestra que es posible transformar imágenes en un conjunto de datos CSV utilizando OpenCV y PyTesseract. El preprocesamiento mejora la legibilidad y la corrección de orientación ayuda con las páginas fotografiadas de lado. Sin embargo, la calidad del reconocimiento depende mucho de la imagen de origen y del tipo de documento. Por ello, el OCR debe considerarse una primera extracción automática que necesita validación humana, especialmente cuando se trabaja con datos numéricos o tablas.
