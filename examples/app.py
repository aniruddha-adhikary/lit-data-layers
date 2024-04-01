import asyncio

import chainlit as cl
import chainlit.data as cl_data

from lit_data_layers.sqldb import SqlDataLayer

layer = SqlDataLayer()
asyncio.get_event_loop().run_until_complete(layer.initialize_database())
cl_data._data_layer = layer


@cl.on_message
async def main(message: cl.Message):
    # Your custom logic goes here...

    # Send a response back to the user
    await cl.Message(
        content=f"Received: {message.content}",
    ).send()
