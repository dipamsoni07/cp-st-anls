import asyncio
from typing import List, Dict, Literal, Optional
from datetime import datetime, timedelta
import logging
from wsgiref import headers
import aiohttp
from pydantic import BaseModel
import json

import requests





ORDER_PLACE_URL = 'https://api-hft.upstox.com/v3/order/place'
ORDER_FETCH_URL = 'https://api.upstox.com/v2/order/details'
ORDER_CANCEL_URL = 'https://api.upstox.com/v3/order/cancel'

access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzSkM2TTQiLCJqdGkiOiI2N2U4MzdjMGE4ZTMwMzUyMTRlMTY4N2MiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzQzMjcxODcyLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NDMyODU2MDB9.9T40rXX27Le_DInxI7gHVz-wijapdNg7l7Nk4xGSTZQ'

class SIGNAL(BaseModel):
    signal: Literal["WAIT", "BUY", "HOLD", "SELL"] = None
    value: float
    timestamp: datetime
    levels: Optional[List] = [] #Dict [ level(int), value(float), timestamp(datetime)]


class ORDER_PLACE:
    
    def __init__(self):

        self.order_place_url = ORDER_PLACE_URL
        self.order_fetch_url = ORDER_FETCH_URL
        self.order_cancel_url = ORDER_CANCEL_URL
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f"Bearer {access_token}"   
        }

        self.orders_history = []
    
    def place_new_intraday_order(self,
                        ISIN: str,
                        net_quantity: int,
                        transaction_type: Literal['BUY', 'SELL'],
                        order_type: Literal['MARKET', 'LIMIT'],
                        price: float = None,
                        validity: Literal['IOC', 'DAY'] = 'IOC',
                        stock_type: Literal['NSE', 'BSE'] = 'NSE',
                        index_type: Literal['EQ', 'FO'] = 'EQ',
                        ):
        
        if net_quantity < 1:
            raise ValueError(f"net_quantity entered should be greater than or equal to 1 in order to place successful order!")
        if order_type == 'LIMIT' and price is None:
            raise ValueError(f"Enter Limit Price value for placing {transaction_type} order.")    
        if order_type == 'MARKET' and price != 0:
            price = 0
        
        identification_tag = f"{ISIN}-{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}" 
       
        order_place_data = {
            'quantity': net_quantity,
            'product': 'I',
            'validity': validity,
            'price': price,
            'tag': identification_tag,
            'instrument_token': f'{stock_type}_{index_type}|{ISIN}',
            'order_type': order_type,
            'transaction_type': transaction_type,
            'disclosed_quantity': 0,
            'trigger_price': 0,
            'is_amo': False,
            'slice': True
        }
        
        try:
            
            response = requests.post(
                self.order_place_url,
                headers=self.headers,
                json=order_place_data
            )
            
            print('Response Code:', response.status_code)
            
            res = json.dumps(response.json(), indent=2)
            
            print('Response Body:', res)
            
            if response["status"] == "success":
                order_details = response["data"]["order_ids"]
                self.orders_history.extend(order_details)
                return 
            
        except Exception as e:
            print('Error: ', str(e))

    def get_order_details(self, order_id):
        
        
        params = {
            'order_id' : order_id
        }
        response = requests.get(self.order_fetch_url, headers=self.headers, params=params)
        
        print('Response Code:', response.status_code)
            
        res = json.dumps(response.json(), indent=2)
            
        # print('Response Body:', res)
        print(res)
        
    def cancel_order(self, order_id):
        
        params = {
            'order_id': order_id
        }
        
        response = requests.delete(self.order_cancel_url, headers=self.headers, params=params)
        print('Resposne Code:', response.status_code)
        res = json.dumps(response.json(), indent=2)
        print(res)
        
        
    
place_order = ORDER_PLACE()


# place_order.place_new_intraday_order(
#     net_quantity=2,
#     validity='DAY',
#     price=485.52,
#     order_type='LIMIT',
#     transaction_type='SELL',
#     ISIN='INE914M01019'
# )        

# for order in place_order.orders_history:
#     print(order)

# place_order.get_order_details(order_id='250328000025309')

orders = [
    "250328000025327",
    "250328000025339",
    "250328000025344",
    "250328000025312",
    "250328000025309",
    "250328000025147"
]

for order in orders:
    place_order.cancel_order(order_id=order)


import asyncio
from typing import Literal, Optional
import logging
from datetime import datetime

