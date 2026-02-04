import asyncio

import uvicorn
from api import app as fastapi_app
from latex_service import start_consumer


async def main():
    """
    Run the FastAPI server and the RabbitMQ consumer concurrently.
    """
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=80, log_level="info")
    server = uvicorn.Server(config)

    api_task = asyncio.create_task(server.serve())
    consumer_task = asyncio.create_task(start_consumer())

    await asyncio.gather(api_task, consumer_task)


if __name__ == "__main__":
    asyncio.run(main())
