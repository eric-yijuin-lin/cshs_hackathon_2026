# ============== CLI 執行指令 ==============
# uv run --env-file .env ai/langconv/main.py
# =========================================

import os
from converter import LanguageConverter

API_KEY = os.getenv("YATING_API_KEY")
converter = LanguageConverter(api_key=API_KEY)

# ============= 測試語音轉文字 ==============
# file_path = "./ai/langconv/sample_files/_68018194.m4a"
# result = converter.audio_to_text(file_path=file_path, lang="中英", speaker_count=1)
# print("語音轉文字結果:", result)

# ============= 測試文字轉語音 ==============
text = "今天天氣真好，我要出去玩"
converter.text_to_audio(text=text, lang="中台")
