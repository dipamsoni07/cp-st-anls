from datetime import datetime, timedelta, timezone
from typing import List, Optional
from abc import ABC, abstractmethod
import logging
# 
from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.indicators import IndicatorModel
# 
from src.algorithm.tools.indicator import Indicator

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
        self.one_min_buffer: List[Candle] = []
    
    def update(self, candle: Candle):
        """Calculate VWAP using HLC3 of the 5-minute candle."""

        hlc3 = (candle.high + candle.low + candle.close) / 3
        price_volume = hlc3 * candle.volume
        
        # Σ
        self.cumulative_price_volume += price_volume
        self.cumulative_volume += candle.volume

        vwap_value = (self.cumulative_price_volume / self.cumulative_volume) if self.cumulative_volume != 0 else 0
        self.save_value(vwap_value, candle.timestamp)
        self.one_min_buffer.clear()
        
    
    def estimate(self, one_min_candle: Candle = None):
        """Estimate VWAP using the latest 1-minute candle."""
        
        if self.current_value is None or one_min_candle is None:
            return 0.0
        
        self.one_min_buffer.append(one_min_candle)
        
        buffer_price_volume = sum((candle.high + candle.low + candle.close) / 3 * candle.volume for candle in self.one_min_buffer)
        buffer_volume = sum(candle.volume for candle in self.one_min_buffer)
        # hlc3 = (one_min_candle.high + one_min_candle.low + one_min_candle.close) / 3
        # price_volume = hlc3 * one_min_candle.volume
        
        # Σ
        #! BUG Fix: This formula is only valid for suceeding 1-min candle after 5-min completion
        estimated_cumulative_price_volume = self.cumulative_price_volume + buffer_price_volume
        estimated_cumulative_volume = self.cumulative_volume + buffer_volume
        
        estimated_vwap = (estimated_cumulative_price_volume / estimated_cumulative_volume) if estimated_cumulative_volume != 0 else 0
        # estimated_cumulative_price_volume = self.cumulative_price_volume + price_volume
        # estimated_cumulative_volume = self.cumulative_volume + one_min_candle.volume
        
        # estimated_vwap = (estimated_cumulative_price_volume / estimated_cumulative_volume) if estimated_cumulative_volume != 0 else 0
        return estimated_vwap
        
