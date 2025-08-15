from pydantic import BaseModel, Field
from typing import List

class PredictQuery(BaseModel):
    steps: int = Field(6, ge=1, le=60, description="pasos a pronosticar")
    alpha: float = Field(0.05, gt=0, lt=1, description="nivel de significancia 0.05 ≈ 95%")

class ForecastPoint(BaseModel): 
    date: str
    mean: float
    lower: float
    upper: float

class PredictResponse(BaseModel):
    medicamento: str
    steps: int
    start: str
    forecast: List[ForecastPoint]