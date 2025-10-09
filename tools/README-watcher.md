Watcher para generación de miniaturas

Este archivo explica cómo instalar dependencias y ejecutar el watcher en Windows (PowerShell).

1) (Opcional) Crear entorno virtual y activarlo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Instalar dependencias:

```powershell
pip install -r .\tools\requirements.txt
```

3) Ejecutar el watcher (desde la raíz del repo):

```powershell
python .\tools\watch_generate_thumbnails.py --source "C:\Users\VENTAS 4\Desktop\Finder fichas tecnicas\pdfs" --out "C:\Users\VENTAS 4\Desktop\Finder fichas tecnicas\pdfs\thumbs" --size 320
```

- Usar `--no-initial` para evitar la ejecución inicial del generador.
- Para ejecutar en background puedes abrir otra ventana de PowerShell o usar `Start-Process`:

```powershell
Start-Process -NoNewWindow -FilePath python -ArgumentList '.\tools\watch_generate_thumbnails.py --source "C:\Users\VENTAS 4\Desktop\Finder fichas tecnicas\pdfs" --out "C:\Users\VENTAS 4\Desktop\Finder fichas tecnicas\pdfs\thumbs" --size 320'
```

Notas:
- El watcher ignora cambios dentro de la carpeta de miniaturas si ésta está ubicada dentro de `pdfs/`.
- El debounce por defecto es 2 segundos; puedes ajustarlo con `--debounce`.
