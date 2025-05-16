from pydantic import BaseModel


class StockRequest(BaseModel):
    isin:str
    quantity: int
    date:str
    # buy/sell