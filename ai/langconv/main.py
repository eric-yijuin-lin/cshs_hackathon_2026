# ============== CLI 執行指令 ==============
# uv run --env-file .env ai/langconv/main.py
# =========================================

import os
from converter import LanguageConverter

API_KEY = os.getenv("YATING_API_KEY")
converter = LanguageConverter(api_key=API_KEY)

file_path = "./ai/langconv/sample_files/_68018194.m4a"

result = converter.audio_to_text(file_path=file_path, lang="中英", speaker_count=1)
print("語音轉文字結果:", result)
