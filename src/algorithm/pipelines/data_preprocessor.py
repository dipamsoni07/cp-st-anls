from datetime import datetime
from typing import List, Optional, Dict
from collections import deque

from src.algorithm.models.candle import Candle


class DataPreprocessor:
    """
    A class for processing 1-minute candlestick data and aggregating it into 5-minute candlesticks.
    
    This class handles both historical data conversion and real-time updates as well. It maintains a queue of last five 1-minute candles and generates a new candle once an interval is completed.
    
    Attributes:
        five_min_candles (List[Candle]): Stores all completed 5-minutes candles.
        candle_queue (deque): A queue maintaining the last five 1-minute candles for real-time processing.
        current_5min_candle (Optional[Candle]): Tracks the current 5-minute candle being formed. [latest one]
        
    Methods:
        convert_to_5min_candles(one_min_candles: List[Candle]) -> None:
            Converts a list of 1-minute candles into 5-minute candles and updates storage.
        
        update_with_realtime_data(new_candle: Candle) -> Optional[Candle]:
            Processes a new 1-minute candle in real-time and returns a completed 5-minute candle if ready. If not ready than returns "None".
            
        _merge_candles(candles: List[Candle]) -> Candle:
            Logic that enable merging of five 1-minute consecutive candles into a single 5-minute candle by computing OPEN, HIGH, LOW, CLOSE, and VOLUME values by keeping track of timestamp.
    """
    
    
    
    def __init__(self):
        """Initialize with storage for all 5-min candles and a queue for real-time updates."""
        self.five_min_candles: List[Candle] = [] # All completed 5-min candles storage...
        self.candle_queue = deque(maxlen=5) # storing preceeding 5 one-min candles
        self.current_5min_candle: Optional[Candle] = None # curr. 5 min candle tracking
    
    def convert_to_5min_candles(self, one_min_candles: List[Candle]) -> List[Candle]:
        """Convert historical 1-min candles into 5-min candles."""
        
        buffer = []
        one_min_candles = sorted(one_min_candles, key=lambda candle:candle.timestamp)
        for candle in one_min_candles:
            buffer.append(candle)

            if len(buffer) == 5:
                merged_candle = self._merge_candles(buffer)
                if merged_candle:
                    self.five_min_candles.append(merged_candle)
                buffer = []
        
        # return five_min_candles
        # remaining buffer candles carry over to candle queue with real-time updates...
        self.candle_queue.extend(buffer)
    
    
    def update_with_realtime_data(self, new_candle: Candle) -> Optional[Candle]:
        """
        Process new 1-minute candle and return a completed 5-min candle if ready.
        - NOTE: Use this in real-time data loop : i.e.: websocket one
        """ 


        if len(self.candle_queue) == 0:
            self.candle_queue.append(new_candle)
        elif new_candle.timestamp != self.candle_queue[-1].timestamp:
                self.candle_queue.append(new_candle)  

        
        # check if new candle completes a 5-min interval
        if new_candle.timestamp.minute % 5 == 4 and len(self.candle_queue) == 5:
            self.current_5min_candle = self._merge_candles(list(self.candle_queue))
            if self.current_5min_candle:
                self.five_min_candles.append(self.current_5min_candle)
                # self.candle_queue.clear() # reset candle queue for next interval
                return self.current_5min_candle
        return None
           
    
    def _merge_candles(self, candles:List[Candle]) -> Candle:
        """Merge five 1-minute candles into a single 5-minute candle."""
 
        if not candles:
            return None
        
        return Candle(
            timestamp=candles[0].timestamp,
            open=candles[0].open,
            high=max(candle.high for candle in candles),
            low=min(candle.low for candle in candles),
            close=candles[-1].close,
            volume=sum(candle.volume for candle in candles)
        )
        
        

