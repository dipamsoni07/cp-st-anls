# src/pipelines/data_fetcher.py

import asyncio
import json
import ssl
import websockets
import requests

from google.protobuf.json_format import MessageToDict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging

import websockets.connection

import MarketDataFeed_pb2 as pb
from pydantic import BaseModel

from algorithm.models import candle



logging.basicConfig(level=logging.INFO)

# LTPC 
class LTPC(BaseModel):
    ltp: float      # Last Traded Price 
    ltt: datetime   # Last Traded Time
    ltq: int        # Last Traded Quantity
    cp: float       # Previous Close    

class Candle(BaseModel):
    timestamp : datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    

class DataFetcher:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        self.subscribed_instruments: set = set()
        self.candle_queues:Dict[str, asyncio.Queue] = {}
        self.ltpc_queues:Dict[str, asyncio.Queue] = {}
        self.logger = logging.getLogger(__name__)
        self.websocket = None
        self.market_status = "NORMAL_CLOSE"
    
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
        """Subscribe to real-time data for an instrument"""
        
        if instrument_key not in self.subscribed_instruments and self.websocket:
            self.subscribed_instruments.add(instrument_key)
            self.candle_queues[instrument_key] = candle_queue
            self.ltpc_queues[instrument_key] = ltpc_queue
            
            # encode data before sending
            await self.websocket.send(json.dumps(
                {
                    "guid": "subscription",
                    "method": "sub",
                    "data": {
                        "mode": "full",
                        "instrumentKeys": [instrument_key]
                    }
                }
            ))
            
            self.logger.info(f"Subscribed to {instrument_key}")
            
    async def unsubscribe(self, instrument_key: str):
        """Unsubsrcibe from an instrument's real-time data."""
        if instrument_key in self.subscribed_instruments and self.websocket:
            self.subscribed_instruments.remove(instrument_key)
            await self.websocket.send(json.dumps({
                "guid": "unsubscription",
                "method": "unsub",
                "data": {
                    "instrumentKeys": [instrument_key]
                }
            }))
            del self.candle_queues[instrument_key]            
            del self.ltpc_queues[instrument_key]
            self.logger.info(f"Unsubscribed from {instrument_key}")

        
    async def start_websocket(self):
        """Start the websocket to stream real-time data for subscribed instruments."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        auth_response = self.get_market_data_feed_authorize_v3()
        ws_uri = auth_response['data']['authorized_redirect_uri']

        async with websockets.connect(ws_uri, ssl=ssl_context) as websocket:
            self.websocket = websocket
            self.logger.info("Upstox websocket connection established...")
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
                self.logger.info("Market is closed! Real-Time feed not available ATM")    
                return
            
            self.logger.info("Market is open. Starting real-time data processing.")
            while True:
                try:
                    message = await websocket.recv()
                    decoded_data = self.decode_protobuf(message)
                    data_dict = MessageToDict(decoded_data)

                    feeds:Dict = data_dict.get("feeds", {})
                    for instrument_key in self.subscribed_instruments:
                        if instrument_key in feeds:
                            stock_data:Dict = feeds[instrument_key].get("fullFeed", {}).get("marketFF", {})

                            if "ltpc" in stock_data:
                                ltpc_dict = stock_data["ltpc"]
                                ts = self.convert_timestamp(ltpc_dict["ltt"])
                                ltpc = LTPC(
                                    ltp=float(ltpc_dict["ltp"]),
                                    ltt=ts,
                                    ltq=int(ltpc_dict["ltq"]),
                                    cp = float(ltpc_dict["cp"])
                                )
                                await self.ltpc_queues[instrument_key].put(ltpc)

                            if "marketOHLC" in stock_data:
                                ohlc_list = stock_data["marketOHLC"]["ohlc"]
                                for ohlc in ohlc_list:
                                    if ohlc['interval'] == "I1":
                                        ts = self.convert_timestamp(ohlc["ts"])
                                        candle = Candle(
                                            timestamp=ts,
                                            open=float(ohlc["open"]),
                                            high=float(ohlc["high"]),
                                            low=float(ohlc["low"]),
                                            close=float(ohlc["close"]),
                                            volume=int(ohlc["vol"])
                                        )
                                        await self.candle_queues[instrument_key].put(candle)

                except Exception as e:
                    self.logger.error(f"Websocket error: {e}")
                    break
    
    @staticmethod
    def decode_protobuf(buffer):
        """Decode Protobuf message from WebSocket."""
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(buffer)
        return feed_response
    
    @staticmethod
    def convert_timestamp(ts):
        """Convert timestamp to datetime format (readable) | Use this function for websocket's ts conversion..."""
        try:
            ist_offset = timedelta(hour=5, minutes=30)
            ts  = datetime.fromtimestamp(int(ts)/1000, tz = timezone.utc)
            ts = ts.astimezone(timezone(ist_offset))
            return ts
        except Exception:
            raise ValueError("Invalid Timestamp")


            
