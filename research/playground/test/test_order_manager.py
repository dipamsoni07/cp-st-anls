import aiohttp
import asyncio
from typing import Literal, Optional
import logging
from datetime import datetime


from pydantic import BaseModel
from typing import Literal, Optional, List
class SIGNAL(BaseModel):
    signal: Literal["WAIT", "BUY", "HOLD", "SELL"] = None
    value: float
    timestamp: datetime
    levels: Optional[List] = []





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
            'is_amo': True,  # After Market Order flag
            'slice': True
        }

        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.order_place_url, headers=self.headers, json=payload) as response:
                response_json = await response.json()
                self.logger.info(f"Place order response: {response_json}")

                if response_json.get('status')== 'success':
                    order_id = response_json['data']['order_ids']
                    self.order_history.extend(order_id)
                    return order_id[0]
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
                if response_json['status'] != 'success':  
                    stock_name = response_json['data']['trading_symbol']
                    order_status = response_json['data']['status']
                    order_tag = response_json['data']['tag']
                    self.logger.info(f"Order details for ordre_id: {order_id} & tag: {order_tag} | {stock_name} : {order_status} | {response_json['data']['quantity']} shares")
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
    
    async def exit_all_positions(self, tag: str):
        """
        Exit all open positions in one go using specific tags.
        
        :param tag: 
        """             
                
                
                


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
        self.current_position: int = 0 # quantities you own...
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
                    await self._handle_buy_signal(signal)
                elif signal.signal == "SELL":
                    await self._handle_sell_signal()
                    
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
            response = await self.order_manager.get_order_details(buy_order_id)
            if response.get('status') == 'success':
                
                order_data = response['data']
                order_status = order_data['status']
                #! for testing set status == 'after market order req received'
                if order_status == 'after market order req received':
                #? if order_status == 'complete' and order_data['pending_quantity'] == 0:
                    #? self.current_position += order_data['filled_quantity'] #-> Use this in live market. 
                    self.current_position += order_data['quantity']
                    logger.info(f"BUY order {buy_order_id} executed successfully.")
                    logger.info(f"""Stock Name: {order_data['trading_symbol']}
                                Quantity Purchased: {order_data['filled_quantity']} Shares @ {order_data['order_type']}
                                """)
                    self.executed_orders.append({
                        'order_id': buy_order_id,
                        'tag': buy_order_tag
                    })
                    break
                
                if order_status == 'rejected':
                    logger.warning(f"BUY order rejected: {order_data['status_message']}")
                    break
                
            await asyncio.sleep(0.5)
            
        await asyncio.sleep(0.5)
        
        # Profit levels order placing...
        positive_levels = [level for level in signal.levels if level['level'] > 0]
        N = len(positive_levels)
        if N > 0 and N < 5:
            # sell_quantity = 
            t1_qty = round(0.50 * Q) # %50
            t2_qty = round(0.10 * Q) # %10
            t3_qty = round(0.15 * Q) # %15
            t4_qty = Q - (t1_qty + t2_qty + t3_qty) # ~%25 (Remaining) 

            sell_orders_info = [
                (t1_qty, "T1"),
                (t2_qty, "T2"),
                (t3_qty, "T3"),
                (t4_qty, "T4"),
            ]

            for (qty, label), level in zip(sell_orders_info, positive_levels):
                limit_price = level['value']
                tag = f"{label}-SELL-ORDER-{self.isin}-{qty}"
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
                await asyncio.sleep(0.25)
        

    async def _handle_sell_signal(self):
        """Handle a SELL signal by canceling pending orders and selling the position."""
        if self.current_position <=0:
            # IF BUY order didn't executed at all... there's nothing to sell...
            logger.warning("No position to sell")
            return
        
        total_filled_quantities: int = 0
        total_pending_quantities: int = 0
        try:
            for order in self.pending_orders:
                order_id = order['order_id']
                order_tag = order['tag']
                
                response = await self.order_manager.get_order_details(order_id=order_id)
                
                if response.get('status') == 'success':
                    order_data = response['data']
                    order_status = order_data['status']
                    pending_quantity = order_data['pending_quantity']
                    
                    # If Profit Order Executed Before SL call
                    if order_status == 'complete' and pending_quantity == 0:
                        total_filled_quantities += order_data['filled_quantity']
                        self.executed_orders.append({
                            'order_id': order_id,
                            'tag': order_tag
                        })
                        logger.info(f"Profit Booked at {order_tag[:2]} level | Q:{order_data['filled_quantity']} @ {order_data['price']}/- INR.")
                    
                    
                    # If Profit Booking Order didn't executed Before SL Call then Order will be cancelled and calculate the remaining quantities to SELL.
                    if order_status == 'open' or pending_quantity != 0:
                        total_pending_quantities += pending_quantity
                        # Cancelling all the OPEN orders [During SL condition hit]
                        await self.order_manager.cancel_orders(order_id=order_id)
                    
                    if order_status == 'rejected':
                        logger.info(f"Order at {order_tag[:2]} level |{order_data['status_message']}")
                    
                else:
                    logger.warning(f"Error fetching order {order_id} | TAG: {order_tag}")         

                await asyncio.sleep(0.25)
            
            self.current_position -= total_filled_quantities
            await asyncio.sleep(0.2)
            
            if total_pending_quantities == 0:
                logger.info('All orders executed successfully! Nothing to SELL')
                self.pending_orders = []
                return 
            
            if total_pending_quantities > 0: # selling all the remaining quantities (total exit from market)
                sell_order_tag = f'SELL-SL-ORDER-{self.isin}'
                sell_order_id = await self.order_manager.place_new_intraday_order(
                    self.isin,
                    net_quantity=total_pending_quantities,
                    transaction_type='SELL',
                    order_type='MARKET',
                    tag=sell_order_tag
                )
                logger.info(f"Placing [SELL] order {sell_order_id} for remaining {total_pending_quantities} shares of {self.isin}")
                
                while True:
                    response = await self.order_manager.get_order_details(sell_order_id)
                    if response.get('status') == 'success':
                        order_data = response['data']
                        order_status = order_data['status']
                        #! for testing set status == 'after market order req received.
                        if order_status == 'after market order req received': 
                        #? if order_status == 'complete' and order_data['pending_quantity'] == 0:
                            #? self.current_position = order_data['pending_quantity']
                            self.current_position = 0
                            logger.info(f"SELL order {sell_order_id} executed successfully.")
                            logger.info(f"""Stock Name: {order_data['trading_symbol']}
                                        Quantity Sold: {order_data['filled_quantity']}
                                        """)
                            self.executed_orders.append({
                                'order_id': sell_order_id,
                                'tag': sell_order_tag
                            })
                            break
                        
                        if order_status == 'rejected':
                            logger.warning(f"SELL order rejected: {order_data['status_message']}")
                            break
                        
                        await asyncio.sleep(0.5)
            
            # Status
            logger.info(f"""
                        Trade Status:
                        Number of Executed Orders: {len(self.executed_orders)}
                        Number of Unexecuted Orders: {len(self.pending_orders)}
                        """)
            
            if self.current_position != 0:
                logger.warning(f"""{self.current_position} Shares left to SELL. Please do it manually right now.""")        
            
            
            self.pending_orders = []
            
                    
            
            
        except Exception as e:
            logger.error(f"Error @ _handle_sell_signal: {e}")

        


