from typing import List, Optional

from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.indicators import IndicatorModel

from src.algorithm.tools.indicator import Indicator


class MACD_Line(Indicator):
    """_summary_

    Args:
        Indicator (_type_): _description_
    """
    
    
    def __init__(self):
        super().__init__()
        
    
    def update(self, candle: Candle):
        """"""
        pass
    
    def estimate(self, ltpc: LTPC = None):
        """"""
        pass


class Signal_Line(Indicator):
    """_summary_

    Args:
        Indicator (_type_): _description_
    """
    
    
    def __init__(self):
        super().__init__()
        
    
    def update(self, candle: Candle):
        """"""
        pass
    
    def estimate(self, ltpc: LTPC = None):
        """"""
        pass
        

