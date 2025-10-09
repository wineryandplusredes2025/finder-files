#!/usr/bin/env python3
"""
Watcher simple para la carpeta `pdfs/`.
Detecta creación/modificación/eliminación de archivos .pdf (ignorando la carpeta thumbs)
y ejecuta `generate_thumbnails.py` con debounce para evitar ejecuciones en ráfaga.

Uso:
    python tools/watch_generate_thumbnails.py --source "C:\\Users\\VENTAS 4\\Desktop\\Finder fichas tecnicas\\pdfs" --out "C:\\Users\\VENTAS 4\\Desktop\\Finder fichas tecnicas\\pdfs\\thumbs" --size 320 --debounce 2.0

Requiere: watchdog
"""
import argparse
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class DebouncedRunner:
    def __init__(self, delay, fn):
        self.delay = delay
        self.fn = fn
        self._timer = None
        self._lock = threading.Lock()

    def schedule(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.delay, self._run)
            self._timer.daemon = True
            self._timer.start()

    def _run(self):
        try:
            self.fn()
        except Exception:
            logging.exception('Error during debounced run')


class PdfChangeHandler(FileSystemEventHandler):
    def __init__(self, runner, source_dir, ignore_subdir):
        super().__init__()
        self.runner = runner
        self.source_dir = os.path.abspath(source_dir)
        self.ignore_subdir = os.path.abspath(ignore_subdir) if ignore_subdir else None

    def _is_pdf_event(self, src_path):
        path = os.path.abspath(src_path)
        if self.ignore_subdir and path.startswith(self.ignore_subdir):
            return False
        return path.lower().endswith('.pdf')

    def on_created(self, event):
        if not event.is_directory and self._is_pdf_event(event.src_path):
            logging.info('PDF creado: %s', event.src_path)
            self.runner.schedule()

    def on_modified(self, event):
        if not event.is_directory and self._is_pdf_event(event.src_path):
            logging.info('PDF modificado: %s', event.src_path)
            self.runner.schedule()

    def on_moved(self, event):
        # mover puede traer nuevos archivos
        if not event.is_directory and self._is_pdf_event(event.dest_path):
            logging.info('PDF movido a: %s', event.dest_path)
            self.runner.schedule()

    def on_deleted(self, event):
        if not event.is_directory and self._is_pdf_event(event.src_path):
            logging.info('PDF eliminado: %s', event.src_path)
            # Actualizar la lista names.txt de inmediato para reflejar la eliminación
            try:
                update_names_txt(self.source_dir)
            except Exception:
                logging.exception('Error al actualizar names.txt tras eliminación')
            # Programar la regeneración de miniaturas (debounced)
            self.runner.schedule()


def call_generate(source, out, size):
    script_dir = Path(__file__).resolve().parent
    gen_script = script_dir / 'generate_thumbnails.py'
    if not gen_script.exists():
        logging.error('No se encontró generate_thumbnails.py en %s', script_dir)
        return
    cmd = [sys.executable, str(gen_script), '--source', source, '--out', out, '--size', str(size)]
    logging.info('Ejecutando: %s', ' '.join(cmd))
    try:
        # Ejecutar y esperar. Capturamos la salida para que quede visible en consola.
        res = subprocess.run(cmd, cwd=str(script_dir), check=False)
        logging.info('generate_thumbnails.py finalizó con código %s', res.returncode)
    except Exception:
        logging.exception('Fallo al ejecutar generate_thumbnails.py')


def update_names_txt(source_dir):
    """Regenera pdfs/names.txt con la lista ordenada de PDFs encontrados en source_dir."""
    try:
        src = Path(source_dir)
        if not src.exists():
            logging.warning('Source directory no existe: %s', source_dir)
            return
        pdfs = [p.name for p in src.rglob('*.pdf') if p.is_file()]
        pdfs_sorted = sorted(pdfs, key=lambda s: s.lower())
        out_file = src / 'names.txt'
        logging.info('Actualizando %s (%d archivos)', out_file, len(pdfs_sorted))
        with out_file.open('w', encoding='utf-8') as f:
            for name in pdfs_sorted:
                f.write(name + '\n')
    except Exception:
        logging.exception('Error al actualizar names.txt')


def main():
    parser = argparse.ArgumentParser(description='Watcher: regenerar miniaturas cuando cambien PDFs')
    # Valores por defecto específicos para tu workspace en Windows
    parser.add_argument('--source', default=r'C:\Users\VENTAS 4\Desktop\Finder fichas tecnicas\pdfs', help='Carpeta donde están los PDFs (por defecto: ruta del workspace)')
    parser.add_argument('--out', default=r'C:\Users\VENTAS 4\Desktop\Finder fichas tecnicas\pdfs\thumbs', help='Carpeta de salida de miniaturas (por defecto: ruta del workspace)')
    parser.add_argument('--size', type=int, default=320, help='Ancho de miniatura en px')
    parser.add_argument('--debounce', type=float, default=2.0, help='Segundos de debounce antes de ejecutar el generador')
    parser.add_argument('--no-initial', action='store_true', help='No ejecutar la generación inicial al arrancar')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

    source = os.path.abspath(args.source)
    out = os.path.abspath(args.out)

    # Ignorar la carpeta de thumbs dentro de source si está dentro
    ignore_subdir = out if out.startswith(source) else None

    def run_gen():
        # Primero actualizar names.txt para mantener la lista sincronizada
        update_names_txt(source)
        call_generate(source, out, args.size)

    runner = DebouncedRunner(args.debounce, run_gen)

    if not args.no_initial:
        logging.info('Ejecución inicial del generador de miniaturas...')
        run_gen()

    event_handler = PdfChangeHandler(runner, source, ignore_subdir)
    observer = Observer()
    observer.schedule(event_handler, path=source, recursive=True)

    try:
        logging.info('Observando %s (presiona Ctrl+C para salir)', source)
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info('Saliendo...')
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
