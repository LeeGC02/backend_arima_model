"""
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
"""

from pydantic import BaseModel, EmailStr
from datetime import date

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool

class UploadSummary(BaseModel):
    rows_inserted: int
    file_saved_as: str

# Predicción por 4 atributos (concentration puede venir número)
class PredictByAttrs(BaseModel):
    name: str
    concentration: str | int
    dosage_form: str
    unit_measure: str
    periods: int = 6

class ForecastPoint(BaseModel):
    date: date
    yhat: float

class PredictResponse(BaseModel):
    modelo: str
    points: list[ForecastPoint]
