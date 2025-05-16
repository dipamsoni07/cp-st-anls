from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

# LTPC 
class LTPC(BaseModel):
    ltp: float      # Last Traded Price 
    ltt: datetime   # Last Traded Time
    ltq: int        # Last Traded Quantity
    cp: float       # Previous Close    
