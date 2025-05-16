import asyncio
from datetime import datetime

from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.shared_data import precise_indicator_data 
# 
from src.algorithm import get_logger
from src.algorithm.pipelines.data_fetcher import DataFetcher
from src.algorithm.pipelines.data_preprocessor import DataPreprocessor
from src.algorithm.pipelines.indicator_pipeline import IndicatorPipeline
# 
from src.algorithm.tools.ema import EMA
from src.algorithm.tools.vwap import VWAP
from src.algorithm.algo_core.algo import Algorithm
from src.algorithm.core.order_manager import ORDER_MANAGER
from src.algorithm.core.signal_based_order_manager import SignalBasedOrderManager


class StockProcessor:
    """_summary_
    """
    
    def __init__(self,
                 isin:str,
                 fetcher:DataFetcher,
                 order_manager:ORDER_MANAGER,
                 quantity: int):
        """Initialize the StockProcessor Module to execute the algorithm along with order manager.
        
        :param isin(str): Enter an Stock ISIN Number (e.g., 'INE121J01017').
        :param fetcher(DataFetcher): Pass an Instance of DataFetcher Module.
        :param order_manager(ORDER_MANAGER): Pass an Instance of ORDER_MANAGER Module.
        :param quantity(int): Enter the number of Shares (quantity) in integers.
        """
        
        self.isin = isin
        self.fetcher = fetcher
        self.order_manager = order_manager
        self.quantity = quantity
        self.logger = get_logger(__name__, isin=isin)
        self.preprocessor = DataPreprocessor()
        self.pipeline = IndicatorPipeline(isin=isin)
        # Indicators Instances add...
        self.ema9 = EMA(period=9) 
        self.ema20 = EMA(period=20) 
        self.vwap = VWAP()
        # Pass the indicators to pipeline...
        self.pipeline.add_indicator("EMA9", self.ema9)
        self.pipeline.add_indicator("EMA20", self.ema20)
        self.pipeline.add_indicator("VWAP", self.vwap)
        # Initialize all the Major Queues (Common Resources)
        self.candle_queue = asyncio.Queue()
        self.ltpc_queue = asyncio.Queue()
        self.algo_ltpc_queue = asyncio.Queue()
        self.indicator_queue = asyncio.Queue()
        self.trade_signal_queue = asyncio.Queue()
        # Initialize an Algorithm & SignalBasedOrderManager
        self.algo:Algorithm = None
        # self.algo = Algorithm(
        #     algo_ltpc_queue=self.algo_ltpc_queue,
        #     indicator_queue=self.indicator_queue,
        #     trade_signal_queue=self.trade_signal_queue,
        #     isin = self.isin,
        # )
        # 
        self.signal_manager = SignalBasedOrderManager(
            order_manager = self.order_manager,
            signal_queue = self.trade_signal_queue,
            default_quantity = self.quantity,
        )
        
    # async def initialize(self, date:str):
    async def initialize(self):
        """Initialize with historical and intraday data.
        """
        date = date = datetime.now().strftime('%Y-%m-%d') 
        # Historical Data Fetch & Preprocess:
        historical_candles = self.fetcher.get_historical_data(ISIN=self.isin, date=date)
        self.preprocessor.convert_to_5min_candles(historical_candles[:375]) # Converting previous day's one min candles only
        self.pipeline.initialize_indicators(self.preprocessor.five_min_candles) # Initialize Indicators
        if historical_candles and self.preprocessor.five_min_candles: 
            self.logger.info(f"Fetched and Preprocessed Historical Stock Data for {self.isin}.")
        # Intraday Data Fetch & Preprocess:
        intraday_candles = self.fetcher.get_intraday_data(ISIN=self.isin)
        if intraday_candles:
            self.logger.info(f"Fetched preceeding indraday data for {self.isin}")
        self.preprocessor.convert_to_5min_candles(intraday_candles)
        self.preprocessor.five_min_candles = self.preprocessor.five_min_candles[75:] # Removing Previous day's 5 mins candles...
        for candle in self.preprocessor.five_min_candles:
            self.pipeline.update_all(candle) # Update all the indicators
        
        first_candle = None
        if self.preprocessor.five_min_candles or len(self.preprocessor.five_min_candles) > 0:
            first_candle = self.preprocessor.five_min_candles[0] if (self.preprocessor.five_min_candles[0].timestamp.hour == 9 and self.preprocessor.five_min_candles[0].timestamp.minute == 15) else self.preprocessor.five_min_candles[-1]

        # Push Initial Indicator Values...
        if self.ema9.current_value and self.ema20.current_value and self.vwap.current_value:
            await self.indicator_queue.put(
                precise_indicator_data(
                    timestamp=self.preprocessor.five_min_candles[-1].timestamp,
                    ema9=self.ema9.current_value.value,
                    ema20=self.ema20.current_value.value,
                    vwap=self.vwap.current_value.value,
                    #todo volume = first_candle.volume
                )
            )
        self.algo = Algorithm(
            algo_ltpc_queue=self.algo_ltpc_queue,
            indicator_queue=self.indicator_queue,
            trade_signal_queue=self.trade_signal_queue,
            isin = self.isin,
            first_candle= first_candle
        )
        
    async def process_candles(self):
        """Processes incoming 1-min candles and Handle 5-min candles update. (task-2)"""

        while True:
            candle:Candle = await self.candle_queue.get()
            five_min_candle:Candle = self.preprocessor.update_with_realtime_data(candle)
            if five_min_candle:
                self.pipeline.update_all(five_min_candle)
                
                if self.preprocessor.current_5min_candle and self.vwap.current_value and self.ema9.current_value and self.ema20.current_value:
                    #todo curr_volume = five_min_candle.volume
                    await self.indicator_queue.put(
                        precise_indicator_data(
                            timestamp=five_min_candle.timestamp,
                            ema9=self.ema9.current_value.value,
                            ema20=self.ema20.current_value.value,
                            vwap=self.vwap.current_value.value
                            #todo volume= curr_volume,
                        )
                    )
                
            # estimates = (vwap one min calculations with one min candle...)
        
        
    async def process_ltpc(self):
        """Process incoming LTPC data & Handle real-time LTP updates without any delay."""
        
        while True:
            ltpc:LTPC = await self.ltpc_queue.get()
            # estimates = (ema calculations with ltpc data...)
            # await self.algo.get_realtime_tradesignal()
            if ltpc:
                await self.algo_ltpc_queue.put(ltpc)
    
    async def run(self):
        """Start DataFetcher & Processing Tasks."""
        
        # Stock Subscribe & Data ingestion into the Queue after fetching...
        if self.fetcher.market_status == "NORMAL_OPEN":
            await self.fetcher.subscribe(
                instrument_key=f"NSE_EQ|{self.isin}",
                candle_queue=self.candle_queue,
                ltpc_queue=self.ltpc_queue
            )
        
        return [
            asyncio.create_task(self.process_candles()),
            asyncio.create_task(self.process_ltpc()),
            asyncio.create_task(self.algo.get_realtime_tradesignal()),
            asyncio.create_task(self.signal_manager.start_monitoring(isin=self.isin)),
        ]
                