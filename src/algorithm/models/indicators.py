from pydantic import BaseModel
from datetime import datetime

class IndicatorModel(BaseModel):
    value: float
    timestamp: datetime
    # indicator: str
    
