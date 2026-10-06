import requests
import time

class LanguageConverter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.accepted_languages = ["中英", "中台"]
        self.api_root = "https://asr.api.yating.tw/v1"
        self.audio_uri = ""
        self.transcription_uid = ""
        self.transcription_status = ""

    def audio_to_text(self, file_path: str, lang: str, speaker_count: int = 0) -> dict:
        self.upload_audio(file_path)
        self.request_transcription(lang, speaker_count)
        return self.get_transcription_result()

    def upload_audio(self, file_path: str) -> dict:
        print(f"Uploading audio file: {file_path}")
        headers = {'key': self.api_key}
        files = {'file': open(file_path, 'rb')}
        response = requests.post(f'{self.api_root}/uploads',
                                 headers=headers,
                                 files=files)
        self.audio_uri = response.json().get('url', '')
        print(f"上傳完成，音檔 uri: {self.audio_uri}")

    # [{'id': 2474531, 'uid': '9658653c-5c17-4d6a-89b9-0aac1f74ab4a', 'audioUri': 'yd://1c45c6f7-6a4e-471b-ad34-02d1fb59d81b', 'model': 'asr-zh-en-std', 'customLm': '', 'isPunctuation': 1, 'isSpeakerDiarization': 0, 'speakerCount': 0, 'isSentiment': 0, 'status': 'pending', 'audioDuration': 0, 'createdAt': '2026-10-06T00:23:40.756Z', 'updatedAt': '2026-10-06T00:23:40.756Z'}]
    def request_transcription(self, lang: str, speaker_count: int = 0) -> dict:
        print(f"發送語音轉文字請求。音檔 uri: {self.audio_uri} 語言: {lang} 人數: {speaker_count}")
        if lang not in self.accepted_languages:
            raise ValueError(f"無效的語言模型 ({lang})，只接受 '中英' or '中台'.")
        
        model = "asr-zh-en-std" if lang == "中英" else "asr-zh-tw-std"
        headers = {'key': self.api_key, 'Content-Type': 'application/json'}
        body = {
            'audioUri': self.audio_uri,
            "modelConfig": {
                "model": model,
                "customLm": ""
            },
            "featureConfig": {
                "speakerDiarization": False,
                "speakerCount": speaker_count,
                "sentiment": False
            }
        }
        response = requests.post(f'{self.api_root}/transcriptions',
                                 headers=headers,
                                 json=body)
        self.transcription_uid = response.json()[0].get('uid', '')
        self.transcription_status = response.json()[0].get('status', 'error')
        print(f"請求已發送。轉換任務 UID: {self.transcription_uid}, 狀態: {self.transcription_status}")

    def get_transcription_result(self) -> dict:
        print(f"輪詢轉換狀態。轉換任務 UID: {self.transcription_uid}")
        url = f'{self.api_root}/transcriptions/{self.transcription_uid}'
        headers = {'key': self.api_key}

        while self.transcription_status != "completed":
            response = requests.get(url, headers=headers)
            self.transcription_status = response.json().get("status", "error")
            if self.transcription_status == "error" or self.transcription_status == "failed":
                raise ValueError(f"發生未預期錯誤，請檢查 API 回應: {response.json()}")
            print(f"目前轉換狀態: {self.transcription_status}。5 秒後重新查詢...")
            time.sleep(5)
        return response.json()
