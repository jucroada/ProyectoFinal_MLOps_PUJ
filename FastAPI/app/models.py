from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class PredictRequest(BaseModel):
    features: Dict[str, Any]      

class PredictResponse(BaseModel):
    prediction: float
    run_id: str
    model_version: int

class ModelUpdatePayload(BaseModel):
    model_name: str
    model_version: int
    run_id: str

class HistoryEntry(BaseModel):
    experiment_id: int
    model_name  : str
    run_id: str
    run_name: str
    model_version: int
    new_mse: float
    new_rmse: float
    new_mae: float
    new_r2: float
    prod_mse: Optional[float]
    prod_rmse: Optional[float]
    prod_mae: Optional[float]
    prod_r2: Optional[float]
    promoted: bool
    shap_uri: Optional[str]
    trained_at: str  # ISO timestamp

class ShapResponse(BaseModel):
    run_id: str
    shap_values: Dict[str, List[Any]]  