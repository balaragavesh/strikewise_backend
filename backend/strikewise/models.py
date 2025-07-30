# strikewise/models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from typing import Literal

class AnalysisRequest(BaseModel):
    instrument_key: str
    expiry_date: str
    spot_target_gain: float
    spot_sl_loss: float
    capital: float
    risk_tolerance: float
    minutes_to_hit_target: int
    option_type: str

class Projection(BaseModel):
    Strike: float
    LTP: float
    Target_Premium: float
    SL_Premium: float
    Capital_Per_Lot: float
    Profit_Per_Lot: float
    Loss_Per_Lot: float
    Profit_: float
    Loss_: float
    Delta: float
    Gamma: float
    IV_Used: float
    Lot_Size: int

class SelectedContract(BaseModel):
    Strike: float
    Lots: int
    Entry_Price: float
    Target_Price: float
    SL_Price: float
    Total_Reward: float
    Total_Risk: float
    Total_Cost: float

class AnalysisResponse(BaseModel):
    projections: List[Projection]
    selected_contracts: List[SelectedContract]

# --- Models for Authentication ---

class User(BaseModel):
    id: Optional[str] = None # Firebase UID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str # This is your backend's JWT
    token_type: str = "bearer"
    user: User