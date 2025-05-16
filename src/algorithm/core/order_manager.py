import json
import aiohttp
import asyncio
from typing import Literal, Optional
from datetime import datetime

from src.algorithm import get_logger
from src.algorithm.core.order_placement_queue import OrderPlacementQueue


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
        self.logger = get_logger(__name__)
        self.order_queue = OrderPlacementQueue(self)
    
    async def _place_order_direct(self, payload: dict) -> str:
        """Directly place an order via the API (used by OrderPlacementQueue)."""
        async with aiohttp.ClientSession() as session:
            async with session.post(self.order_place_url, headers=self.headers, json=payload) as response:
                response_json = await response.json()
                self.logger.info(f"Place order response: {response_json}")
                if response_json.get('status') == 'success':
                    order_id = response_json['data']['order_ids'][0]
                    self.order_history.append(order_id)
                    return order_id
                else:
                    raise Exception(f"Failed to place order: {response_json}")
            
    
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
        
        try:
            return await self.order_queue.place_order(payload)
        except Exception as e:
            self.logger.error(f"Error placing order for {ISIN}: {e}")
            raise


        
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
                else:
                    self.logger.info(f"Failed to fetch order {order_id}: {response_json}")
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
    
