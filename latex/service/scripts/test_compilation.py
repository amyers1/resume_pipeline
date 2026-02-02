import asyncio
import json

import aio_pika


async def test():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    channel = await connection.channel()

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(
                {
                    "job_id": "test-001",
                    "content": r"\documentclass{article}\begin{document}Test\end{document}",
                    "engine": "xelatex",
                }
            ).encode()
        ),
        routing_key="latex_compile",
    )

    await connection.close()


asyncio.run(test())
