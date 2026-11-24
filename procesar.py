"""Preprocesamiento y OCR de imágenes con OpenCV y Tesseract.

Genera:
- resultados/imagenes_procesadas/: imágenes en gris/umbralizadas utilizadas por OCR.
- resultados/textos/: texto OCR individual por imagen.
- resultados/ocr_lineas.csv: una fila por línea reconocida, con confianza y coordenadas.
- resultados/resumen_imagenes.csv: resumen de cada imagen procesada.
- resultados/resultado_completo.txt: texto OCR concatenado.

Uso:
    python procesar.py
    python procesar.py --lang eng
    python procesar.py --tesseract "C:/Program Files/Tesseract-OCR/tesseract.exe"
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def rotate_image(image: np.ndarray, clockwise_degrees: int) -> np.ndarray:
    """Rota una imagen en incrementos de 90 grados en sentido horario."""
    if clockwise_degrees == 0:
        return image
    if clockwise_degrees == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if clockwise_degrees == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if clockwise_degrees == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError("La rotación debe ser 0, 90, 180 o 270")


def resize_max_side(image: np.ndarray, max_side: int) -> np.ndarray:
    """Reduce imágenes grandes sin cambiar su proporción."""
    height, width = image.shape[:2]
    largest = max(height, width)
    if largest <= max_side:
        return image
    scale = max_side / largest
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def quick_orientation_score(image: np.ndarray) -> float:
    """Puntúa una orientación con OCR rápido sobre una miniatura de 650 px."""
    small = resize_max_side(image, 650)
    if len(small.shape) == 3:
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    else:
        gray = small
    try:
        data = pytesseract.image_to_data(
            gray,
            lang="eng",
            config="--oem 3 --psm 11",
            output_type=Output.DICT,
            timeout=12,
        )
        confidences = []
        for word, confidence in zip(data["text"], data["conf"]):
            try:
                value = float(confidence)
            except (TypeError, ValueError):
                continue
            if str(word).strip() and value >= 0:
                confidences.append(value)
        if not confidences:
            return 0.0
        # La raíz del número de palabras favorece orientaciones que reconocen
        # más contenido, sin dejar que la cantidad domine por completo la confianza.
        return float(np.mean(confidences)) * math.sqrt(len(confidences))
    except Exception:
        return 0.0


def detect_orientation(image: np.ndarray, lang: str) -> tuple[np.ndarray, int]:
    """Usa OSD y, si su confianza es baja, contrasta las cuatro orientaciones."""
    small = resize_max_side(image, 1100)
    try:
        osd = pytesseract.image_to_osd(
            small,
            lang="osd",
            output_type=Output.DICT,
            timeout=12,
        )
        degrees = int(osd.get("rotate", 0)) % 360
        confidence = float(osd.get("orientation_conf", 0.0))
        if degrees in (0, 90, 180, 270) and confidence >= 2.5:
            return rotate_image(image, degrees), degrees
    except Exception as exc:
        print(f"  Aviso: OSD no concluyente; se compararán las orientaciones ({exc}).")

    best_rotation = 0
    best_score = float("-inf")
    for degrees in (0, 90, 180, 270):
        candidate = rotate_image(image, degrees)
        score = quick_orientation_score(candidate)
        if score > best_score:
            best_score = score
            best_rotation = degrees
    return rotate_image(image, best_rotation), best_rotation


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Convierte a escala de grises, mejora contraste y aplica umbral adaptativo."""
    # OpenCV carga normalmente BGR; también se contempla una imagen ya en gris.
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Mejora el contraste local de fotografías con iluminación desigual.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.medianBlur(enhanced, 3)

    # Umbral adaptativo: separa texto y fondo cuando la iluminación no es uniforme.
    processed = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return processed


