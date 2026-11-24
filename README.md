# Práctica de OCR con OpenCV y PyTesseract

## 1. Descripción

Este proyecto convierte imágenes en información textual estructurada mediante **OpenCV** y **Tesseract OCR**, utilizando **PyTesseract** como interfaz desde Python.

El ZIP facilitado para la práctica contiene 23 imágenes de distinto tipo: páginas y cronogramas relacionados con Apollo 11, fotografías de tablas/documentos y capturas de pantalla. El programa procesa todos los ficheros compatibles que se encuentren en `imagenes_originales/`.

## 2. Objetivos

- Aplicar preprocesamiento de imágenes con OpenCV.
- Corregir automáticamente la orientación probando giros de 0°, 90°, 180° y 270°.
- Reconocer texto con Tesseract OCR desde PyTesseract.
- Guardar el resultado en CSV y TXT.
- Conservar información de confianza y coordenadas para facilitar la revisión de los resultados.

## 3. Estructura del proyecto

```text
Practica_OCR_Apollo11/
├── imagenes_originales/           # Imágenes de entrada proporcionadas
├── resultados/
│   ├── imagenes_procesadas/       # Imágenes después del preprocesamiento
│   ├── textos/                    # Un TXT por cada imagen
│   ├── ocr_lineas.csv             # Una fila por línea reconocida
│   ├── resumen_imagenes.csv       # Resumen por imagen
│   └── resultado_completo.txt     # Texto OCR concatenado
├── procesar.py                    # Programa principal
├── requirements.txt
├── .gitignore
└── README.md
```

## 4. Instalación

### 4.1. Crear un entorno virtual (recomendado)

Desde una terminal, dentro de la carpeta del proyecto:

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.2. Instalar las dependencias de Python

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3. Instalar Tesseract OCR

Tesseract es un programa independiente: instalar `pytesseract` con pip no instala el motor OCR.

