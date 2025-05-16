import asyncio
import json
import ssl
import websockets
import socket
import requests
from google.protobuf.json_format import MessageToDict


from datetime import datetime, timedelta, timezone
from collections import deque
from typing import List, Optional, Dict
import src.algorithm.pipelines.MarketDataFeedV3_pb2 as pb

from src.algorithm import get_logger
from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC



class DataFetcher:
    """Fetches the Historical Market Data, Intraday Market Data, and Real-Time Market Feed."""

    def __init__(self, access_token: str):
        """
        Initialize DataFetcher with API credentials.
        
        Args:
            access_token (str): The access token for API and websocket authorization, can be generated via upstox sandbox after creating an account.        
        """
        self.access_token = access_token
        self.isin = None
        self.headers = {
            "Accept": 'application/json',
            "Authorization": f"Bearer {self.access_token}"
        }
        
        self.subscribed_instruments: set = set()
        self.candle_queues: Dict[str, asyncio.Queue] = {}
        self.ltpc_queues: Dict[str, asyncio.Queue] = {}
        self.websocket = None
        self.market_status = "NORMAL_CLOSE"
        self.last_ltpc_timestamp: Optional[datetime] = None
        self.last_candle_timestamp: Optional[datetime] = None
        self.logger = get_logger(__name__)
    
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
        
        # ! --------- Historical Data [All previous days...] ---------
        # req_url = f"https://api.upstox.com/v2/historical-candle/{exchange}_{index_type}%7C{ISIN}/1minute/{date}"
        
        req_url = f"https://api.upstox.com/v2/historical-candle/{exchange}_{index_type}%7C{ISIN}/1minute/{date}"
        self.isin = ISIN
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
    
    async def subscribe(self,
                        instrument_key:str,
                        candle_queue:asyncio.Queue,
                        ltpc_queue:asyncio.Queue):
        """Subscribe to real-tiime data for particular instrument/s (stock/s)
        
        :param instrument_key(str): Enter an Instrument Key (str) (e.g., 'NSE_EQ|INE121J01017')
        :param candle_queue(asyncio.Queue): Pass a candle queue instance to store the candle data.
        :param ltpc_queue(asyncio.Queue): Pass a ltpc queue instance to store the ltpc data.
        """

        if instrument_key not in self.subscribed_instruments and self.websocket:
            self.subscribed_instruments.add(instrument_key)
            self.candle_queues[instrument_key] = candle_queue
            self.ltpc_queues[instrument_key] = ltpc_queue
            
            subscription_data = {
                    "guid": "subscription",
                    "method": "sub",
                    "data": {
                        "mode" : "full",
                        "instrumentKeys": list(self.subscribed_instruments)
                    }
                }
            bin_sub_data = json.dumps(subscription_data).encode('utf-8')
            await self.websocket.send(bin_sub_data)
            self.logger.info(f"Subscribed to {instrument_key}")
            
    async def unsubscribe(self,
                          instrument_key:str):
        """Unsubscribe from an instrument's real-time data.
        
        :param instrument_key(str): Enter an Instrument Key (str) (e.g., 'NSE_EQ|INE121J01017')
        """
        if instrument_key in self.subscribed_instruments and self.websocket:
            self.subscribed_instruments.remove(instrument_key)
            
            unsub_data = {
                "guid": "re-subscription",
                "method": "sub",
                "data": {
                    "mode" : "full",
                    "instrumentKeys": list(self.subscribed_instruments)
                }
            }
            bin_unsub_data = json.dumps(unsub_data).encode('utf-8')
            await self.websocket.send(bin_unsub_data)
            del self.candle_queues[instrument_key]
            del self.ltpc_queues[instrument_key]
            self.logger.info(f"Unsubscribed from {instrument_key}")
        
    async def start_websocket(self):
        """Start WebSocket to stream real-time ltp, volume, and OHLC 1-minute data."""

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        #* NEW BRANCH - data_fetcher_ws_reconnection
        
        auth_response = self.get_market_data_feed_authorize_v3()
        ws_uri = auth_response['data']['authorized_redirect_uri']
        retries = 0
        while True:
            try:
                # Create websocket connection:
                async with websockets.connect(ws_uri, ssl = ssl_context) as websocket:
                    self.websocket = websocket
                    self.logger.info("Upstox webSocket connection established...")
                    await asyncio.sleep(0.5)
            
                    first_message = await websocket.recv()
                    decoded_data = self.decode_protobuf(first_message)
                    data_dict = MessageToDict(decoded_data)
            
                    if "marketInfo" in data_dict:
                        market_segment = "NSE_EQ"
                        if data_dict["marketInfo"]["segmentStatus"][market_segment] == "NORMAL_OPEN":
                            self.market_status = "NORMAL_OPEN"
                        else:
                            self.market_status = "NORMAL_CLOSE"                

            
                    if self.market_status == "NORMAL_CLOSE":
                        self.logger.info("Market is closed! Real-Time feed not available ATM.")
                        return

                    # Resubscribe to all previously subscribed instruments (again... upon retrying)
                    if self.subscribed_instruments and retries > 0:
                        subscription_data = {
                            "guid": "re-subscription",
                            "method": "sub",
                            "data": {
                                "mode": "full",
                                "instrumentKeys": list(self.subscribed_instruments)
                            }
                        }
                        bin_sub_data = json.dumps(subscription_data).encode('utf-8')
                        await websocket.send(bin_sub_data)
                        self.logger.info(f"Re-subscribed to instruments: {self.subscribed_instruments}")
                
                    self.logger.info("Market is open. Starting real-time data processing.")
                
                    while True:
                        message = await websocket.recv()
                        decoded_data = self.decode_protobuf(message)
                        data_dict = MessageToDict(decoded_data)
                        feeds: Dict = data_dict.get("feeds", {})
                    
                        for instrument_key in self.subscribed_instruments:
                            if instrument_key in feeds:
                                stock_data:Dict = feeds[instrument_key].get("fullFeed", {}).get("marketFF", {})
                            
                                #? 1) LTPC data:
                                if "ltpc" in stock_data:
                                    ltpc_dict = stock_data['ltpc']
                                    ts = self.convert_timestamp(ltpc_dict['ltt'])
                                
                                    if self.last_ltpc_timestamp is None or ts > self.last_ltpc_timestamp:
                                        ltpc = LTPC(
                                            ltp=float(ltpc_dict['ltp']),
                                            ltt=ts,
                                            ltq=int(ltpc_dict['ltq']),
                                            cp=float(ltpc_dict['cp']),
                                        )
                                        await self.ltpc_queues[instrument_key].put(ltpc)
                                        self.last_ltpc_timestamp = ts

                                #? 2) OHLC data:
                                if "marketOHLC" in stock_data:
                                    ohlc_list = stock_data["marketOHLC"]["ohlc"]
                                    for ohlc in ohlc_list:
                                        if ohlc["interval"] == "I1":
                                            ts = self.convert_timestamp(ohlc["ts"])
                                            if self.last_candle_timestamp is None or ts > self.last_candle_timestamp:
                                                candle = Candle(
                                                    timestamp=ts,
                                                    open=float(ohlc["open"]),
                                                    high=float(ohlc["high"]),
                                                    low=float(ohlc["low"]),
                                                    close=float(ohlc["close"]),
                                                    volume=int(ohlc["vol"])
                                                )
                                                await self.candle_queues[instrument_key].put(candle)
                                                self.last_candle_timestamp = ts 
                    
                                #? 3) BidAskQuotes:
                            
            except (websockets.ConnectionClosed, asyncio.TimeoutError, ConnectionRefusedError, socket.gaierror, OSError) as e:
                retries += 1
                delay = 5
                self.logger.warning(f"Websocket connection error: {e}. Reconnecting in {delay} seconds...")
                await asyncio.sleep(delay) # retries...
                
            except Exception as e:
                self.logger.error(f"Unexpected error in WebSocket connection: {e}")
                self.websocket = None # Reset Websocket reference
                break # loop exit (program closure...)
            
                
                        
    
    
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

