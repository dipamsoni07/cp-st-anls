import asyncio
import json
import ssl
import websockets
import requests
from google.protobuf.json_format import MessageToDict

import MarketDataFeedV3_pb2 as pb
# 
import logging
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import List, Optional
from pydantic import BaseModel
import threading
import upstox_client

# Config. [Logging]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
    
class Indicators(BaseModel):
    VWAP: float
    EMA9: float
    EMA20: float
    MACD_line: float
    signal_line: float
    volume_spike: bool
    # ave_volume_12: int
    


class DataFetcher:
    """
    ...
    
    Attributes:
    
    Methods:
    
    """
    
    def __init__(self, access_token: str):
        """
        Initialize DataFetcher with API credentials.
        
        Args:
            access_token (str): The access token for API and websocket authorization, can be generated via upstox sandbox after creating an account.        
        """

        self.access_token = access_token
        self.headers = {
            "Accept": 'application/json',
            "Authorization": f"Bearer {self.access_token}"
        }
        
        self.last_ltpc_timestamp: Optional[datetime] = None
        self.last_candle_timestamp: Optional[datetime] = None
    
    def get_historical_data(self, ISIN: str, date: str = None, exchange: str = "NSE", index_type: str = "EQ") -> List[Candle]:
        """Fetch 1-minute candles for a specific date from the historical API.

        Args:
            exchange (str): The stock exchange from which data is being fetched (e.g., 'NSE', 'BSE').
            index_type (str): The type of index or instrument category (e.g., 'EQ' for equity).
            ISIN (str): The ISIN number of the Stock (e.g., 'INE389H01022').
            date (str): The date in 'YYYY-MM-DD' format for which to fetch data.

        Returns:
            List[Candle]: A list of Candle Objects.
        
        Raises:
            ValueError: If the API request fails or the response indicates an error.
        """
        
        req_url = f"https://api.upstox.com/v2/historical-candle/{exchange}_{index_type}%7C{ISIN}/1minute/{date}/{date}"
        
        response = requests.get(req_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch historical data: {response.text}")    
        
        data = response.json()
        if data.get('status') != 'success':
            raise ValueError(f"Failed to fetch historical data: {data.get('message', 'Unknown error')}")
        
        candles = []
        for candle in data['data']['candles']:
            ts = datetime.strptime(candle[0], '%Y-%m-%dT%H:%M:%S%z')
            candles.append(
                Candle(
                    timestamp=ts,
                    # timestamp=candle[0],
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=int(candle[5]),
                )
            )
            
        return candles
    
    def get_intraday_data(self, ISIN: str, exchange: str = 'NSE', index_type: str = "EQ") -> List[Candle]:
        """Fetch intraday 1-minute candle data for the current day.

        Args:
            exchange (str): The stock exchange from which data is being fetched (e.g., 'NSE', 'BSE').
            index_type (str): The type of index or instrument category (e.g., 'EQ' for equity).
            ISIN (str): The ISIN number of the Stock (e.g., 'INE389H01022').

        Returns:
            List[Candle]: A list of Candle Objects.
        
        Raises:
            ValueError: If the API request fails or the response indicates an error.
        """
        
        req_url = f"https://api.upstox.com/v2/historical-candle/intraday/{exchange}_{index_type}%7C{ISIN}/1minute/"

        response = requests.get(req_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch intraday data: {response.text}")

        data = response.json()
        if data.get('status') != 'success':
            raise ValueError(f"Failed to fetch intraday data: {data.get('message', 'Unknown error')}")

        candles = []
        for candle in data['data']['candles']:
            ts = datetime.strptime(candle[0], '%Y-%m-%dT%H:%M:%S%z')
            candles.append(
                Candle(
                    timestamp=ts,
                    # timestamp=candle[0],
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=int(candle[5]),
                )
            )    
        
        return candles
    
    def get_market_data_feed_authorize_v3(self):
        """Authorize WebSocket connection using API v3."""

        auth_url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'
        response = requests.get(url=auth_url, headers=self.headers)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to authorize WebSocket: {response.text}")
        
        return response.json()
    
    
    async def start_websocket(self, ISIN: str, candle_queue: asyncio.Queue , ltpc_queue: asyncio.Queue, exchange: str = 'NSE', index_type: str = "EQ"):
        """Start WebSocket to stream real-time ltp, volume, and OHLC 1-minute data."""

        market_segment = f"{exchange}_{index_type}"
        instrument_key = f"{exchange}_{index_type}|{ISIN}" 
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        auth_response = self.get_market_data_feed_authorize_v3()
        ws_uri = auth_response['data']['authorized_redirect_uri']

        # Create websocket connection:
        async with websockets.connect(ws_uri, ssl = ssl_context) as websocket:
            logging.info("WebSocket connection established 🟢")
            await asyncio.sleep(1)
            
            # Subscribe to full mode data for the instrument
            
            subscription_data = {
                "guid": "someguid",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": [instrument_key]
                }
            }
            
            binary_sub_data = json.dumps(subscription_data).encode('utf-8')
            await websocket.send(binary_sub_data)

            # Market Open Status Check:
            first_message = await websocket.recv()
            decoded_data = self.decode_protobuf(first_message)
            data_dict = MessageToDict(decoded_data)
            
            market_status = "NORMAL_CLOSE"
            if "marketInfo" in data_dict:
                if data_dict["marketInfo"]["segmentStatus"][market_segment] == "NORMAL_OPEN":
                    market_status = "NORMAL_OPEN"
                
            if market_status == "NORMAL_CLOSE":
                print("Market is closed! Real-Time feed not available ATM")
                return

            if market_status == "NORMAL_OPEN":
                while True:
                    message = await websocket.recv()
                    decoded_data = self.decode_protobuf(message)
                    data_dict = MessageToDict(decoded_data)
                    
                    # MARKET FF [LTPC & marketOHLC Data]
                    stock_data = data_dict["feeds"][instrument_key]["fullFeed"]["marketFF"] 
                    
                    # Real-Time Tick-by-Tick incoming stock data fetching (e.g., ltp, ltt, ltq, volume, etc)
                    if "ltpc" in stock_data:
                        ltpc_dict = stock_data["ltpc"]
                        ts = self.convert_timestamp(ltpc_dict['ltt'])
                        
                        if ts > self.last_ltpc_timestamp or self.last_ltpc_timestamp is None:
                            ltpc = LTPC(
                                ltp=float(ltpc_dict['ltp']),
                                ltt=ts,
                                ltq=int(ltpc_dict["ltq"]),
                                cp=float(ltpc_dict["cp"])
                            )
                            await ltpc_queue.put(ltpc)
                            self.last_ltpc_timestamp = ts
                            
                    # To add candle based logic and collect the ltp and other values separately
                    if "marketOHLC" in stock_data:
                        ohlc_dict = stock_data["marketOHLC"]["ohlc"][1]
                        if ohlc_dict["interval"] == "I1":
                            ts = self.convert_timestamp(ohlc_dict["ts"])
                            
                            if ts > self.last_candle_timestamp or self.last_candle_timestamp is None:
                                candle = Candle(
                                    timestamp=ts,
                                    open=float(ohlc_dict["open"]),
                                    high=float(ohlc_dict["high"]),
                                    low=float(ohlc_dict["low"]),
                                    close=float(ohlc_dict["close"]),
                                    volume=int(ohlc_dict["volume"])
                                )
                            
                                await candle_queue.put(candle)
                                self.last_candle_timestamp = ts 
                        
                        
                    # Buy / Sell Information [For future!]
                
                
    
    
    @staticmethod
    def decode_protobuf(buffer):
        """Decode Protobuf message from WebSocket."""
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(buffer)
        return feed_response
    
    @staticmethod
    def convert_timestamp(ts):
        """Convert timestamp to datetime format (readable) | Use this function for websocket ts conversion..."""
        
        try:
            ist_offset = timedelta(hours=5, minutes=30)
            ts = datetime.fromtimestamp(int(ts)/1000, tz=timezone.utc)
            ts = ts.astimezone(timezone(ist_offset))
            return ts
        except Exception:
            return "Invalid Timestamp"
        
    

#! USAGE

async def main():
    access_token = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzSkM2TTQiLCJqdGkiOiI2N2RhN2RkZjZhYTU4MDUyMjNlOTMzNmMiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzQyMzcyMzE5LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NDI0MjE2MDB9.LcCevGC2dTRW4QzTMQ2f1bf539sYU3PqdtBsEuqX6W8"
    exchange = "NSE"
    index_type = "EQ"
    ISIN = "INE389H01022"
    
    fetcher = DataFetcher(access_token)
    candle_queue = asyncio.Queue()
    ltpc_queue = asyncio.Queue()

    # Websocket start to fetch real-time data:
    asyncio.create_task(fetcher.start_websocket(ISIN, 
                                                candle_queue=candle_queue,
                                                ltpc_queue=ltpc_queue
                                                ))
    
    
    # Process Historical Candle Data:
    print("Previous Day's Candles [1-min]:\n")
    prev_day_candles = fetcher.get_historical_data(ISIN, "2025-03-18")
    for candle in prev_day_candles:
        print(f"New 1-min Candle: {candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
    print("-"*50)
    
    # Process Historical Intrayday Data:
    print("Today's Intraday Candles Data")
    intraday_candles = fetcher.get_intraday_data(ISIN)
    for candle in intraday_candles:
        print(f"New 1-min Candle: {candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
    print("-"*50)
    
    
    # Convert Historical candles into 5 mins 
    # preprocessor.convert_to_5min_candles(sorted(prev_day_candles+intraday_candles, key = lambda c:c.timestamp))
    
    # Access to converted candles
    # preprocessor.five_min_candles
    
    # Process Real-Time Candle Data:
    async def process_candles():
        while True:
            candle = await candle_queue.get()
            
            print(f"New 1-min Candle: {candle.timestamp.day} | {candle.timestamp.hour}:{candle.timestamp.minute} | O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} | V:{float(candle.volume)/1000}K")
            
            # real-time to 5-min candle conversion:
            # five_min_candle = preprocessor.update_with_realtime_data(candle)
            # if five_min_candle:
                # Calculate requires indicators @ every 5 min intervals:
            # else:
                # Calculate Estimators (in between 5 min intervals of data here)
                 
            

    # Process LTPC Data: [Real-Time]
    async def process_ltpc():
        while True:
            ltpc = await ltpc_queue.get()
            print(f"LTP @ {ltpc.timesamp.day} |{ltpc.timestamp.hour}:{ltpc.timestamp.minute} | LTP: {ltpc.ltp}")


    await asyncio.gather(process_candles(), process_ltpc())
    

if __name__ == "__main__":
    asyncio.run(main())
