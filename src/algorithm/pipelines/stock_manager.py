import asyncio
from typing import Dict, List
from src.algorithm.pipelines.data_fetcher import DataFetcher
from src.algorithm.pipelines.stock_processor import StockProcessor
from src.algorithm.core.order_manager import ORDER_MANAGER
from src.algorithm import get_logger

class StockManager:
    
    def __init__(self, access_token:str):
        self.fetcher = DataFetcher(access_token=access_token)
        self.order_manager = ORDER_MANAGER(access_token=access_token)    
        self.processors:Dict[str, StockProcessor] = {} # New task tree for each stock selected...
        self.tasks:List[asyncio.Task] = []
        self.logger = get_logger(__name__)
        
    
    async def add_stock(self, isin:str, quantity:int):
        """Add a stock for algo-monitoring.
        
        :param isin(str): Enter an Stock ISIN Number (e.g., 'INE121J01017').
        :param quantity(int): Enter the number of Shares (quantity) in integer.
        :param date(str): Enter 'date' in 'YYYY-MM-DD' format.
        """
        if isin not in self.processors:
            processor = StockProcessor(
                isin=isin,
                fetcher=self.fetcher,
                order_manager=self.order_manager,
                quantity=quantity
            )
            self.processors[isin] = processor
            await processor.initialize()
            self.logger.info(f"Initialized StockProcessor Task: {isin} | {quantity} Shares")
            self.tasks.extend(await processor.run())

    async def remove_stock(self, isin:str):
        """Removing a stock from algo-monitoring and deleing it's data.
        
        :param isin(str): Enter an Stock ISIN Number (e.g., 'INE121J01017').
        """
        if isin in self.processors:
            await self.processors[isin].signal_manager.stop_monitoring()
            
            await self.fetcher.unsubscribe(instrument_key=f"NSE_EQ|{isin}")
            self.logger.info(f"Stopped Signal Monitoring & StockProcessor task for instrument: {isin}")
            del self.processors[isin]
    
    async def run(self):
        """Start the websocket task and other all automation tasks."""
        self.logger.info(f"Starting Stock Manager... <add_stock> <remove_stock>")
        websocket_task = asyncio.create_task(self.fetcher.start_websocket()) #p1
        await asyncio.gather(websocket_task, *self.tasks)
        self.logger.info(f"Gathering all tasks: websocket_task, and other 4 StockProcessor's tasks.")
    