#todo: src/algorithm/pipelines/stock_processor.py [NEW]
    
    
import asyncio

from src.algorithm import get_logger
# from src.algorithm.pipelines.data_fetcher import DataFetcher
from src.algorithm.pipelines.data_preprocessor import DataPreprocessor
from src.algorithm.pipelines.indicator_pipeline import IndicatorPipeline

from src.algorithm.tools.ema import EMA
from src.algorithm.tools.vwap import VWAP
from src.algorithm.algo_core.algo import Algorithm
from src.algorithm.core.order_manager import ORDER_MANAGER
from src.algorithm.core.signal_based_order_manager import SignalBasedOrderManager
from src.algorithm.models.shared_data import precise_indicator_data

class StockProcessor:
    def __init__(self,
                 isin:str,
                 fetcher:DataFetcher,
                 order_manager:ORDER_MANAGER,
                 quantity: int):
        
        self.isin = isin
        self.fetcher = fetcher
        self.order_manager = order_manager
        self.quantity = quantity
        self.logger = get_logger(f"StockProcessor-{isin}")
        self.preprocessor = DataPreprocessor()
        self.pipeline = IndicatorPipeline()
        # 
        self.ema9 = EMA(period=9)
        self.ema20 = EMA(period=20)
        self.vwap = VWAP()
        # 
        self.pipeline.add_indicator("EMA9", self.ema9)
        self.pipeline.add_indicator("EMA20", self.ema20)
        self.pipeline.add_indicator("VWAP", self.vwap)
        # 
        self.candle_queue = asyncio.Queue()
        self.ltpc_queue = asyncio.Queue() 
        self.indicator_queue = asyncio.Queue() 
        self.trade_signal_queue= asyncio.Queue() 
        # 
        self.algo = Algorithm(
            self.ltpc_queue,
            self.indicator_queue,
            self.trade_signal_queue
        )
        # 
        self.signal_manager = SignalBasedOrderManager(
            order_manager=self.order_manager,
            signal_queue=self.trade_signal_queue,
            default_quantity=self.quantity
        )
    
    async def initialize(self, date:str):
        """
        Initialize with historical and intraday data.
        
        :param date: Enter 'date' in 'YYYY-MM-DD' format.
        """
        
        historical_candles = self.fetcher.get_historical_data(ISIN=self.isin, date=date)
        self.preprocessor.convert_to_5min_candles(historical_candles[:375])     # Converting previous day's one min candles only
        self.pipeline.initialize_indicators(self.preprocessor.five_min_candles)     # Initializing indicators
        intraday_candles = self.fetcher.get_intraday_data(ISIN=self.isin)
        self.preprocessor.convert_to_5min_candles(intraday_candles)
        self.preprocessor.five_min_candles = self.preprocessor.five_min_candles[75:] # Removing Previous Day's 5 min candles...
        for candle in self.preprocessor.five_min_candles:
            self.pipeline.update_all(candle)
        
        await self.indicator_queue.put(
            precise_indicator_data(
                timestamp=self.preprocessor.five_min_candles[-1].timestamp,
                ema9=self.ema9.current_value.value,
                ema20=self.ema20.current_value.value,
                vwap=self.vwap.current_value.value
            )
        )

    async def process_candles(self):
        """Processes incoming  1-min candles and Handle 5-minute candles update."""

        while True:
            # try:
            candle:Candle = await self.candle_queue.get()
            five_min_candle:Candle = self.preprocessor.update_with_realtime_data(candle)
            if five_min_candle:
                self.pipeline.update_all(five_min_candle)
                
                if self.preprocessor.current_5min_candle and self.vwap.current_value and self.ema9.current_value:
                    await self.indicator_queue.put(
                        precise_indicator_data(
                            timestamp=five_min_candle.timestamp,
                            vwap=self.vwap.current_value.value,
                            ema9=self.ema9.current_value.value,
                            ema20=self.ema20.current_value.value
                        )
                    )
            # estimates calculation here...(vwap one min estimations...)
            # except Exception as e:

    async def process_ltpc(self):
        """Process incoming LTPC data & Handle real-time LTP updates without any delay."""

        while True:
            ltpc:LTPC = await self.ltpc_queue.get()
            # estimates calculation to be added in future... (ema estimations...)
            await self.algo.get_realtime_tradesignal()
    
    async def run(self):
        """Start Fetching & Processing Tasks."""
        
        # Data Ingestion into the Queue post fetching
        await self.fetcher.subscribe(
            instrument_key=f"NSE_EQ|{self.isin}",
            candle_queue=self.candle_queue,
            ltpc_queue=self.ltpc_queue
        )
        
        # Binding up all the tasks and return 'em
        return [
            asyncio.create_task(self.process_candles()),
            asyncio.create_task(self.process_ltpc()),
            asyncio.create_task(self.algo.get_realtime_tradesignal()),
            asyncio.create_task(self.signal_manager.start_monitoring(isin=self.isin))
        ]
        


