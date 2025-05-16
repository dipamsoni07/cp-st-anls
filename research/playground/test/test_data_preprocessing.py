import asyncio
from datetime import datetime
from collections import deque
import json
import logging
from os import times
from typing import List, Dict, Optional
from pydantic import BaseModel
import requests
import upstox_client
from google.protobuf.json_format import MessageToDict

import MarketDataFeedV3_pb2 as pb

# Sample ts conversions:
# print((datetime.fromisoformat("2025-03-13T15:45:59+05:30"[:-6]).minute % 5 == 0))
# datetime.utcfromtimestamp(int("1741285800000") / 1000).isoformat()

# Models
class Candle(BaseModel):
    timestamp : datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
class Indicators(BaseModel):
    VWAP: float
    EMA9: float
    EMA20: float
    MACD_line: float
    signal_line: float
    volume_spike: bool
    # ave_volume_12: int
    


# Data Preprocessor:

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
        
        



#! TESTING PIPELINE usage

import requests
req_url = f"https://api.upstox.com/v2/historical-candle/NSE_EQ%7CINE389H01022/1minute/2025-03-18/2025-03-18"
response = requests.get(req_url)
if response.status_code != 200:
    raise ValueError(f"Failed to fetch historical data: {response.text}")

data = response.json()
if data.get("status") != "success":
    raise ValueError(f"Failed to fetch historical data: {data.get('message', 'Unknown error')}")

historical_candles = []
for candle in data['data']['candles']:
    ts = datetime.strptime(candle[0], '%Y-%m-%dT%H:%M:%S%z')
    historical_candles.append(
        Candle(
            # timestamp=ts,
            timestamp=candle[0],
            open = float(candle[1]),
            high=float(candle[2]),
            low=float(candle[3]),
            close=float(candle[4]),
            volume=int(candle[5]),
        )
    )

# for candle in historical_candles:
#     print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
print(f"\n {'-'*75}")
    
    
    
# print(len(five_min_candles))

intraday_req_url = f"https://api.upstox.com/v2/historical-candle/intraday/NSE_EQ%7CINE389H01022/1minute/"
res_intra = requests.get(intraday_req_url)
intra_data = res_intra.json()
intra_candles = []
for candle in intra_data['data']['candles']:
    ts = datetime.strptime(candle[0], '%Y-%m-%dT%H:%M:%S%z')
    intra_candles.append(
        Candle(
            # timestamp=ts,
            timestamp=candle[0],
            open = float(candle[1]),
            high=float(candle[2]),
            low=float(candle[3]),
            close=float(candle[4]),
            volume=int(candle[5]),
        )
    )
    
    
# for candle in intra_candles:
#     print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
# print(f"\n {'-'*75}")



all_candles_past = sorted(historical_candles+intra_candles, key=lambda c:c.timestamp)
# for candle in [all_candles_past[-1]]:
#     print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")

print(f"\n {'-'*75}")

preprocessor = DataPreprocessor()

# print(len(all_candles_past))
preprocessor.convert_to_5min_candles(all_candles_past[:-1])
print(len(preprocessor.five_min_candles))


print("converted 5 minutes candles:")
for candle in preprocessor.five_min_candles:
    print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
    
print(f"\n{'-'*75}")
print("unconverted candles left in buffer:")
for candle in list(preprocessor.candle_queue):
    print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
    
print(f"\n{'-'*75}")
print("new 1 min candle")
new_candle = all_candles_past[-1]
for candle in [new_candle]:
    print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
print(f"\n{'-'*75}")


five_min_candle = preprocessor.update_with_realtime_data(new_candle)
if five_min_candle:
    print("New 5 minute candle formed")
    for candle in [five_min_candle]:
        print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
else:
    print("wait for 5 minutes timeframe to complete | and look candle queue below:")
print(f"\n{'-'*75}")

print("unconverted candles left in buffer after new candle addition:")
for candle in list(preprocessor.candle_queue):
    print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
print(f"\n{'-'*75}")
    
print("few latest converted 5 minutes candles:")
for candle in preprocessor.five_min_candles[-3:]:
    print(f"{candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
    
from datetime import datetime, timezone, timedelta
ts = "2025-03-18T15:07:00+05:30"
ts = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S%z')
# ts.minute
print(ts)

ts2 = "1742373997100"
ts2 = datetime.fromtimestamp(int(ts2)/1000, tz=timezone.utc)

ist_offset = timedelta(hours=5, minutes=30)
ts2 = ts2.astimezone(timezone(ist_offset))

print("ts2:", ts2)

ts3 = "1742373997241"
ts3 = datetime.fromtimestamp(int(ts3)/1000, tz=timezone.utc)
ts3 = ts3.astimezone(timezone(ist_offset))

print("ts3:", ts3)
print(max(ts2, ts3))