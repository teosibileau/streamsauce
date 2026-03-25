from contextlib import asynccontextmanager

import uvicorn
from dbos import DBOS
from fastapi import FastAPI

from .api import router
from .config import amqp_config, dbos_config
from .consumer import AMQPConsumer

consumer = AMQPConsumer(amqp_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    DBOS.launch()
    await consumer.start()
    yield
    await consumer.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
DBOS(fastapi=app, config=dbos_config)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
