# lit-data-layers

Provides 

## Installation

```shell
pip install "lit-data-layers[sqldb]"
```

## Usage

```python
import asyncio

import chainlit.data as cl_data
from lit_data_layers.sqldb import SqlDataLayer

layer = SqlDataLayer()
asyncio.get_event_loop().run_until_complete(layer.initialize_database())
cl_data._data_layer = layer
```