#todo: src/algorithm/pipelines/stock_manager.py [NEW]
import asyncio
# from src.algorithm.pipelines.data_fetcher import DataFetcher
# from src.algorithm.pipelines.stock_processor import StockProcessor
from src.algorithm.core.order_manager import ORDER_MANAGER


class StockManager:
    
    def __init__(self, access_token:str):
        self.fetcher = DataFetcher(access_token=access_token)
        self.order_manager = ORDER_MANAGER(access_token)
        self.processors:Dict[str, StockProcessor] = {} # New task tree for each stock selected...
        self.tasks: List[asyncio.Task] = []
        
    
    async def add_stock(self, isin:str, quantity: int, date:str):
        """Add a stock for monitoring."""
        if isin not in self.processors:
            processor = StockProcessor(
                isin=isin,
                fetcher=self.fetcher,
                order_manager=self.order_manager,
                quantity=quantity
            )
            self.processors[isin] = processor
            await processor.initialize(date)
            self.tasks.extend(await processor.run())
    
    async def remove_stock(self, isin:str):
        """Remove a stock from monitoring."""
        if isin in self.processors:
            await self.fetcher.unsubscribe(instrument_key=f"NSE_EQ|{isin}")
            del self.processors[isin]
            # For production have to consider proper tasks cleanup...
    
    async def run(self):
        """Start the Websocket & Manager Tasks."""
        websocket_task = asyncio.create_task(self.fetcher.start_websocket()) #p1
        await asyncio.gather(websocket_task, *self.tasks)
        
        


#todo: src/algorithm/core/order_placement_queue.py [NEW]

# This handles the Order Placement Limits Precisely to avoid suspension.

import asyncio
from src.algorithm.core.order_manager import ORDER_MANAGER


class OrderPlacementQueue:
    def __init__(self,
                 order_manager: ORDER_MANAGER,
                 max_rate: int = 4):
        self.order_manager = order_manager
        self.queue = asyncio.Queue()
        self.max_rate = max_rate
        self.semaphore = asyncio.Semaphore(max_rate)
        asyncio.create_task(self.process_queue())
    
    async def place_order(self, order_data: dict):
        """Queue an order for placement."""
        await self.queue.put(order_data)
    
    async def process_queue(self):
        """Process queued orders with rate limiting."""
        while True:
            order_data = await self.queue.get()
            async with self.semaphore:
                await self.order_manager.place_new_intraday_order(**order_data)
            await asyncio.sleep(1 / self.max_rate)

#! todo: src/algorithm/core/signal_based_ordermanager.py ->
# Replace Direct calls to order_manager.place_new_intraday_order with order_placement_queue.place_order.


#todo: main.py:

import os
import asyncio
from dotenv import load_dotenv
from src.algorithm import get_logger
# from src.algorithm.pipelines import StockManager
# from src.algorithm.core.order_placement_queue import OrderPlacementQueue

logger = get_logger("main")

async def user_input_loop(stock_manager: StockManager):
    """Temprorary CLI for user interaction."""
    while True:
        cmd = input("Enter command (add <isin> <quantity>, remove <isin>, quit): ").split()
        if cmd[0].lower() == 'add' and len(cmd) == 3:
            await stock_manager.add_stock(cmd[1], int(cmd[2]), "2025-04-03")
        elif cmd[0].lower() == 'remove' and len(cmd) == 2:
            await stock_manager.remove_stock(cmd[1])
        elif cmd[0] == 'quit':
            break

async def main():
    load_dotenv()
    access_token = os.getenv('ACCESS_TOKEN')
    stock_manager = StockManager(access_token)
    order_queue = OrderPlacementQueue(stock_manager.order_manager)
    await stock_manager.add_stock(
        "INE389H01022",
        10,
        "2025-04-03"
    )
    await asyncio.gather(
        stock_manager.run(),
        order_queue.process_queue(),
        user_input_loop(stock_manager=stock_manager)
    )


if __name__ == "__main__":
    asyncio.run(main())