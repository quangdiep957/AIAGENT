from langchain.tools import tool
import os
import openai
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

def get_flashcards_from_openai(topic: str, n_words: int = 10) -> str:
    """
    Gọi OpenAI API để sinh danh sách từ vựng tiếng Anh theo chủ đề.
    Đầu vào: topic (chủ đề), n_words (số lượng từ vựng, mặc định 10)
    Đầu ra: danh sách từ vựng dạng 'word: meaning' mỗi dòng một cặp.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Lỗi: Chưa cấu hình OPENAI_API_KEY trong biến môi trường."
    openai.api_key = api_key
    prompt = (
        f"Hãy liệt kê {n_words} từ vựng tiếng Anh về chủ đề \"{topic}\", "
        "kèm nghĩa tiếng Việt, mỗi dòng một cặp theo định dạng: word: meaning."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.7,
        )
        content = response['choices'][0]['message']['content']
        return content.strip()
    except Exception as e:
        return f"Lỗi khi gọi OpenAI API: {str(e)}"

def generate_flashcard_image(english: str, vietnamese: str, save_path: str = None) -> Image.Image:
    """
    Sinh flashcard ảnh: trên là tiếng Anh, giữa là ảnh minh họa (OpenAI DALL·E), dưới là tiếng Việt.
    Trả về đối tượng PIL Image hoặc lưu ra file nếu có save_path.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("Chưa cấu hình OPENAI_API_KEY trong biến môi trường.")
    openai.api_key = api_key

    # Gọi OpenAI DALL·E để sinh ảnh minh họa
    dalle_prompt = f"A simple illustration of {english} for language learning, white background, no text"
    try:
        dalle_response = openai.Image.create(
            prompt=dalle_prompt,
            n=1,
            size="256x256"
        )
        image_url = dalle_response['data'][0]['url']
        img_data = requests.get(image_url).content
        illustration = Image.open(BytesIO(img_data)).convert("RGBA")
    except Exception as e:
        # Nếu lỗi, tạo ảnh trắng thay thế
        illustration = Image.new("RGBA", (256, 256), (255, 255, 255, 255))

    # Tạo flashcard: 256x400 (trên: 60, giữa: 256, dưới: 84)
    card_w, card_h = 256, 400
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Font
    try:
        font_en = ImageFont.truetype("arial.ttf", 32)
    except:
        font_en = None  # fallback default

    # Load NataSans font cho tiếng Việt
    try:
        font_vi = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "../NataSans-VariableFont_wght.ttf"), 24)
    except:
        font_vi = None  # fallback default

    # Vẽ tiếng Anh phía trên
    en_text = english
    en_w, en_h = draw.textsize(en_text, font=font_en)
    draw.text(((card_w - en_w) // 2, 10), en_text, fill=(0, 0, 0), font=font_en)

    # Dán ảnh minh họa vào giữa
    card.paste(illustration, (0, 60), illustration)

    # Vẽ tiếng Việt phía dưới
    vi_text = vietnamese
    vi_w, vi_h = draw.textsize(vi_text, font=font_vi)
    draw.text(((card_w - vi_w) // 2, 330), vi_text, fill=(80, 80, 80), font=font_vi)

    if save_path:
        card.save(save_path)
    return card

@tool
def generate_flashcard(topic: str) -> str:
    """
    Sinh flashcard từ vựng tiếng Anh theo chủ đề bằng OpenAI.
    Đầu vào: tên chủ đề (ví dụ: 'animals', 'fruits', 'jobs').
    Đầu ra: danh sách từ vựng dạng 'word: meaning' mỗi dòng một cặp.
    Nếu có lỗi sẽ trả về thông báo lỗi.
    Ngoài ra, tạo tối đa 10 ảnh flashcard minh họa cho từng cặp từ vựng (lưu vào thư mục 'uploads/').
    """
    result = get_flashcards_from_openai(topic, n_words=10)
    print(f"[LOG] Tool used: generate_flashcard | input={topic}")
    # Parse kết quả thành list (english, vietnamese)
    pairs = []
    for line in result.splitlines():
        if ":" in line:
            en, vi = line.split(":", 1)
            pairs.append((en.strip(), vi.strip()))
        if len(pairs) >= 10:
            break
    # Tạo ảnh flashcard cho từng cặp
    img_paths = []
    os.makedirs("uploads", exist_ok=True)
    for idx, (en, vi) in enumerate(pairs):
        img_path = f"uploads/flashcard_{topic}_{idx+1}.png"
        try:
            generate_flashcard_image(en, vi, save_path=img_path)
            img_paths.append(img_path)
        except Exception as e:
            print(f"[ERROR] Không tạo được ảnh cho {en}: {e}")
    # Trả về danh sách từ vựng và đường dẫn ảnh
    result_text = "\n".join([f"{en}: {vi} (ảnh: {img_path})" for (en, vi), img_path in zip(pairs, img_paths)])
    return result_text if result_text else result