class ORDER_MANAGER:
    """Manages order placement, fetching and cancellation using upstox API."""

    def __init__(self, access_token: str):
        """
        Initialize the order manager with an access token for auth...

        :param access_token: Upstox API access token.
        """
        
        self.order_place_url = 'https://api-hft.upstox.com/v3/order/place'
        self.order_fetch_url = 'https://api.upstox.com/v2/order/details'
        self.order_cancel_url = 'https://api.upstox.com/v3/order/cancel'
        
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f"Bearer {access_token}"
        }
        
        self.order_history = []
        self.logger = logging.getLogger(__name__)
    
    
    async def place_new_intraday_order(self,
                                       ISIN: str,
                                       net_quantity: int, 
                                       transaction_type: Literal['BUY', 'SELL'],
                                       order_type: Literal['MARKET', 'LIMIT'],
                                       price: Optional[float]= None,
                                       validity: Literal['IOC', 'DAY'] = 'IOC',
                                       stock_type: Literal['NSE', 'BSE'] = 'NSE',
                                       index_type: Literal['EQ', 'FO'] = 'EQ',
                                       tag: str = None
                                       ) -> str:

        """Place a new intraday order (BUY / SELL)
        
        :param ISIN: Stock ISIN (e.g., 'INE914M01019').
        :param net_quantity: Number of shares to buy or sell.
        :param transaction_type: 'BUY' or 'SELL'.
        :param order_type: 'MARKET' or 'LIMIT'.
        :param price: Price for limit orders (None for market orders).
        :param validity: 'IOC' (Immediate or Cancel) or 'DAY'.
        :param stock_type: 'NSE' or 'BSE' (default: 'NSE').
        :param index_type: 'EQ' (Equity) or 'FO' (Futures & Options, default: 'EQ').
        :param tag: [Optional] Order tag to identify the order type / Datetime tag by default.
        :return: Order ID of the placed order.
        :raises ValueError: If parameters are invalid.
        :raises Exception: If the order placement fails.
        """

        if net_quantity < 1:
            raise ValueError("net_quantity must be at least 1.")
        if order_type == 'LIMIT' and price is None:
            raise ValueError("price must be provided for LIMIT orders.")
        if order_type == 'MARKET':
            price = 0
            
        if tag is None:
            f"{ISIN}-{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"
            

        instrument_token = f"{stock_type}_{index_type}|{ISIN}"
        
        payload = {
            'quantity': net_quantity,
            'product': 'I',  # Intraday product
            'validity': validity,
            'price': price,
            'tag': tag,
            'instrument_token': instrument_token,
            'order_type': order_type,
            'transaction_type': transaction_type,
            'disclosed_quantity': 0,
            'trigger_price': 0,
            'is_amo': False,  # After Market Order flag
            'slice': True
        }

        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.order_place_url, headers=self.headers, json=payload) as response:
                response_json = await response.json()
                self.logger.info(f"Place order response: {response_json}")

                if response_json.get('status')== 'success':
                    order_id = response_json['data']['order_ids']
                    self.order_history.extend(order_id)
                    return order_id
                else:
                    raise Exception(f"Failed to place order: {response_json}")
        
    async def get_order_details(self, order_id:str) -> dict:
        """
        Fetch details of specific order...

        :param order_id: The ID of the order to fetch.
        :return: Dictionery containing order details.
        """
        
        params = { 'order_id' : order_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.order_fetch_url, headers= self.headers, params=params) as response:
                response_json = await response.json()
                self.logger.info(f"Order details for {order_id}: {response_json}")
                return response_json
            
    async def cancel_orders(self, order_id: str) -> None:
        """
        Cancel a specific order.

        :param order_id: The ID of the order to cancel.
        :raises Exception: If cancellation fails.
        """
        
        params = {'order_id': order_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(self.order_cancel_url, headers=self.headers, params=params) as response:
                response_json = await response.json()
                self.logger.info(f"Cancel order response for {order_id}: {response_json}")

                if response_json.get('status') != 'success':
                    raise Exception(f"Failed to cancel order: {response_json}")
                


#* ------------------------------------------------------------------------------------- 
#* ------------------------------------------------------------------------------------- 
#* ------------------------------------------------------------------------------------- 

import asyncio 
import logging
from typing import List

# from models.trade_signals import SIGNAL
# from core.order_manager import ORDER_MANAGER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalBasedOrderManager:
    
    def __init__(self,
                 order_manager: ORDER_MANAGER,
                 signal_queue: asyncio.Queue,
                 default_quantity: int):

        self.order_manager = order_manager
        self.signal_queue = signal_queue
        self.default_quantity = default_quantity
        self.current_position = 0
        self.pending_orders: List[str] = []
        self.executed_orders: List[str] = []
        self.is_monitoring = False
        self.isin: str = ""
        
    async def start_monitoring(self, isin:str):
        """Start monitoring signals for the given Stock ISIN."""
        self.isin = isin
        self.is_monitoring = True
        logger.info(f"Started monitoring signals for {self.isin}.")
        await self._monitor_signals()
    
    async def stop_monitoring(self):
        """Stop monitoring signals."""
        self.is_monitoring = False
    
    async def _monitor_signals(self):
        """Monitor the signal and process signals."""
        while self.is_monitoring:
            try:
                signal: SIGNAL = await self.signal_queue.get()
                if signal.signal == "BUY":
                    #
                    pass
                elif signal.signal == "SELL":
                    # 
                    pass
                self.signal_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing signal: {e}")
            await asyncio.sleep(0.1)
    
    async def _handle_buy_signal(self, signal:SIGNAL):
        """Handle a BUY signal by placing a buy order and setting up sell orders."""    
        Q = self.default_quantity
        buy_order_tag = f'BUY-ORDER-{self.isin}-{Q}'
        buy_order_id = await self.order_manager.place_new_intraday_order(
            ISIN=self.isin,
            net_quantity=Q, 
            transaction_type='BUY',
            order_type='MARKET',
            tag= buy_order_tag
        )
        logger.info(f"Placing buy order {buy_order_id} for {Q} shares of {self.isin}")

        while True:
            order_details = self.order_manager.get_order_details(buy_order_id)
            if order_details.get('status') == 'success':
               self.current_position += order_details['data']['quantity']
               logger.info(f"BUY order {buy_order_id} executed successfully. ")
               self.executed_orders.append({
                   'order_id': buy_order_id,
                   'tag': buy_order_tag
               })
               break
            await asyncio.sleep(0.5)
            
        await asyncio.sleep(0.5)
        # self.current_position += Q
        
        # Profit levels order placing...
        positive_levels = [level for level in signal.levels if level['level'] > 0]
        N = len(positive_levels)
        if N > 0 and N < 5:
            # sell_quantity = 
            t1_qty = round(0.50 * Q) # %50
            t2_qty = round(0.10 * Q) # %10
            t3_qty = round(0.15 * Q) # %15
            t4_qty = Q - (t1_qty - t2_qty - t3_qty) # ~%25 (Remaining) 

            sell_orders_info = [
                (t1_qty, "T1"),
                (t2_qty, "T2"),
                (t3_qty, "T3"),
                (t4_qty, "T4"),
            ]

            for (qty, label), level in zip(sell_orders_info, positive_levels):
                limit_price = level['value']
                tag = f"{label}-SELL-ORDER-{self.isin}-{qty}-{limit_price}INR"
                sell_order_id = await self.order_manager.place_new_intraday_order(
                    ISIN = self.isin,
                    net_quantity=qty,
                    transaction_type='SELL',
                    order_type='LIMIT',
                    price=limit_price,
                    tag=tag
                )
                self.pending_orders.append({
                    'order_id': sell_order_id,
                    'tag': tag
                })
                logger.info(f"Placed limit {label} SELL order {sell_order_id} for {qty} shares @ {limit_price}/- INR")
        
        #! Temporary adding (-2% SL here):
        stop_loss_level = next((level for level in signal.levels if level['levels'] == -2), None)
        if stop_loss_level:
            # trigger_price = stop_loss_level['value']
            # sl_order_id = await self.order_manager.place_new_intraday_order(
            #     ISIN = self.isin,
            #     net_quantity=Q,
            #     transaction_type='SELL',
            #     order_type='SL-M',
            #     # trigger_price
            # )
            # self.pending_orders.append(sl_order_id)
            # logger.info(f"Placed stop-loss order {sl_order_id} for {Q} shares with trigger {trigger_price}/- INR.")
            pass    

    async def _handle_sell_signal(self):
        """Handle a SELL signal by canceling pending orders and selling the position."""
        if self.current_position <=0:
            logger.warning("No position to sell")
            return
        
        # order status order with filled_quantity and match them, 
        # count the pending order and match them 
        # Both's summation should be equal to net_quantity self.current_position
        
        total_filled_quantities = 0
        for order in self.pending_orders:
            order_id = order['order_id']
            order_tag = order['tag']
            order_details = self.order_manager.get_order_details(order_id=order_id)
            if order_details.get('status') == 'success':
                order_status = order_details['data']['status']
                filled_quantity = order_details['data']['filled_quantity']
                if order_status == 'complete':
                    total_filled_quantities += filled_quantity
                    self.executed_orders.append({
                        'order_id': order_id,
                        'tag': order_tag
                    })
                
                if order_status == 'open':
                    # Force exit condition...
                    pass

            await asyncio.sleep(0.5)
        
        
        self.pending_orders.get
        for order_id in self.pending_orders:
            await self.order_manager.cancel_orders(order_id)


#* ------------------------------------------------------------------------------------- 
#* SCRAPED--------------------------------------------------------------------------- 
#* ------------------------------------------------------------------------------------- 
import asyncio
import logging
from datetime import datetime
import math
from typing import List, Optional, Literal

# from order_manager import ORDER_MANAGER


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s %(name)s: %(message)s]",
    handlers=[logging.StreamHandler()]
)

