import asyncio
import datetime 
import json
import logging
from typing import List, Dict
from aiohttp import Payload
from pydantic import BaseModel
import requests
import upstox_client
from google.protobuf.json_format import MessageToDict

import MarketDataFeedV3_pb2 as pb

# Configure loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Models:

class Candle(BaseModel):
    timestamp : datetime.datetime
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
    
# Data Fetching Module:

class DataFetcher:
    def __init__(self, api_key: str, access_token:str):
        # self.upstox =  
        self.access_token = access_token
        self.ws_headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        self.hist_headers = {
            'Accept': 'application/json'
        }
        self.hist_payload = {}
        # url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'
        # api_response = requests.get(url=url, headers=self.headers)
        self.ws = None
        # pass
        
    def get_historical_data(self, instrument_key:str, date: str) -> List[Candle]:
        """Fetch historical 1-minute candle data for a specific date: here, generally previous day."""
        
        req_url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/1minute/{date}/{date}"
        response = requests.get(req_url, headers=self.hist_headers, data=self.hist_payload)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch historical data: {response.text}")
        
        data = response.json()
        if data.get('status') != 'success':
            raise ValueError(f"Failed to fetch historical data: {data.get("message", "Unknown Error")}")
        
        candles = []
        for candle in data['data']['candles']:
            ts = datetime.datetime.strptime(candle[0], '%Y-%m-%dT%H:%M:%S%z')
            candles.append(Candle(
                timestamp=ts,
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=int(candle[5])
            ))
        
        logging.info(f"Fetched {len(candles)} historical candles for {date}")
        return candles
    
    def get_intraday_data(self, instrument_key:str) -> List[Candle]:
        """Fetch intraday 1-minute candle data for the current trading day."""
        
        req_url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute"
        response = requests.get(req_url, headers=self.hist_headers, data=self.hist_payload)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch intraday data: {response.text}")
        
        data = response.json()
        if data.get('status') != 'success':
            raise ValueError(f"Failed to fetch intraday data: {data.get("message", "Unknown Error")}")
        
        candles = []
        for candle in data['data']['candles']:
            ts = datetime.datetime.strptime(candle[0], '%Y-%m-%dT%H:%M:%S%z')
            candles.append(Candle(
                timestamp=ts,
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=int(candle[5])
            ))
        
        logging.info(f"Fetched {len(candles)} intraday candles")
        return candles
    
    
    async def connect_websocket(self, instrument_key: str, callback):
        """Connect to Upstox Websocket & process a real-time data."""

        # web socket auth. & conn.
        
        # subscription msg.
        
        await asyncio.Future()



class DataPreprocessor:
    """Converting incoming 1 minute candle data into 5 minutes candle data"""
    
    def convert_to_5min(self, one_min_candles: List[Candle]) -> List[Candle]:
        """Converts existing candles data (from historical data)."""
        five_min_candles = []
        pass
    
    def update_5min_candle(self, five_min_candles: List[Candle], new_candle: Candle) -> List[Candle]:   
        """Updates Five minute candles with new 1-minute candle data."""
        pass


class Indicators:
    """Calculating all the indicator values."""

    def calculate_vwap(self, candles: List[Candle]) -> float:
        pass

    def calculate_ema(self, candles: List[Candle]) -> float:
        pass

    def calculate_macd(self, candles: List[Candle]) -> float:
        pass

    def calculate_volume_spike(self, candles: List[Candle]) -> float:
        pass
    







"""
Check this link consisting of the example file of github:
https://github.com/upstox/upstox-python/blob/master/examples/websocket/market_data/v3/websocket_client.py

refer this for websocket connection exactly...

And I want to perform this connection in such a way that the websocket connection occurs only for the one time (i.e. when user opens the app / run the code - later on real-time basis the subscription message can be altered based upon the stock selection by the user...


rest all things look good as of now make sure not a single minute data is skipped at all while switching occurs...
from intraday_candles to real-time (websocket based candles) and this thing will run in loop (and strictly the data should be captures at real-time and rounded figure : for instance in while collecting the data, seconds in time stamp should be :00 to :59 [value at the 00 second will be opening 

"""