- **Windows:** instala Tesseract desde [UB Mannheim - Tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Normalmente el ejecutable queda en `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **macOS:** `brew install tesseract`. Para disponer de los datos de idioma adicionales, instala el paquete de idiomas de Tesseract que corresponda a tu versión de Homebrew.
- **Ubuntu / Debian:** `sudo apt update && sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa`.

El programa utiliza por defecto los idiomas inglés y español (`eng+spa`), porque el contenido de las imágenes es mixto. Si no tienes instalado español, puedes ejecutar con `--lang eng`.

Comprueba que Tesseract está disponible:

```bash
tesseract --version
tesseract --list-langs
```

Si Windows no reconoce el comando `tesseract`, añade la carpeta de instalación al `PATH` o pasa la ruta del ejecutable al programa (ver apartado 5).

## 5. Ejecución

Con el entorno virtual activado y Tesseract instalado, ejecuta:

```bash
python procesar.py
```

Opciones disponibles:

```bash
# Reconocimiento solo en inglés
python procesar.py --lang eng

# Indicar manualmente la ubicación de Tesseract en Windows
python procesar.py --tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe"

# Procesamiento más rápido, sin detección automática de rotación
python procesar.py --skip-orientation

# Cambiar carpetas de entrada/salida
python procesar.py --input imagenes_originales --output resultados
```

Al terminar, los resultados se escriben en `resultados/`. Se pueden borrar los resultados anteriores y volver a ejecutar el script en cualquier momento.

## 6. Preprocesamiento aplicado

El programa realiza las siguientes operaciones:

1. **Lectura:** OpenCV carga cada archivo de imagen.
2. **Redimensionado:** reduce imágenes demasiado grandes manteniendo la proporción (máximo predeterminado: 1600 píxeles en el lado mayor).
3. **Corrección de orientación:** analiza las cuatro orientaciones posibles con una pasada OCR rápida y selecciona la que obtiene mejor puntuación. Cuando OSD no tiene suficiente confianza, contrasta las cuatro rotaciones con un OCR rápido sobre una miniatura.
4. **Escala de grises:** elimina la información de color que no es necesaria para reconocer el texto.
5. **CLAHE:** mejora el contraste local para compensar sombras o iluminación desigual.
6. **Reducción de ruido:** aplica un filtro de mediana.
7. **Umbral adaptativo:** convierte la imagen a blanco y negro para separar el texto del fondo.
8. **OCR:** PyTesseract envía la imagen preprocesada a Tesseract. Para las tres tablas Apollo 11, amplía la página al doble, aplica umbral Otsu y utiliza PSM 6 para mantener el contenido en bloques/filas; para las demás imágenes utiliza PSM 11, útil para localizar bloques de texto dispersos.

La imagen binarizada utilizada por OCR se guarda en `resultados/imagenes_procesadas/` para poder comprobar visualmente el efecto de las transformaciones.

## 7. Formatos de salida

### `ocr_lineas.csv`

Cada registro representa una línea reconocida. Sus campos son:

| Campo | Descripción |
|---|---|
| `imagen` | Nombre de la imagen de origen |
| `pagina`, `bloque`, `parrafo`, `linea` | Identificadores de segmentación de Tesseract |
| `texto` | Texto reconocido en esa línea |
| `confianza_media` | Confianza media asignada por Tesseract (0 a 100; no es una probabilidad garantizada) |
| `x`, `y`, `ancho`, `alto` | Rectángulo aproximado de la línea en píxeles de la imagen procesada |

### Otros ficheros

- `resumen_imagenes.csv`: una fila por imagen, con dimensiones, rotación, número de líneas y confianza media.
- `textos/`: texto completo reconocido para cada imagen.
- `resultado_completo.txt`: todos los textos reunidos en un archivo.


## 8. Resultado obtenido con las imágenes incluidas

En la ejecución preparada para esta entrega se procesaron las 23 imágenes del ZIP y se reconocieron 1.712 líneas de texto. La confianza media agregada de los resúmenes por imagen fue de aproximadamente 67,83/100. Este valor es orientativo: algunas capturas se reconocen con mucha claridad y varias fotografías de tablas tienen valores inferiores, por lo que requieren revisión manual.

## 9. Revisión de calidad y limitaciones

El OCR no garantiza una transcripción perfecta. Los resultados pueden contener errores por desenfoque, perspectiva, sombras, letra pequeña, tablas con líneas, columnas o texto girado. La confianza de Tesseract sirve como orientación, pero no demuestra que una palabra sea correcta.

Para evaluar el resultado:

1. Abre algunas imágenes de `resultados/imagenes_procesadas/` y comprueba si el texto aparece nítido y separado del fondo.
2. Abre `resultados/ocr_lineas.csv` y compara varias líneas con su imagen original.
3. Revisa especialmente números, abreviaturas, fechas, nombres propios y celdas de tablas.
4. Si el resultado es deficiente, prueba `--lang eng`, cambia el tamaño máximo o ajusta los parámetros de `preprocess_image()` (por ejemplo, el tamaño de bloque `31` y la constante `11` del umbral adaptativo).
5. Vuelve a ejecutar el programa después de cada cambio y compara los CSV.

El CSV es una estructuración por líneas de texto detectadas. No reconstruye automáticamente la estructura semántica de una tabla (filas y columnas); esa tarea requeriría reglas específicas para cada tipo de documento y una validación manual.

## 10. Subir el proyecto a GitHub

1. Crea un repositorio vacío en [GitHub](https://github.com/) con el nombre `Practica-OCR-Apollo11` (o el que te haya indicado el profesor).
2. Abre una terminal dentro de esta carpeta.
3. Inicializa Git y registra el proyecto:

```bash
git init
git add README.md requirements.txt .gitignore procesar.py
git commit -m "Añade estructura inicial y documentación de la práctica"
```

4. Añade las imágenes y los resultados generados en commits separados:

```bash
git add imagenes_originales/
git commit -m "Añade imágenes de entrada para OCR"

git add resultados/
git commit -m "Añade imágenes preprocesadas y resultados OCR"
```

5. Enlaza tu repositorio remoto (copia la URL que GitHub muestra al crear el repositorio) y sube los commits:

```bash
git branch -M main
git remote add origin URL_DE_TU_REPOSITORIO
git push -u origin main
```

No compartas contraseñas ni tokens en el repositorio. El enlace final de GitHub será la URL del repositorio que crees en tu cuenta.

## 11. Dependencias

Las librerías Python empleadas están listadas en `requirements.txt`: `opencv-python`, `pytesseract`, `Pillow` y `numpy`. Además, es necesario instalar el ejecutable externo **Tesseract OCR** y sus datos de idioma.
