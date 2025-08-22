# tools.py
from langchain.tools import tool
import requests

@tool
def get_weather(city: str) -> str:
    """Trả về thông tin thời tiết của một thành phố."""
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    return response.text

@tool
def calculate_sum(a: int, b: int) -> int:
    """Tính tổng của hai số nguyên."""
    return a + b
