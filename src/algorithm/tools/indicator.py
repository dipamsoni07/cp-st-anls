from datetime import datetime
from typing import List, Optional
from abc import ABC, abstractmethod

from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.indicators import IndicatorModel


class Indicator(ABC):
    """Base Class for all the indicators | Blueprint."""
    def __init__(self):
        self.current_value: Optional[IndicatorModel] = None
        self.history: list[IndicatorModel] = []
        
    @abstractmethod
    def update(self, candle: Candle):
        """Update the indicator with the latest 5-minute candle data."""
        pass
    
    @abstractmethod
    def estimate(self, ltpc: LTPC = None, one_min_candle: Candle = None):
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
                
                