async def main():
    
    ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzSkM2TTQiLCJqdGkiOiI2N2U4ZTBlOGE4ZTMwMzUyMTRlMTZiOTkiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzQzMzE1MTc2LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NDMzNzIwMDB9.rfLNqMuHpb_xi7ip-2LQ57EIhqzriP1m5eMmFIpUiR8"
    order_manager = ORDER_MANAGER(ACCESS_TOKEN)
    signal_queue = asyncio.Queue()
    default_quantity = 20
    signal_manager = SignalBasedOrderManager(
        order_manager=order_manager, 
        signal_queue=signal_queue,
        default_quantity=default_quantity
    )

    isin = "INE002A01018" # Reliance
    
    
    # p5 
    asyncio.create_task(signal_manager.start_monitoring(isin))
    
    
    #  let's suppose buy price 1275.10 :
    sample_profit_levels = [
        {'level': 1, 'value': 1287.851,'timestamp': datetime.now()},
        {'level': 2, 'value': 1300.602,'timestamp': datetime.now()},
        {'level': -2, 'value': 1249.598,'timestamp': datetime.now()},
        {'level': 3, 'value': 1313.353,'timestamp': datetime.now()},
        {'level': 4, 'value': 1326.104,'timestamp': datetime.now()},
    ]
    
    buy_signal = SIGNAL(
        signal='BUY',
        value=1275.10,
        timestamp=datetime.now(),
        levels = sample_profit_levels
    )
    
    logger.info("""
                WAIT FOR 5 SECONDS 
                DUMMY BUY SIGNAL TO BE QUEUED 
                """)
    await asyncio.sleep(5)
    await signal_queue.put(buy_signal)
    await asyncio.sleep(2)
    
    
    
    sell_signal = SIGNAL(
        signal='SELL',
        value=1270.1,
        timestamp=datetime.now(),
        levels = sample_profit_levels
    )
    
    logger.info("""
                WAIT FOR 10 SECONDS 
                DUMMY SELL SIGNAL TO BE QUEUED 
                """)
    
    await asyncio.sleep(10)
    await signal_queue.put(sell_signal)
    await asyncio.sleep(2)
    
    await asyncio.sleep(5)
    print("stopping the auto order manager...")
    await signal_manager.stop_monitoring()
    
    
if __name__ == "__main__":
    asyncio.run(main())

