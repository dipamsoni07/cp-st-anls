from datetime import datetime
from pydantic import BaseModel

# Candle
class Candle(BaseModel):
    timestamp : datetime
    open: float
    high: float
    low: float
    close: float
    volume: int