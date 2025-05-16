from typing import List

from src.algorithm import get_logger
from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
#
from src.algorithm.tools.indicator import Indicator
from src.algorithm.tools.vwap import VWAP
from src.algorithm.tools.ema import EMA


class IndicatorPipeline:
    
    def __init__(self, isin:str=None):
        self.logger = get_logger(__name__, isin=isin)
        self.indicators = {}
        
    def add_indicator(self, name: str, indicator: Indicator):
        """Add an indicator to the pipeline."""
        self.indicators[name] = indicator
        
    def initialize_indicators(self, historical_candles: List[Candle]):
        for name, indicator in self.indicators.items():
            if isinstance(indicator, EMA):
                indicator.initialize_ema_with_history(historical_candles)
                self.logger.info(f"Initialized {name} with historical data: {indicator.current_value.value: .2f}")
    
    def update_all(self, candle:Candle):
        """Updates all indicators with the latest 5-minute candle."""
        for name, indicator in self.indicators.items():
            indicator.update(candle)
            self.logger.info(f"Updated {name}: {indicator.current_value.value} | {candle.timestamp}")
        
        self.logger.info(f"{'-'*100}")
            
    def estimate_all(self, ltpc: LTPC = None, one_min_candle: Candle = None):
        """Get real-time estimators for all indicators."""

        
        estimates = {}
        for name, indicator in self.indicators.items():
            if isinstance(indicator, EMA) and ltpc is not None:
                estimates[name] = indicator.estimate(ltpc=ltpc)
                self.logger.info(f"Estimated {name}: {estimates[name]}")
            elif isinstance(indicator, VWAP) and one_min_candle is not None:
                estimates[name] = indicator.estimate(one_min_candle=one_min_candle)
                self.logger.info(f"Estimated {name}: {estimates[name]}")
            # More Tools to add here in future...
        self.logger.info(f"{'-'*75}")
        return estimates
    
    def get_current_values(self):
        """Get the current values of all indicators."""

        return {
            name: indicator.current_value 
            for name, indicator in self.indicators.items()
        }
    