from pathlib import Path
from typing import Dict, Optional, Tuple
import joblib

"""
class ModelRegistry:
    
    Carga todos los .pkl desde 'modelos/' y los deja en memoria.
    La clave del modelo es el nombre del archivo sin .pkl (p.ej. paracetamol.pkl -> 'paracetamol').
   
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
"""

def _norm(x: str) -> str:
    return x.strip().lower().replace(" ", "_")

def build_model_basename(name: str, concentration: str | int, dosage_form: str, unit_measure: str) -> str:
    # Debe coincidir con el entrenamiento:
    # f"{name.lower().replace(' ', '_')}_{concentration}_{dosage_form.lower()}_{unit_measure.lower()}"
    return f"{_norm(name)}_{str(concentration).strip()}_{_norm(dosage_form)}_{_norm(unit_measure)}"

class ModelRegistry:
    def __init__(self, modelos_dir: Path):
        self.dir = modelos_dir
        self._models: Dict[str, object] = {}

    def load_all(self) -> int:
        self._models.clear()
        self.dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for p in self.dir.glob("*.pkl"):
            try:
                m = joblib.load(p)
                if any(hasattr(m, fn) for fn in ("get_forecast", "forecast", "predict")):
                    self._models[p.stem] = m
                    count += 1
            except Exception as e:
                print(f"[WARN] {p.name} no se cargó: {e}")
        return count

    def keys(self): return sorted(self._models.keys())

    def get_by_attrs(self, name: str, concentration: str | int, dosage_form: str, unit_measure: str) -> Optional[Tuple[str, object]]:
        key = build_model_basename(name, concentration, dosage_form, unit_measure)
        m = self._models.get(key)
        if m is None:
            return None
        return key, m
    
    