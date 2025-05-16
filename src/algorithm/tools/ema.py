from datetime import datetime, timedelta, timezone
from typing import List, Optional
#
from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.indicators import IndicatorModel
#
from src.algorithm.tools.indicator import Indicator


class EMA(Indicator):
    """EXPONENTIAL MOVING AVERAGE @ Close.
    A class to calculate EMA values of "N" periods for the 5 minutes of the chart data. 

    Attributes:
        period (int): period of EMA (e.g., 9 ema, 20 ema)
        alpha (float): multiplier / α, also known as smoothening factor (formula: 2 / period+1)
        previous_ema (float): Storing previous ema value to calculate the current ema value
        
    Methods:
        ...

    """
    
    def __init__(self, period:int, smoothening_factor: int = None):
        super().__init__()
        self.period = period
        self.alpha = 2 / ( (period if smoothening_factor is None else smoothening_factor) + 1)
        self.previous_ema: Optional[float] = None
    
    def initialize_ema_with_history(self, historical_candles: List[Candle]):
        """Initializing EMA 0 value (initial value for EMA).
        Here we are using Simple Moving Average of last N (period) candles' close price of the previous day [strictly].

        Args:
            historical_candles (List[Candle]): Previous Day's 5-minute all candles.

        Raises:
            ValueError: _description_
        """


        if len(historical_candles) < self.period:
            raise ValueError(f"Not enough historical data for the given EMA period {self.period}")
        
        #! BUG FIX: to add condition to check for order of the candles before trimming the values.
        SMA:float = sum(candle.close for candle in historical_candles[-self.period:]) / self.period
        
        # initializing EMA value [EMA 0]
        self.previous_ema = SMA 
        self.save_value(SMA, historical_candles[-1].timestamp)
                    
    def update(self, candle:Candle):
        """Calculate EMA using the closing price of the 5-minute candles."""
        current_ema: Optional[float] = None
        
        if self.previous_ema is None:
            raise ValueError(f"Initial EMA not initialized, use initialize_ema_with_history(historical_candles:List(Candle)) method to initialize.")
        else:
            current_ema = (self.alpha * candle.close) + ((1 - self.alpha)*(self.previous_ema))

        self.previous_ema = current_ema
        self.save_value(self.previous_ema, candle.timestamp)


    def estimate(self, ltpc: LTPC = None):
        """Estimate EMA values (in-between) using real-time ltp values."""

        ltp = ltpc.ltp
        
        if self.previous_ema is None or ltp is None:
            return 0.0
        
        estimated_ema = (self.alpha * ltp) + ((1 - self.alpha)*(self.previous_ema))

        return estimated_ema
        # return IndicatorModel(
        #     value=estimated_ema,
        #     timestamp=ltt
        # )
    