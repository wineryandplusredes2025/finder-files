"""
Script offline para generar miniaturas PNG de la primera página de cada PDF en la carpeta `pdfs/`.

Salida:
- `pdfs/thumbs/<safe-filename>.png` para cada PDF procesado.
- `pdfs/thumbs/manifest.json` con un mapeo { "Original Name.pdf": "thumbs/safe-filename.png" }

Requisitos:
- Python 3.8+
- Instalar dependencias: pip install -r tools/requirements.txt

Uso:
    python tools/generate_thumbnails.py --source ./pdfs --out ./pdfs/thumbs --size 320

Nota: usa PyMuPDF (fitz) para renderizar la página 0 a una imagen. Ajusta `size` para controlar el ancho del thumbnail (la altura se calcula manteniendo la proporción).
"""

import os
import sys
import json
import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from PIL import Image
except Exception as e:
    print("Falta alguna dependencia: instale 'PyMuPDF' y 'Pillow'. Ejecuta: pip install -r tools/requirements.txt")
    raise


def safe_name(name: str) -> str:
    # crear nombre de archivo seguro para el thumbnail
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in name)


def generate_thumbnail(pdf_path: Path, out_path: Path, width: int) -> Path:
    doc = fitz.open(pdf_path)
    if doc.page_count == 0:
        raise RuntimeError(f"PDF sin páginas: {pdf_path}")
    page = doc.load_page(0)
    # zoom para obtener la anchura solicitada
    rect = page.rect
    scale = width / rect.width
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_data = pix.tobytes('png')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(img_data)
    doc.close()
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Genera miniaturas PNG de la primera página de PDFs')
    parser.add_argument('--source', default='./pdfs', help='Carpeta que contiene PDFs')
    parser.add_argument('--out', default='./pdfs/thumbs', help='Carpeta destino para miniaturas')
    parser.add_argument('--size', type=int, default=320, help='Ancho en px de la miniatura')
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    size = args.size

    if not source.exists():
        print(f"La carpeta fuente no existe: {source}")
        sys.exit(1)

    pdfs = sorted([p for p in source.iterdir() if p.is_file() and p.suffix.lower() == '.pdf'])
    if not pdfs:
        print("No se encontraron PDFs en la carpeta fuente.")
        sys.exit(0)

    manifest = {}
    print(f"Procesando {len(pdfs)} PDFs desde {source} -> {out_dir} (thumb width={size})")

    for p in pdfs:
        try:
            safe = safe_name(p.name) + '.png'
            out_file = out_dir / safe
            if out_file.exists():
                print(f"Ya existe, saltando: {out_file.name}")
                manifest[p.name] = os.path.relpath(out_file, start=out_dir.parent)
                continue
            print(f"Generando thumbnail para: {p.name}")
            generate_thumbnail(p, out_file, size)
            manifest[p.name] = os.path.relpath(out_file, start=out_dir.parent)
        except Exception as e:
            print(f"Error procesando {p.name}: {e}")

    # escribir manifest
    out_manifest = out_dir / 'manifest.json'
    with open(out_manifest, 'w', encoding='utf-8') as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)

    print(f"Thumbnails generados. Manifest: {out_manifest}")


if __name__ == '__main__':
    main()