class TradeExecutor:
    """Manages the execution of 'BUY' orders & all predefined profit booking levels (e.g., t1-t4)."""
    
    def __init__(self, order_manager: ORDER_MANAGER):
        """Initializing with an instance of ORDER_MANAGER"""    
        self.order_manager = order_manager
        self.logger = logging.getLogger(f"{__name__}.TradeExecutor")
        self.total_quantity = 0 # Variable to track total shares bought to keep buying & selling in sync and avoiding possible errors.
        
    async def execute_trade(self,
                            isin:str,
                            quantity: int,
                            buy_price: Optional[float] = None,
                            sell_prices: Optional[List[float]] = None
                            ) -> str:
        """
        Place a buy order and optional predefined sell orders. 
        
        :param ISIN: Stock ISIN (e.g., 'INE914M01019).
        :param quantity: Total shares to buy (e.g., 100 Quantities).
        :param buy_price: Buy order price (None for market order).
        :param sell_prics: Optional List of 4 limit prices for predefined profit booking (sell after buy) t1-t4 orders.
        :return: Buy order ID for tracking.
        """
        
        # BUY Order Execution...
        buy_order_type = 'MARKET' if buy_price is None else 'LIMIT'
        buy_order_id = self.order_manager.place_new_intraday_order(
            ISIN=isin,
            net_quantity=quantity,
            transaction_type='BUY',
            order_type=buy_order_type,
            price=buy_price,
            validity='IOC',
            tag=f'BUY-ORDER-{isin}-{quantity}'
        )
        self.logger.info(f"Placing buy order {buy_order_id} for {quantity} shares of {isin}")

        while True:
            order_details = self.order_manager.get_order_details(buy_order_id)
            if order_details.get('status') == 'success':
               self.total_quantity = order_details['data']['quantity']
               self.logger.info(f"BUY order {buy_order_id} executed successfully. ")
               break
            await asyncio.sleep(0.5)
        
        if sell_prices and len(sell_prices) == 4:
            await self._place_predefined_sell_orders(isin, quantity, sell_prices)
        
        return buy_order_id 

            
    async def _place_predefined_sell_orders(self,
                                            isin:str,
                                            quantity: int,
                                            sell_prices: List[float]
                                            ):
        """Place t1-t4 sell orders with calculated quantities."""
        
        #! BUG: To discuss & finalize before execution with real-money.
        #! My Recommendations: use round() feature for better accuracy compare to floor. 
        # t1_qty = math.floor(0.5 * quantity) # %50
        # t2_qty = math.floor(0.1 * quantity) # %10
        # t3_qty = math.floor(0.15 * quantity) # %15
        t1_qty = round(0.50 * quantity) # %50
        t2_qty = round(0.10 * quantity) # %10
        t3_qty = round(0.15 * quantity) # %15
        t4_qty = quantity - (t1_qty - t2_qty - t3_qty) # ~%25 (Remaining) 

        sell_orders = [
            (t1_qty, sell_prices[0], "T1"),
            (t2_qty, sell_prices[1], "T2"),
            (t3_qty, sell_prices[2], "T3"),
            (t4_qty, sell_prices[3], "T4"),
        ]

        for qty, price, label in sell_orders:
            order_id = self.order_manager.place_new_intraday_order(
                ISIN=isin,
                net_quantity=qty,
                transaction_type='SELL',
                order_type='LIMIT',
                price=price,
                validity='IOC',
                tag=f"{label}-SELL-ORDER-{isin}-{qty}-{price}INR"
            )
            self.logger.info(f"Placed {label} sell order {order_id}: {qty} shares @ {price}/- INR")


class StopLossManager:
    """Monitoring trade signals and places stop-loss sell orders dynamically at market price."""
    
    def __init__(self, order_manager: ORDER_MANAGER, signal_queue: asyncio.Queue):
        """Initialize with order manager and signal queue."""
        self.order_manager = order_manager
        self.signal_queue = signal_queue
        self.logger = logging.getLogger(f"{__name__}.StopLossManager")
        self.remaining_quantity = 0 # To track unsold shares...
        self.is_active = False 
        
        
            
               
        
    
