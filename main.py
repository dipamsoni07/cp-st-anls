import os
import socket
import asyncio
from dotenv import load_dotenv
from src.algorithm import get_logger
import uvicorn

from src.algorithm.pipelines.stock_manager import StockManager
from src.algorithm.core.order_manager import OrderPlacementQueue
from src.algorithm.api import endpoints, dependencies 

logger = get_logger("main")


async def main():
    access_token = os.getenv("ACCESS_TOKEN")
    if access_token:
        access_token = access_token.replace("'", "").replace('"','')
    else:
        raise RuntimeError("ACCESS_TOKEN not found in environment. Create .env file & put ACCESS_TOKEN=here from upstox.")
    
    stock_manager_instance = StockManager(access_token=access_token)
    dependencies.stock_manager_instance = stock_manager_instance
    logger.info(f"Initialized Auto Stock Manager with upstox access token...")
    
    port = 8000
    config = uvicorn.Config(endpoints.app, host='0.0.0.0', port=port, log_level="info", reload=True)
    server = uvicorn.Server(config)
    
    host_ip = socket.gethostbyname(socket.gethostname())
    # logger.info(f"--> Server Running Open: http://{host_ip}:{port}")
    logger.info(f"--> Server Running Open: http://localhost:{port}")
    

    await asyncio.gather(
        server.serve(), 
        stock_manager_instance.run())


if __name__ == "__main__":
    try:
        load_dotenv(override=True)
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process inturrupted by user! Force shut-down.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        












# async def user_input_loop(stock_manager: StockManager):
#     """Temp. CLI for user interaction."""
#     while True:
#         cmd = input("Enter command (add <isin> <quantity>, remove <isin>, quit): ").split()
#         if cmd[0].lower() == "add" and len(cmd) == 3:
#             await stock_manager.add_stock(cmd[1], int(cmd[2]), "2025-04-05"),
#         elif cmd[0].lower() == "remove" and len(cmd) == 2:
#             await stock_manager.remove_stock(cmd[1])
#         elif cmd[0] == "quit":
#             break
        

# async def main():
#     load_dotenv()
    
#     access_token = os.getenv('ACCESS_TOKEN')
#     stock_manager = StockManager(access_token)
#     order_queue = OrderPlacementQueue(stock_manager.order_manager)
#     await stock_manager.add_stock(
#         "INE389H01022",
#         10,
#         "2025-04-05"
#     )
#     await asyncio.gather(
#         stock_manager.run(),
#         order_queue.process_queue(),
#         user_input_loop(stock_manager = stock_manager)
#     )
    
# if __name__ == "__main__":
#     asyncio.run(main())