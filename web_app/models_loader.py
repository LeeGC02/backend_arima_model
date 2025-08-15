from pathlib import Path
from typing import Dict, Optional
import joblib

class ModelRegistry:
    """
    Carga todos los .pkl desde 'modelos/' y los deja en memoria.
    La clave del modelo es el nombre del archivo sin .pkl (p.ej. paracetamol.pkl -> 'paracetamol').
    """
    def __init__(self, modelos_dir: Path):
        self.modelos_dir = modelos_dir
        self._modelos: Dict[str, object] = {}
    
    def load_all(self) -> int:
        self._modelos.clear()
        self.modelos_dir.mkdir(parents=True, exist_ok=True)
        count = 0 
        for p in self.modelos_dir.glob("*.pkl"):
            try:
                m = joblib.load(p)
                if hasattr (m, "get_forecast"):
                    self._modelos[p.stem] = m
                    count += 1 
                else: 
                    print(f"[WARN] {p.name} no expone get forecast()")
            except Exception as e:
                print(f"[WARN] No se pudo cargar {p.name}: {e}")
        return count
    def keys(self):
        return sorted(self._modelos.keys())
    def get(self, key: str) -> Optional[object]:
        return self._modelos.get(key)