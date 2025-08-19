"""
Punto de entrada de la API:
- Crea la app de FastAPI
- Habilita CORS (para que tu frontend pueda llamar a la API)
- Importa modelos y crea las tablas si no existen
- Registra los routers (módulos)
"""


"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


from pathlib import Path
import pandas as pd

from .schemas import PredictQuery, PredictResponse, ForecastPoint
from .models_loader import ModelRegistry

# --- Config básica ---
BASE_DIR = Path(__file__).resolve().parents[1]
MODELOS_DIR = BASE_DIR / "modelos"

app = FastAPI(title="ARIMA Forecast API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

# --- Cargar modelos al inicio ---
registry = ModelRegistry(MODELOS_DIR)
loaded = registry.load_all()
print(f"[INIT] Modelos cargados: {loaded} desde {MODELOS_DIR}")

# --- Endpoints básicos ---
@app.get("/")
def root():
    return {"ok": True, "msg": "API viva. Prueba /docs"}

@app.get("/health")
def health():
    return {"status": "ok", "models": registry.keys()}

@app.get("/medicamentos")
def medicamentos():
    return registry.keys()

@app.post("/reload")
def reload_models():
    n = registry.load_all()
    return {"reloaded": n, "models": registry.keys()}

# --- Pronóstico ---
@app.post("/predict/{med}", response_model=PredictResponse)
def predict(med: str, body: PredictQuery):
    model = registry.get(med)
    if model is None:
        raise HTTPException(status_code=404, detail=f"No hay modelo para '{med}'. "
                            f"Coloca {med}.pkl en /modelos o revisa /medicamentos.")

    try:
        res = model.get_forecast(steps=body.steps, alpha=body.alpha)
        mean = res.predicted_mean
        conf = res.conf_int(alpha=body.alpha)

        # Intentamos usar el índice original; si no es de fechas, creamos mensual desde hoy:
        index = mean.index
        if not isinstance(index, (pd.DatetimeIndex, pd.PeriodIndex)):
            start = pd.Timestamp.today().normalize()
            index = pd.date_range(start=start, periods=body.steps, freq="MS")

        points = []
        for i, ts in enumerate(index):
            points.append(
                ForecastPoint(
                    date=str(ts)[:10],
                    mean=float(mean.iloc[i]),
                    lower=float(conf.iloc[i, 0]),
                    upper=float(conf.iloc[i, 1]),
                )
            )

        return PredictResponse(
            medicamento=med,
            steps=body.steps,
            start=str(index[0])[:10],
            forecast=points
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al pronosticar: {e}")
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine
# importa modelos antes de create_all
from .models.user import User
from .models.medicine import Medicine
from .models.historical import Historical
from .models.prediction import Prediction
from .models.report import Report
from .routers import auth, historical, visualize, predict

app = FastAPI(title="Medicamentos API (ARIMA PKL por 4 atributos)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_methods=["*"], 
    allow_headers=["*"], 
    allow_credentials=True,
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root(): return {"ok": True, "msg": "API viva. Visita /docs"}

app.include_router(auth.router)
app.include_router(historical.router)
app.include_router(visualize.router)
app.include_router(predict.router)