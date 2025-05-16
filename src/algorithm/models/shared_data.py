from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.indicators import IndicatorModel
from src.algorithm.models.trade_signals import SIGNAL
    

#! Temporarily Using for Queuing Data:
class precise_indicator_data(BaseModel):
    timestamp: datetime
    vwap: float
    ema9: float
    ema20: float
    #todo volume: int  

class estimated_vwap(BaseModel):
    timestamp: datetime
    estimated_vwap: float
    
class estimated_ema(BaseModel):
    timestamp: datetime
    estimated_ema9: float
    estimated_ema20: float

class SharedData(BaseModel):
    one_min_candles: Optional[List[Candle]] = []
    five_min_candles: Optional[List[Candle]] = []
    ema9: List[IndicatorModel] = []
    ema20: List[IndicatorModel] = []
    vwap: List[IndicatorModel] = []
    trade_signals: List[SIGNAL] = []
    ltpc_data_window: List[LTPC] = []