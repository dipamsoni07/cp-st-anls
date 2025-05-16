import asyncio
import logging
from typing import List
from datetime import datetime

from src.algorithm import get_logger
from src.algorithm.models.trade_signals import SIGNAL
from src.algorithm.core.order_manager import ORDER_MANAGER
from src.algorithm.models.shared_data import SharedData


class SignalBasedOrderManager:
    """Class to Automate the BUY/SELL and other orders based on the incoming SIGNAL form the algorithm.
    
    NOTE: This algorithm is currently focuses only on LONG Intraday orders [i.e.: BUY first, SELL later]. SHORT Intraday Orders [i.e.: SELL first, BUY later] strategy will be implemented once it is tested manually.
    """

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
        # self.shared_data = shared_data
        self.logger:logging.Logger = None
        self.market_spread = 0.05
        
    async def start_monitoring(self, isin:str):
        """Start monitoring signals for the given Stock ISIN."""
        self.isin = isin
        self.is_monitoring = True
        self.logger = get_logger(__name__, isin=self.isin)
        self.logger.info(f"Started monitoring signals for {self.isin}.")
        await self._monitor_signals()
    
    async def stop_monitoring(self):
        """Stop monitoring signals."""
        self.is_monitoring = False
        self.logger.info(f"Stopped monitoring signals for {self.isin}")
    
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
                self.logger.error(f"Error processing signal: {e}")
            await asyncio.sleep(0.1)
    
    async def _handle_buy_signal(self, signal:SIGNAL):
        """Handle a BUY signal by placing a buy order and setting up sell orders."""
        
        
        if signal.timestamp.date() != datetime.today().date():
            self.logger.warning(f"""
                           Invalid BUY SIGNAL Date: {signal.timestamp.date()}
                           Today's Date: {datetime.today().date()}
                           
                           Cannot Place Intraday Market order with another dates...
                           :BUY ORDER NOT PLACED:
                           """)
            return
        
                    
        Q = self.default_quantity
        buy_order_tag = f'BUY-ORDER-{self.isin}-{Q}'
        buy_order_id = await self.order_manager.place_new_intraday_order(
            ISIN=self.isin,
            net_quantity=Q, 
            transaction_type='BUY',
            order_type='MARKET',
            tag=buy_order_tag,
            validity='DAY'
        )
        self.logger.info(f"Placing buy order {buy_order_id} for {Q} shares of {self.isin}")

        while True:
            response = await self.order_manager.get_order_details(buy_order_id)
            if response.get('status') == 'success':
                
                order_data = response['data']
                order_status = order_data['status']
                #! for testing set status == 'after market order req received'
                # if order_status == 'after market order req received':
                if order_status == 'complete' and order_data['pending_quantity'] == 0:
                    self.current_position += order_data['filled_quantity'] #-> Use this in live market. 
                    # self.current_position += order_data['quantity']
                    self.logger.info(f"""
                                    BUY order (id:{buy_order_id}) executed successfully.
                                    Stock Name: {order_data['trading_symbol']}
                                    Quantity Purchased: {order_data['filled_quantity']} Shares @ {order_data['order_type']}
{'-'*100}""")
                    self.executed_orders.append({
                        'order_id': buy_order_id,
                        'tag': buy_order_tag
                    })
                    break
                
                if order_status == 'rejected':
                    self.logger.warning(f"""
                                    BUY order rejected: {order_data['status_message']}
{'-'*100}""")
                    return
                
            await asyncio.sleep(0.3)
            
        await asyncio.sleep(0.3)
        
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
                # This field must be multiple of 0.05
                limit_price = level['value']
                limit_price = round(limit_price / self.market_spread) * self.market_spread
                tag = f"{label}-SELL-ORDER-{self.isin}-{qty}"
                sell_order_id = await self.order_manager.place_new_intraday_order(
                    ISIN = self.isin,
                    net_quantity=qty,
                    transaction_type='SELL',
                    order_type='LIMIT',
                    price=limit_price,
                    tag=tag,
                    validity='DAY'
                )
                self.pending_orders.append({
                    'order_id': sell_order_id,
                    'tag': tag
                })
                self.logger.info(f"""Placed LIMIT {label} SELL order {sell_order_id} for {qty} shares @ {limit_price}/- INR ({level['level']}% of BUY PRICE.)""")
                await asyncio.sleep(0.25)
                
                
    async def _handle_sell_signal(self):
        """Handle a SELL signal by canceling pending orders and selling the position."""
        if self.current_position <=0:
            # IF BUY order didn't executed at all... there's nothing to sell...
            self.logger.warning("No position to sell")
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
                        self.logger.info(f"Profit Booked at {order_tag[:2]} level | Q:{order_data['filled_quantity']} @ {order_data['price']}/- INR.")
                    
                    
                    # If Profit Booking Order didn't executed Before SL Call then Order will be cancelled and calculate the remaining quantities to SELL.
                    if order_status == 'open' or pending_quantity != 0:
                        total_pending_quantities += pending_quantity
                        # Cancelling all the OPEN orders [During SL condition hit]
                        await self.order_manager.cancel_orders(order_id=order_id)
                    
                    if order_status == 'rejected':
                        self.logger.info(f"Order at {order_tag[:2]} level |{order_data['status_message']}")
                    
                else:
                    self.logger.warning(f"Error fetching order {order_id} | TAG: {order_tag}")         

                await asyncio.sleep(0.25)
            
            self.current_position -= total_filled_quantities
            await asyncio.sleep(0.2)
            
            if total_pending_quantities == 0:
                self.logger.info('All orders executed successfully! Nothing to SELL')
                self.pending_orders = []
                return 
            
            if total_pending_quantities > 0: # selling all the remaining quantities (total exit from market)
                sell_order_tag = f'SELL-SL-ORDER-{self.isin}'
                sell_order_id = await self.order_manager.place_new_intraday_order(
                    self.isin,
                    net_quantity=total_pending_quantities,
                    transaction_type='SELL',
                    order_type='MARKET',
                    tag=sell_order_tag,
                    validity='DAY'
                )
                self.logger.info(f"Placing [SELL] order {sell_order_id} for remaining {total_pending_quantities} shares of {self.isin}")
                
                while True:
                    response = await self.order_manager.get_order_details(sell_order_id)
                    if response.get('status') == 'success':
                        order_data = response['data']
                        order_status = order_data['status']
                        #! for testing set status == 'after market order req received.
                        # if order_status == 'after market order req received': 
                        if order_status == 'complete' and order_data['pending_quantity'] == 0:
                            self.current_position = order_data['pending_quantity']
                            # self.current_position = 0
                            self.logger.info(f"SELL order {sell_order_id} executed successfully.")
                            self.logger.info(f"""
                                        Stock Name: {order_data['trading_symbol']}
                                        Quantity Sold: {order_data['filled_quantity']}
                                        """)
                            self.executed_orders.append({
                                'order_id': sell_order_id,
                                'tag': sell_order_tag
                            })
                            break
                        
                        if order_status == 'rejected':
                            self.logger.warning(f"SELL order rejected: {order_data['status_message']}")
                            break
                        
                        await asyncio.sleep(0.5)
            
            # Status
            self.logger.info(f"""
                        Trade Status:
                        Number of Executed Orders: {len(self.executed_orders)}
                        Number of Unexecuted Orders: {len(self.pending_orders)}
                        """)
            
            if self.current_position != 0:
                self.logger.warning(f"""{self.current_position} Shares left to SELL. Please EXIT all positions manually.""")        
            
            
            self.pending_orders = []
            
        except Exception as e:
            self.logger.error(f"Error @ _handle_sell_signal: {e}")

