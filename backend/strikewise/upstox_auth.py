import json
import os

TOKEN_STORE_PATH = os.path.join(os.path.dirname(__file__), 'token_store.json')

def save_tokens(token_data: dict):
    with open(TOKEN_STORE_PATH, 'w') as f:
        json.dump(token_data, f)
