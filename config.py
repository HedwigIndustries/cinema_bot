import os

TOKEN = os.getenv("TOKEN")
API = os.getenv("API")
google_headers: dict[str, str] = {'User-Agent': 'cinema_bot'}
kp_api_headers: dict[str, str] = {'X-API-KEY': API}
