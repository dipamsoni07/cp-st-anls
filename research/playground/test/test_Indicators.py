import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from collections import deque
from pydantic import BaseModel
from abc import ABC, abstractmethod
import threading
import logging



# Models:
class Candle(BaseModel):
    timestamp : datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
# Real-Time Tick-by-Tick Data Model:
class LTPC(BaseModel):
    ltp: float      # Last Traded Price 
    ltt: datetime   # Last Traded Time
    ltq: int        # Last Traded Quantity
    cp: float       # Previous Close  
    
class IndicatorModel(BaseModel):
    value: float
    timestamp: datetime
    # indicator: str

# BASE INDICATOR CLASS [BLUEPRINT]:
class Indicator(ABC):
    def __init__(self):
        self.current_value: Optional[IndicatorModel] = None
        self.history: list[IndicatorModel] = []
        
    @abstractmethod
    def update(self, candle: Candle):
        """Update the indicator with the latest 5-minute candle data."""
        pass
    
    @abstractmethod
    def estimate(self, ltpc: float = None, one_min_candle: Candle = None):
        """Estimate the indicator value in real-time between intervals."""
        pass
    
    def save_value(self, value:float, timestamp: datetime):
        """Save the calculated or estimated value."""
        model = IndicatorModel(value=value, timestamp=timestamp)
        self.current_value = model
        self.history.append(model)
        
    def save_to_file(self, filename: str):
        with open(filename, 'w') as f:
            for entry in self.history:
                f.write(f"{entry.timestamp},{entry.value}\n")
                

#* TOOLS:

#? VWAP:

class VWAP(Indicator):
    """A class to calculate the Volume-Weighted Average Price using HCL3.
    

    Attributes:
        cumulative_price_volume (float)
        cumulative_volume (int)
    
    Methods:
        update(candle: Candle):
            Calculate VWAP using HLC3 of the 5-minute candle.
            
        estimate(one_min_candle: Candle) -> float:
            Estimate VWAP using the latest 1-minute candle.
    
    """
    
    def __init__(self):
        super().__init__()
        self.cumulative_price_volume = 0.0
        self.cumulative_volume = 0
        # 1-min in-between candles... 
        self.estimated_cumulative_price_volume = 0.0
        self.estimated_cumulative_volume = 0
        self.estimated_vwap_buffer = deque(maxlen=5)
        
    
    def update(self, candle: Candle):
        """Calculate VWAP using HLC3 of the 5-minute candle."""

        hlc3 = (candle.high + candle.low + candle.close) / 3
        price_volume = hlc3 * candle.volume
        
        # Σ
        self.cumulative_price_volume += price_volume
        self.cumulative_volume += candle.volume

        vwap_value = (self.cumulative_price_volume / self.cumulative_volume) if self.cumulative_volume != 0 else 0
        self.save_value(vwap_value, candle.timestamp)
        
    
    def estimate(self, one_min_candle: Candle = None):
        """Estimate VWAP using the latest 1-minute candle."""
        
        if self.current_value is None or one_min_candle is None:
            return 0.0
        
        
        hlc3 = (one_min_candle.high + one_min_candle.low + one_min_candle.close) / 3
        price_volume = hlc3 * one_min_candle.volume
        
        # Σ
        #! BUG Fix: This formula is only valid for suceeding 1-min candle after 5-min completion
        estimated_cumulative_price_volume = self.cumulative_price_volume + price_volume
        estimated_cumulative_volume = self.cumulative_volume + one_min_candle.volume
        
        estimated_vwap = (estimated_cumulative_price_volume / estimated_cumulative_volume) if estimated_cumulative_volume != 0 else 0
        return estimated_vwap
        

#? EMA:

class EMA(Indicator):
    """A class to calculate EMA values of "N" periods for the 5 minutes of the chart data. 

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
        SMA = sum(candle.close for candle in historical_candles[-self.period:]) / self.period
        
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


    def estimate(self, ltp: float = None):
        """Estimate EMA values (in-between) using real-time ltp values."""

        if self.previous_ema is None or ltp is None:
            return 0.0
        
        estimated_ema = (self.alpha * ltp) + ((1 - self.alpha)*(self.previous_ema))

        return estimated_ema
    
    

#* Indicator Pipeline:

class IndicatorPipeline:
    
    def __init__(self):
        self.indicators = {}
        
    def add_indicator(self, name: str, indicator: Indicator):
        """Add an indicator to the pipeline."""
        self.indicators[name] = indicator
        
    def initialize_indicator(self, historical_candles: List[Candle]):
        for name, indicator in self.indicators.items():
            if isinstance(indicator, EMA):
                indicator.initialize_ema_with_history(historical_candles)
                logging.info(f"Initialized {name} with historical data")
    
    def update_all(self, candle:Candle):
        """Updates all indicators with the latest 5-minute candle."""
        for name, indicator in self.indicators.items():
            indicator.update(candle)
            logging.info(f"Updated {name}: {indicator.current_value.value} @ {candle.timestamp}")
            
    def estimate_all(self, ltp: float = None, one_min_candle: Candle = None):
        """Get real-time estimators for all indicators."""

        estimates = {}
        for name, indicator in self.indicators.items():
            if isinstance(indicator, EMA):
                estimates[name] = indicator.estimate(ltp=ltp)
            elif isinstance(indicator, VWAP):
                estimates[name] = indicator.estimate(one_min_candle=one_min_candle)
            # More Tools to add here in future...
        
        return estimates
    
    def get_current_values(self):
        """Get the current values of all indicators."""

        return {
            name: indicator.current_value 
            for name, indicator in self.indicators.items()
        }
    