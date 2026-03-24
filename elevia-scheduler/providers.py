import json
from typing import List
from config import PROVIDERS_FILE


def load_providers() -> List[dict]:
    with open(PROVIDERS_FILE) as f:
        return json.load(f)