def extract_lines(data: dict[str, list[Any]], image_name: str) -> list[dict[str, Any]]:
    """Agrupa las palabras TSV de Tesseract en líneas con sus coordenadas."""
    groups: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
    for index, word in enumerate(data["text"]):
        if not str(word).strip():
            continue
        key = (
            int(data["page_num"][index]),
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        groups[key].append(index)

    rows: list[dict[str, Any]] = []
    for line_number, (key, indices) in enumerate(sorted(groups.items()), start=1):
        words = [str(data["text"][i]).strip() for i in indices if str(data["text"][i]).strip()]
        if not words:
            continue
        confidences = []
        for i in indices:
            try:
                value = float(data["conf"][i])
                if value >= 0:
                    confidences.append(value)
            except (TypeError, ValueError):
                pass
        lefts = [int(data["left"][i]) for i in indices]
        tops = [int(data["top"][i]) for i in indices]
        rights = [int(data["left"][i]) + int(data["width"][i]) for i in indices]
        bottoms = [int(data["top"][i]) + int(data["height"][i]) for i in indices]
        rows.append({
            "imagen": image_name,
            "pagina": key[0],
            "bloque": key[1],
            "parrafo": key[2],
            "linea": line_number,
            "texto": " ".join(words),
            "confianza_media": round(float(np.mean(confidences)), 2) if confidences else "",
            "x": min(lefts),
            "y": min(tops),
            "ancho": max(rights) - min(lefts),
            "alto": max(bottoms) - min(tops),
        })
    return rows


def clean_filename(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("_")
    return stem or "imagen"


def process_one(
    image_path: Path,
    output_dir: Path,
    lang: str,
    max_side: int,
    auto_rotate: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("OpenCV no pudo abrir el archivo (formato o archivo no válido).")

    original_height, original_width = image.shape[:2]
    is_apollo_table = image_path.name.lower().startswith("apollo 11")
    rotation = 0

    if is_apollo_table:
        # Las tres láminas Apollo son escaneos rectos de tablas impresas.
        # Se conserva su orientación original, se amplían 2x y se usa Otsu + PSM 6,
        # que agrupa el contenido de las filas mejor que el modo de texto disperso.
        image = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        processed = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]
        ocr_config = "--oem 3 --psm 6 -c preserve_interword_spaces=1"
    else:
        image = resize_max_side(image, max_side)
        if auto_rotate:
            image, rotation = detect_orientation(image, lang)
        processed = preprocess_image(image)
        ocr_config = "--oem 3 --psm 11 -c preserve_interword_spaces=1"

    safe_stem = clean_filename(image_path.name)
    processed_path = output_dir / "imagenes_procesadas" / f"{safe_stem}_procesada.png"
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(processed_path), processed):
        raise IOError(f"No se pudo guardar {processed_path}")

    pil_image = Image.fromarray(processed)
    data = pytesseract.image_to_data(
        pil_image,
        lang=lang,
        config=ocr_config,
        output_type=Output.DICT,
        timeout=45,
    )
    rows = extract_lines(data, image_path.name)
    full_text = "\n".join(row["texto"] for row in rows)

    text_dir = output_dir / "textos"
    text_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / f"{safe_stem}.txt").write_text(full_text + "\n", encoding="utf-8")

    confidences = [
        float(row["confianza_media"])
        for row in rows
        if row["confianza_media"] != ""
    ]
    summary = {
        "imagen": image_path.name,
        "ancho_original": original_width,
        "alto_original": original_height,
        "rotacion_aplicada_grados": rotation,
        "lineas_reconocidas": len(rows),
        "confianza_media": round(float(np.mean(confidences)), 2) if confidences else "",
        "archivo_preprocesado": str(processed_path.relative_to(output_dir.parent)),
    }
    return rows, summary, full_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Procesa imágenes con OpenCV y PyTesseract.")
    parser.add_argument("--input", default="imagenes_originales", help="Carpeta con las imágenes de entrada.")
    parser.add_argument("--output", default="resultados", help="Carpeta donde guardar los resultados.")
    parser.add_argument("--lang", default="eng+spa", help="Idiomas instalados en Tesseract, por ejemplo eng o eng+spa.")
    parser.add_argument("--tesseract", default=os.environ.get("TESSERACT_CMD"), help="Ruta al ejecutable Tesseract (opcional).")
    parser.add_argument("--max-side", type=int, default=1600, help="Lado máximo de las imágenes al procesarlas (por defecto: 1600 px).")
    parser.add_argument("--skip-orientation", action="store_true", help="No probar rotaciones automáticas (más rápido).")
    args = parser.parse_args()

    if args.tesseract:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: no existe la carpeta de entrada: {input_dir}", file=sys.stderr)
        return 1

    image_paths = sorted(
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not image_paths:
        print(f"No se encontraron imágenes compatibles en {input_dir}.", file=sys.stderr)
        return 1

    try:
        print(f"Tesseract detectado: {pytesseract.get_tesseract_version()}")
        available_languages = pytesseract.get_languages(config="")
        requested_languages = args.lang.split("+")
        missing = [language for language in requested_languages if language not in available_languages]
        if missing:
            raise RuntimeError(
                f"Faltan idiomas de Tesseract: {', '.join(missing)}. "
                "Instala sus archivos .traineddata o ejecuta con --lang eng."
            )
    except Exception as exc:
        print(f"Error al inicializar Tesseract: {exc}", file=sys.stderr)
        print("Comprueba que Tesseract OCR está instalado y que su ejecutable está en el PATH.", file=sys.stderr)
        return 1

    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    full_text_parts: list[str] = []
    failures: list[tuple[str, str]] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for number, image_path in enumerate(image_paths, start=1):
        print(f"[{number}/{len(image_paths)}] Procesando: {image_path.name}")
        try:
            rows, summary, full_text = process_one(
                image_path=image_path,
                output_dir=output_dir,
                lang=args.lang,
                max_side=args.max_side,
                auto_rotate=not args.skip_orientation,
            )
            all_rows.extend(rows)
            summaries.append(summary)
            full_text_parts.append(f"===== {image_path.name} =====\n{full_text}\n")
            print(
                f"    Rotación: {summary['rotacion_aplicada_grados']}° | "
                f"Líneas: {summary['lineas_reconocidas']} | "
                f"Confianza media: {summary['confianza_media']}"
            )
        except Exception as exc:
            failures.append((image_path.name, str(exc)))
            print(f"    ERROR: {exc}", file=sys.stderr)

    output_dir.mkdir(parents=True, exist_ok=True)
    line_csv = output_dir / "ocr_lineas.csv"
    line_fields = ["imagen", "pagina", "bloque", "parrafo", "linea", "texto", "confianza_media", "x", "y", "ancho", "alto"]
    with line_csv.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=line_fields)
        writer.writeheader()
        writer.writerows(all_rows)

    summary_csv = output_dir / "resumen_imagenes.csv"
    summary_fields = ["imagen", "ancho_original", "alto_original", "rotacion_aplicada_grados", "lineas_reconocidas", "confianza_media", "archivo_preprocesado"]
    with summary_csv.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summaries)

    (output_dir / "resultado_completo.txt").write_text(
        "\n".join(full_text_parts), encoding="utf-8"
    )

    print("\nProceso terminado.")
    print(f"Imágenes encontradas: {len(image_paths)}")
    print(f"Imágenes procesadas: {len(summaries)}")
    print(f"Líneas OCR guardadas: {len(all_rows)}")
    print(f"CSV de líneas: {line_csv}")
    print(f"CSV resumen: {summary_csv}")
    if failures:
        print("\nArchivos con errores:")
        for filename, error in failures:
            print(f"- {filename}: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
