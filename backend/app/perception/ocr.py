import hashlib
from app.core.config import settings

_READER = None
_LOAD_COUNT = 0
_CACHE = {}

def get_reader():
    global _READER, _LOAD_COUNT
    if _READER is None:
        try:
            import easyocr
            _READER = easyocr.Reader(['en'], gpu=False)
            _LOAD_COUNT += 1
        except ImportError:
            class DummyReader:
                def readtext(self, payload): return []
            _READER = DummyReader()
    return _READER

def reader_load_count() -> int:
    return _LOAD_COUNT

def reset_ocr_state():
    global _READER, _LOAD_COUNT, _CACHE
    _READER = None
    _LOAD_COUNT = 0
    _CACHE.clear()

def should_run_ocr(dom_sufficient: bool, canvases: list, required_missing: bool) -> tuple[bool, str]:
    if not settings.enable_ocr:
        return False, "ocr_disabled"
        
    if dom_sufficient:
        return False, "dom_sufficient"
        
    if canvases:
        return True, "Canvas detected"
        
    if required_missing:
        return True, "Required text missing from DOM"
        
    return False, "Not required"

def run_ocr(image_bytes: bytes, task: str, bboxes: list = None) -> list[str]:
    if not settings.enable_ocr:
        return []
        
    if settings.ocr_cache:
        h = hashlib.sha256(image_bytes).hexdigest()
        if h in _CACHE:
            return _CACHE[h]
            
    reader = get_reader()
    results = reader.readtext(image_bytes)
    texts = [res[1] for res in results]
    
    if settings.ocr_cache:
        h = hashlib.sha256(image_bytes).hexdigest()
        _CACHE[h] = texts
        
    return texts
