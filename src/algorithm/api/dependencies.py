from src.algorithm.pipelines.stock_manager import StockManager

# This should be set during initialization in main.py
stock_manager_instance:StockManager = None

def get_stock_manager() -> StockManager:
    if stock_manager_instance is None:
        raise Exception("Stock manager not initialized.")
    return stock_manager_instance

