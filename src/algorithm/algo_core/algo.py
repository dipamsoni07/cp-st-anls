import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
# 
from src.algorithm import get_logger
from src.algorithm.models.candle import Candle
from src.algorithm.models.ltpc import LTPC
from src.algorithm.models.trade_signals import SIGNAL
from src.algorithm.models.indicators import IndicatorModel
from src.algorithm.models.shared_data import precise_indicator_data

# logger = get_logger(__name__)

class LevelPlotters:
    def __init__(self, percentage_change: float):
        self.t0: float = None
        self.timestamp: datetime = None
        self.percentage_change = percentage_change
        self.threshold_idx = 1 # AP series initial value (n)
        self.levels: Dict = None

    def get_n_levels(self,number_of_levels: int = 5, BUY_SIGNAL: SIGNAL = None ):
        T:List = []
        
        if BUY_SIGNAL:
            self.t0 = BUY_SIGNAL.value
            for i in range(number_of_levels):
                tn = self.t0 * (1 + self.percentage_change*self.threshold_idx / 100)
                T.append(
                    {
                        "level": self.threshold_idx,
                        "value": tn,
                        "timestamp": BUY_SIGNAL.timestamp
                    }
                )
                
                if self.threshold_idx == 2:
                    T.append(
                        {
                            "level": -1*self.threshold_idx,
                            "value": self.t0 * (1- self.percentage_change*self.threshold_idx / 100),
                            "timestamp": BUY_SIGNAL.timestamp
                        }
                    )
                self.threshold_idx += 1
            self.threshold_idx = 1
        
        return T
    

class Algorithm:
    
    def __init__(
        self,
        algo_ltpc_queue: asyncio.Queue = None,
        indicator_queue: asyncio.Queue = None,
        trade_signal_queue: asyncio.Queue = None,
        isin:str = None,
        first_candle: Candle = None
    ):
        # self.
        self.algo_ltpc_queue = algo_ltpc_queue
        self.indicator_queue = indicator_queue
        self.trade_signal_queue = trade_signal_queue
        self.latest_indicator: Optional[precise_indicator_data] = None
        self.position_open: bool = False # Flag indicating to check whether a BUY is triggered or not
        self.trade_signal_hitory: List[SIGNAL] = []
        self._tasks = [] 
        self.logger = get_logger(__name__, isin=isin)
        self.t0: Optional[float] = None
        self.percentange_change: Optional[float] = None
        self.level_plotters = LevelPlotters(percentage_change=1)
        self.latest_buy_signal: SIGNAL = None
        self.profit_booking_levels: List = []
        self.first_candle: Candle = first_candle
        #todo self.curr_volume: int = first_candle.volume
    
    async def indicator_consumer(self):
        """Take Input from indicator queue and updating latest indicator to compare with ltpc data."""
        while True:
            indicator_data:precise_indicator_data= await self.indicator_queue.get()
            self.latest_indicator = indicator_data
            #todo self.curr_volume = max(indicator_data.volume, self.curr_volume) 
            self.logger.info(f"""[Indicators] Updated indicators: {self.latest_indicator.timestamp.strftime('%Y-%m-%d %H:%M:%S:%f')}     
                             VWAP:  {self.latest_indicator.vwap}/-
                             EMA9:  {self.latest_indicator.ema9}/-
                             EMA20: {self.latest_indicator.ema20}/-""")
            self.indicator_queue.task_done()
    
    async def algo_ltpc_consumer(self):
        """Take Real-Time LTPC data input from ltpc queue and compute a trade signal."""
        while True:
            ltpc_data = await self.algo_ltpc_queue.get()
            if self.latest_indicator is not None:
                signal = self.compute_trade_signal(indicator_data=self.latest_indicator, ltpc_data=ltpc_data)
                await self.trade_signal_queue.put(signal)
                self.trade_signal_hitory.append(signal)
                self.logger.info(f"Trade Signal: [{signal.signal}] | LTP: {signal.value} | {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S:%f')}")
            else:
                self.logger.info("[LTP] No indicator available ATM. Skipping tick.")
            self.algo_ltpc_queue.task_done()
    
    def compute_trade_signal(self, indicator_data:precise_indicator_data, ltpc_data: LTPC = None, candle_data: Candle = None) -> SIGNAL:
        """_summary_

        Args:
            ltpc_data (LTPC): _description_
            indicator_data (_type_): _description_

        Returns:
            SIGNAL: _description_
        """
        if candle_data is not None:
            ltp = candle_data.close
            ltt = candle_data.timestamp
        elif ltpc_data is not None:
            ltp = ltpc_data.ltp
            ltt = ltpc_data.ltt
        else:
            return None
        
        # Collect all the indicator values here...
        vwap = indicator_data.vwap
        ema9 = indicator_data.ema9
        ema20 = indicator_data.ema20
            
        # NOT Uploading the logic for privacy reasons...
        # Example usage as follow
        
        trade_signal = "WAIT" 
        #! Four Kind of Trade Signals as follow:
        # "BUY"  
        # "SELL"
        # "HOLD": if either of buy/sell triggered than algorithm will HOLD the value.
        # "WAIT": if no buy/sell triggered than algorithm will WAIT for trigger.
        
        return SIGNAL(
            signal=trade_signal,
            value=ltp,
            timestamp=ltt,
            levels=self.profit_booking_levels
        )
        
    
    async def get_realtime_tradesignal(self):
        """_summary_
        """
        
        self._tasks = [
            asyncio.create_task(self.indicator_consumer()),
            asyncio.create_task(self.algo_ltpc_consumer()),
        ]
        
        await asyncio.gather(*self._tasks)
        
    def backtest_signal_on_historical_data(
        self,
        one_min_candles: Optional[List[Candle]] = None,
        five_min_candles: Optional[List[Candle]] = None,
        indicators: List[precise_indicator_data] = None
    ) -> List[SIGNAL]:
        """_summary_

        Args:
            five_min_candles (List[Candle]): _description_

        Returns:
            List[SIGNAL]: _description_
        """
        self.position_open = False
        historical_signals = []
        
        if one_min_candles:
            
            for i, candle in enumerate(one_min_candles):
                indicator_idx = i // 5 
                if indicators is not None and indicator_idx < len(indicators):
                    indicator = indicators[indicator_idx]
                    signal = self.compute_trade_signal(candle_data=candle, indicator_data=indicator)
                    historical_signals.append(signal)
                else:
                    break
                
        elif five_min_candles:

            for candle, indicator in zip(five_min_candles, indicators):
                signal = self.compute_trade_signal(indicator_data=indicator, candle_data=candle)
                historical_signals.append(signal)
                self.logger.info(f"[Historical] at Price : {candle.close}, Signal: {signal.signal}, Indicator: {indicator}") 
        
        self.trade_signal_hitory.extend(historical_signals)
        
        return historical_signals
        
        


#todo USAGE:

# async def main():
#     algo_ltpc_queue = asyncio.Queue()
#     indicator_queue = asyncio.Queue()
#     trade_signal_queue = asyncio.Queue()

#     algo = Algorithm(algo_ltpc_queue=algo_ltpc_queue,
#                  indicator_queue=indicator_queue,
#                  trade_signal_queue=trade_signal_queue)

#     await asyncio.gather(
#         # p2 | process_candles (indicators)
#         # p3 | ltpc_process
#         algo.get_realtime_tradesignal(),
#     )
    
# if __name__ == "__main__":
#     asyncio.run(main())



        

        

