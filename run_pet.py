"""Project entry point; paths are independent of the terminal working directory."""
import json
from pathlib import Path
import runpy
import sys
import os
import traceback

ROOT = Path(__file__).resolve().parent
APP = ROOT / "CetaPet"
sys.path.insert(0, str(APP))


def check_environment():
    import PySide6
    from PySide6.QtGui import QImage
    import requests
    import runtime_config
    import main as pet

    missing = [rel for rel in pet.IMAGE_RELS.values()
               if QImage(str(Path(pet.ASSET_ROOT) / rel)).isNull()]
    if missing:
        raise RuntimeError(f"Missing or unreadable runtime images: {missing}")
    from sakura_animation import ASSET_DIR, PLACEMENT
    import sakura_material
    sakura_missing = [name for name in PLACEMENT
                      if QImage(str(ASSET_DIR / f'{name}.png')).isNull()]
    if sakura_missing:
        raise RuntimeError(f'Missing or unreadable Sakura parts: {sakura_missing}')
    print(json.dumps({
        "python": sys.version.split()[0], "executable": sys.executable,
        "application": str(APP), "pyside6": PySide6.__version__,
        "requests": requests.__version__, "runtime_images": len(pet.IMAGE_RELS),
        "sakura_parts": len(PLACEMENT), "default_character": "佐仓三叶",
        "stealth_backend": "numpy-float64" if sakura_material.np is not None else "python-scalar",
        "numpy": sakura_material.np.__version__ if sakura_material.np is not None else None,
        "env_file": str(runtime_config.ENV_PATH),
        "key_configured": bool(runtime_config.read_api_key()),
        "model": runtime_config.read_model(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check_environment()
    else:
        try:
            runpy.run_path(str(APP / "main.py"), run_name="__main__")
        except Exception:
            detail = traceback.format_exc()
            try:
                import runtime_config
                secret = runtime_config.read_api_key()
                if secret:
                    detail = detail.replace(secret, '[redacted]')
            except Exception:
                detail = 'Startup failure; exception details could not be sanitized.'
            log = ROOT / '.bootstrap' / 'startup_error.log'
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(detail, encoding='utf-8')
            if sys.platform == 'win32':
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, '三叶启动失败。请查看：\n' + str(log), '佐仓三叶', 0x10)
            if sys.stderr is not None:
                sys.stderr.write(detail)
            raise SystemExit(1) from None
