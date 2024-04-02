import asyncio

import chainlit as cl
import chainlit.data as cl_data
from chainlit.input_widget import Select

from lit_data_layers.sqldb import SqlDataLayer

layer = SqlDataLayer()
asyncio.get_event_loop().run_until_complete(layer.initialize_database())
cl_data._data_layer = layer


@cl.on_chat_start
async def start():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="OpenAI - Model",
                values=["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"],
                initial_index=0,
            )
        ]
    ).send()


@cl.on_settings_update
async def setup_agent(settings):
    print("on_settings_update", settings)


@cl.on_message
async def main(message: cl.Message):
    # Your custom logic goes here...

    with cl.Step("Foo", type="tool") as step:
        step.output = 'loo'

    # Send a response back to the user
    await cl.Message(
        content=f"Received: {message.content}",
    ).send()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None
