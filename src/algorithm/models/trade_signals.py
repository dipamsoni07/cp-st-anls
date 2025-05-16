from typing import Literal, Optional, List
from pydantic import BaseModel
from datetime import datetime


class SIGNAL(BaseModel):
    signal: Literal["WAIT", "BUY", "HOLD", "SELL"] = None
    value: float
    timestamp: datetime
    levels: Optional[List] = []

