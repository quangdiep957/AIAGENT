# tools.py
from langchain.tools import tool
import requests

@tool
def get_weather(city: str) -> str:
    """Trả về thông tin thời tiết của một thành phố."""
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    print(f"[LOG] Tool used: get_weather | input={city}")
    return response.text

@tool
def calculate_sum(numbers: str) -> str:
    """Tính tổng của hai số nguyên được cung cấp dưới dạng chuỗi cách nhau bằng dấu phẩy. Ví dụ: '5,3' sẽ trả về 8."""
    try:
        # Tách chuỗi thành các số
        num_list = [int(x.strip()) for x in numbers.split(',')]
        if len(num_list) != 2:
            return "Lỗi: Tool chỉ hỗ trợ đúng 2 số, cách nhau bằng dấu phẩy"
        
        a, b = num_list
        result = a + b
        print(f"[LOG] Tool used: calculate_sum | input={numbers}")
        return f"Tổng của {a} + {b} = {result}"
    except ValueError:
        return "Lỗi: Vui lòng nhập đúng định dạng số, ví dụ: '5,3'"
