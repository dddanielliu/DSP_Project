import asyncio
from contextlib import asynccontextmanager
from .demo import try_ask
from typing import Union

import torch
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

generate_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/generate")
async def generate_endpoint(user_text: str) -> Union[str, dict]:
    logger.info(f"got query: {user_text}")
    print(f"got query: {user_text}")
    async with generate_lock:
        logger.info(f"start generating {user_text}")
        print(f"start generating {user_text}")
        try:
            assistant_text = try_ask(user_text)
        except Exception as e:
            assistant_text = f"Failed to generate response. \nError: {e}"
        logger.info(f"llm response: {assistant_text}")
        print(f"llm response: {assistant_text}")
        return assistant_text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8901, log_level="debug", reload=False)

