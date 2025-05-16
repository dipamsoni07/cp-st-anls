from genericpath import getsize
import os
from pathlib import Path
import logging


logging.basicConfig(level=logging.INFO, format='[%(asctime)s: %(module)s]: %(message)s')

project_name = "algorithm-0.1"

list_of_files = [
    ".github/workflows/.gitkeep",
    f"src/{project_name}/__init__.py",
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/common.py",
    #
    f"src/{project_name}/config/__init__.py",
    f"src/{project_name}/config/configuration.py",
    #
    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/entity/config_entity.py",
    #
    f"src/{project_name}/algo_core/__init__.py",
    f"src/{project_name}/algo_core/algo.py",
    # 
    f"src/{project_name}/core/__init__.py",
    f"src/{project_name}/core/order_manager.py",
    f"src/{project_name}/core/signal_based_order_manager.py",
    
    f"src/{project_name}/logs/logger.py",
    #
    f"src/{project_name}/models/__init__.py",
    f"src/{project_name}/models/candle.py",
    f"src/{project_name}/models/indicators.py",
    f"src/{project_name}/models/ltpc.py",
    f"src/{project_name}/models/shared_data.py",
    f"src/{project_name}/models/trade_signals.py",
    #
    f"src/{project_name}/pipelines/__init__.py",
    f"src/{project_name}/pipelines/data_fetcher.py",
    f"src/{project_name}/pipelines/data_preprocessor.py",
    f"src/{project_name}/pipelines/indicator_pipeline.py",
    f"src/{project_name}/pipelines/MarketDataFeedV3_pb2.py",
    #
    f"src/{project_name}/shared/__init__.py",
    #
    f"src/{project_name}/tools/__init__.py",
    f"src/{project_name}/tools/indicator.py",
    f"src/{project_name}/tools/ema.py",
    f"src/{project_name}/tools/vwap.py",
    f"src/{project_name}/tools/macd.py",
    f"src/{project_name}/tools/sma.py",
    #
    f"src/{project_name}/client/__init__.py",
    f"src/{project_name}/client/dashboard.py",
    #
    ".env",
    ".env.example",
    "config/config.yaml",
    "main.py",
    "schema.yaml",
    "Dockerfile",
    "setup.py",
    "research/research.ipynb",
    "templates/index.html"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory [{filedir}] for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
        
        logging.info(f"Creating empty file: {filepath}")

    else:
        logging.info(f"{filename} already exists.")
        