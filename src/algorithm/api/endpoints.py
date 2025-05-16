import os
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from src.algorithm.pipelines.stock_manager import StockManager
from src.algorithm.api.dependencies import get_stock_manager
from src.algorithm import get_logger


logger = get_logger(__name__)
app = FastAPI()

# CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
# templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))



stock_manager: StockManager = None # initialized in main.py


class StockRequest(BaseModel):
    isin:str
    quantity: int
    # buy/sell


@app.post("/stocks", response_class=JSONResponse)
async def add_stock(stock: StockRequest, stock_manager:StockManager= Depends(get_stock_manager)):

    if stock_manager is None:
        raise HTTPException(status_code=500, detail="Stock manager not initialized.")
    await stock_manager.add_stock(stock.isin, stock.quantity)
    logger.info(f"Added stock {stock.isin}")
    return {
        "message": f"Added stock {stock.isin}."
    }
    
@app.delete("/stocks/{isin}", response_class=JSONResponse)
async def remove_stock(isin:str, stock_manager = Depends(get_stock_manager)):
    if stock_manager is None:
        raise HTTPException(status_code=500, detail="Stock manager not initialized.")
    await stock_manager.remove_stock(isin)
    logger.info(f"Removed stock {isin}")
    return {
        "message": f"Removed stock {isin}."
    }
    
@app.get("/stocks",  response_class=JSONResponse)
async def list_stocks(stock_manager:StockManager=Depends(get_stock_manager)):
    if stock_manager is None:
        raise HTTPException(status_code=500, detail="Stock manager not initialized.")
    stocks = list(stock_manager.processors.keys())
    return {
        "stocks": stocks
    }
    
# Frontend Form Handling Endpoint
@app.post("/add-stock", response_class = HTMLResponse)
async def add_stock_form(request: Request,
                            isin: str=Form(...),
                            quantity: int=Form(...),
                            stock_manager:StockManager = Depends(get_stock_manager)):
    
    if stock_manager is None:
        raise HTTPException(status_code=500, detail="Stock manager not initialized.")
    await stock_manager.add_stock(isin, quantity)
    logger.info(f"Added stock {isin} via frontend")
    stocks = list(stock_manager.processors.keys())
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "stocks":stocks,
            "message": f"Stock {isin} added."
        }
    )
    
    
@app.post("/remove-stock", response_class=HTMLResponse)
async def remove_stock_form(request: Request, isin: str = Form(...),
                            stock_manager: StockManager = Depends(get_stock_manager)):
    if stock_manager is None:
        raise HTTPException(status_code=500, detail="Stock manager not initialized.")
    await stock_manager.remove_stock(isin)
    logger.info(f"Removed stock {isin} via frontend")
    stocks = list(stock_manager.processors.keys())
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stocks": stocks,
        "message": f"Stock {isin} removed."
    })
    
@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    stock_manager:StockManager = Depends(get_stock_manager)
):
    stocks = list(stock_manager.processors.keys()) if stock_manager else []
    return templates.TemplateResponse(
        "index.html",
        {
            "request":request,
            "stocks":stocks,
            "message":None
        }
    )
    