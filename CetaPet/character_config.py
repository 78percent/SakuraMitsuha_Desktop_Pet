"""Versioned character preferences; never touches chat, RAG or credentials."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

MODEL_IDS = ('q', 'realistic')


def geometry(value):
    if not isinstance(value, dict):
        return None
    if not all(type(value.get(k)) is int for k in ('x', 'y', 'height')):
        return None
    if not 180 <= value['height'] <= 720:
        return None
    if any(abs(value[k]) > 100000 for k in ('x', 'y')):
        return None
    return {k: value[k] for k in ('x', 'y', 'height')}


class CharacterConfig:
    def __init__(self, path):
        self.path = Path(path)
        self.warning = ''

    def read(self):
        self.warning = ''
        try:
            data = json.loads(self.path.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('config must be an object')
        except FileNotFoundError:
            data = {}
        except (ValueError, UnicodeError):
            self.warning = '配置损坏，已使用Q版默认设置'
            data = {}
        except OSError:
            self.warning = '配置无法读取，已使用Q版默认设置'
            data = {}
        raw = data.get('model_selector', {})
        raw = raw if isinstance(raw, dict) else {}
        layouts = raw.get('geometry', {})
        layouts = layouts if isinstance(layouts, dict) else {}
        layouts = {k: g for k in MODEL_IDS if (g := geometry(layouts.get(k)))}
        # Legacy coordinates belong only to Q, never to the alternate character.
        if 'q' not in layouts:
            old = geometry(dict(x=data.get('window_x'), y=data.get('window_y'), height=180))
            if old:
                layouts['q'] = old
        selected = raw.get('selected', 'q')
        if selected not in MODEL_IDS or raw.get('version', 1) != 1:
            selected = 'q'
        return dict(selected=selected, geometry=layouts)

    def update(self, selected, layouts):
        if selected not in MODEL_IDS or any(geometry(g) is None for g in layouts.values()):
            raise ValueError('invalid character preferences')
        # Re-read on every write so unrelated/unknown fields are retained.
        try:
            original = self.path.read_bytes()
        except FileNotFoundError:
            original = None
        try:
            data = json.loads(original.decode('utf-8-sig')) if original is not None else {}
            if not isinstance(data, dict):
                raise ValueError('config must be an object')
        except (ValueError, UnicodeError):
            # Preserve malformed input before a recovery write. Never overwrite a backup.
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=self.path.name + '.corrupt-', delete=False) as backup:
                backup.write(original)
            data = {}
        raw = data.get('model_selector', {})
        raw = deepcopy(raw) if isinstance(raw, dict) else {}
        if raw.get('version', 1) != 1:
            raise ValueError('unsupported model_selector version')
        previous = raw.get('geometry', {})
        previous = previous if isinstance(previous, dict) else {}
        previous.update(deepcopy(layouts))
        raw.update(version=1, selected=selected, geometry=previous)
        data['model_selector'] = raw
        if 'q' in layouts:
            data.update(window_x=layouts['q']['x'], window_y=layouts['q']['y'])
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix=self.path.name + '.', suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

