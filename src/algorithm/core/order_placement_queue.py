import asyncio
from typing import Dict, Any

class OrderPlacementQueue:
    
    def __init__(self,
                 order_manager):
        self.order_manager = order_manager
        self.queue = asyncio.Queue()
        self.rate_limit_delay = 0.25
        self._task = asyncio.create_task(self._process_queue())


    async def place_order(self, payload: Dict[str, Any]) -> str:
        """Add an order to the queue and wait for its execution."""
        future = asyncio.Future()
        await self.queue.put((payload, future))
        return await future

    async def _process_queue(self):
        """Process orders with rate limiting (fetching from the queue)."""
        while True:
            payload, future = await self.queue.get()
            try:
                order_id = await self.order_manager._place_order_direct(payload=payload)
                future.set_result(order_id)
            except Exception as e:
                future.set_exception(e)
            await asyncio.sleep(self.rate_limit_delay)
            
            
            
# class OrderPlacementQueue:
    
#     def __init__(self,
#                  order_manager:ORDER_MANAGER,
#                  max_rate: int=4):
#         self.order_manager = order_manager
#         self.queue = asyncio.Queue()
#         self.max_rate = max_rate
#         self.semaphore = asyncio.Semaphore(max_rate)
#         asyncio.create_task(self.process_queue())

#     async def place_order(self, order_data: dict):
#         """Queue an order for placement."""
#         future = asyncio.get_event_loop().create_future()
#         await self.queue.put((order_data, future))
#         return await future

#     async def process_queue(self):
#         """Process queued orders with rate limiting."""
#         while True:
#             order_data, future = await self.queue.get()
#             async with self.semaphore:
#                 try:
#                     order_id = await self.order_manager._place_order_direct(order_data)
#                     future.set_result(order_id)
#                 except Exception as e:
#                     future.set_exception(e)
#                 finally:
#                     await asyncio.sleep(1 / self.max_rate)
#             self.queue.task_done()