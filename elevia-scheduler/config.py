import os
from dotenv import load_dotenv

load_dotenv()

PROVIDERS_FILE = os.path.join(os.path.dirname(__file__), "connecticut_psychiatry_providers.json")
GOOGLE_CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")
