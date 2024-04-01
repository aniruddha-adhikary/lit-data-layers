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

## Compatibility Chart

Features that have been **tested**.

| Method              	 | SQLite 	 | PostgreSQL 	 |
|-----------------------|----------|--------------|
| get_user            	 | 	        | 	            |
| create_user         	 | 	        | 	            |
| delete_user_session 	 | 	        | 	            |
| upsert_feedback     	 | 	        | 	            |
| create_element      	 | 	        | 	            |
| get_element         	 | 	        | 	            |
| delete_element      	 | 	        | 	            |
| create_step         	 | ✅      	 | 	            |
| update_step         	 | 	        | 	            |
| delete_step         	 | 	        | 	            |
| get_thread          	 | ✅      	 | 	            |
| get_thread_author   	 | 	        | 	            |
| delete_thread       	 | 	        | 	            |
| list_threads        	 | 	        | 	            |
| update_thread       	 | 	        | 	            |