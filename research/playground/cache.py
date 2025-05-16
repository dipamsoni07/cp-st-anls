import asyncio
import pytz
from datetime import datetime, timedelta
import logging

# 
from models.candle import Candle
from models.indicators import IndicatorModel
#
from pipelines.data_fetcher import DataFetcher
from pipelines.data_preprocessor import DataPreprocessor
from pipelines.indicator_pipeline import IndicatorPipeline
#
from tools import ema
from tools.ema import EMA
from tools.vwap import VWAP
from tools.indicator import Indicator
# temp:
import plotly.graph_objects as go




# Set IST timezone
IST = pytz.timezone('Asia/Kolkata')
def ist_time(*args):
    return datetime.now(IST).timetuple()

# Config.:
logging.Formatter.converter = ist_time  
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def visualize(candles: list[Candle], ema9_hist: list[IndicatorModel], ema20_hist: list[IndicatorModel]):
    fig = go.Figure()
    # Candlestick Chart
    fig.add_trace(
        go.Candlestick(
            x=[candle.timestamp for candle in candles],
            open=[candle.open for candle in candles],
            high=[candle.high for candle in candles],
            low=[candle.low for candle in candles],
            close=[candle.close for candle in candles],
            name="Price"
        )
    )

    # EMA 9 (Blue Line)
    fig.add_trace(
        go.Scatter(
            x=[ema.timestamp for ema in ema9_hist],
            y=[ema.value for ema in ema9_hist],
            mode="lines",
            line=dict(color="blue", width=2),
            name="9 EMA"
        )
    )

    # EMA 20 (Red Line)
    fig.add_trace(
        go.Scatter(
            x=[ema.timestamp for ema in ema20_hist],
            y=[ema.value for ema in ema20_hist],
            mode="lines",
            line=dict(color="red", width=2),
            name="20 EMA"
        )
    )

    # Layout Settings
    fig.update_layout(
        title="KEC INTL. EMA Visualization",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark"
    )

    # Show the Plot
    fig.show()
    



async def main():
    access_token = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzSkM2TTQiLCJqdGkiOiI2N2RiOWFjZWYwNjZiODIzNmI0NDY0NmIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzQyNDQ1MjYyLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NDI1MDgwMDB9.8m7UP2agh5mcv3w4EHKff8zFWfDwEpcvP07e6jizD80"
    exchange = "NSE"
    index_type = "EQ"
    ISIN = "INE389H01022"
    
    instrument_key = f"{exchange}_{index_type}|{ISIN}"
    previous_day = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # initialize...
    try:
        fetcher = DataFetcher(access_token)
        preprocessor = DataPreprocessor()
        pipeline = IndicatorPipeline()

        # add indicators to pipeline [ema, vwap, etc...]
        ema9 = EMA(period=9)
        ema20 = EMA(period=20)
        pipeline.add_indicator("EMA9", ema9)
        pipeline.add_indicator("EMA20", ema20)
        
    
        #* Historical Data Fetch & Process...
        logging.info("Fetching historical data...")
        historical_one_min_candles = fetcher.get_historical_data(ISIN=ISIN,
                                                     date=previous_day)
        preprocessor.convert_to_5min_candles(historical_one_min_candles)
        historical_five_min_candles = preprocessor.five_min_candles.copy()
    
        # 
        pipeline.initialize_indicators(historical_five_min_candles)
    
    
        #* Intrayday Data Fetch & Process...
        logging.info("Fetching intraday data...")
        intraday_one_min_candles = fetcher.get_intraday_data(ISIN=ISIN)
        preprocessor.convert_to_5min_candles(intraday_one_min_candles)
    
        preprocessor.five_min_candles = preprocessor.five_min_candles[75:]
        
        
        #*
        for five_min_candle in preprocessor.five_min_candles:
            pipeline.update_all(five_min_candle)
            print("-"*50)
    
    
        # visualize(preprocessor.five_min_candles[75:], ema9.history, ema20.history)

        # Websocket start to fetch real-time data:
        candle_queue = asyncio.Queue()
        ltpc_queue = asyncio.Queue()
        logging.info("Starting Websocket...")
        asyncio.create_task(fetcher.start_websocket(ISIN, 
                                                candle_queue=candle_queue,
                                                ltpc_queue=ltpc_queue
                                                ))
     
        # Real-time processing loop:
        while True:
            try:
                new_one_min_candle = await candle_queue.get()
                five_min_candle = preprocessor.update_with_realtime_data(new_one_min_candle)
                if five_min_candle:
                    pipeline.update_all(five_min_candle)
                
                ltpc = await ltpc_queue.get()
                estimates = pipeline.estimate_all(ltpc=ltpc)
                ts = ltpc.ltt
                logging.info(f"Real-time estimates: {estimates} @ {ts.hour}:{ts.minute}:{ts.second}:{ts.microsecond} | {ts.day}-{ts.month}-{ts.year}")
            
            except Exception as e:
                logging.error(f"❗Error in real-time processing: {e}")
    
    except Exception as e:
        logging.error(f"Initialization error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Process inturrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")