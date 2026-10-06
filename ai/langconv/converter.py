import requests
import time
import base64
from datetime import datetime

class LanguageConverter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.accepted_languages = ["中英", "中台"]
        self.asr_host = "https://asr.api.yating.tw/v1"
        self.tts_host = "https://tts.api.yating.tw/v2"
        self.audio_uri = ""
        self.transcription_uid = ""
        self.transcription_status = ""

    def audio_to_text(self, file_path: str, lang: str, speaker_count: int = 0) -> dict:
        self.upload_audio(file_path)
        self.request_transcription(lang, speaker_count)
        return self.get_transcription_result()

    def text_to_audio(self, text: str, lang: str) -> None:
        result = self.request_tts(lang, text)
        base64_audio = result.get('audioContent', '')
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.save_audio_file(base64_audio, f"output_{timestamp}.wav")

    def upload_audio(self, file_path: str) -> dict:
        print(f"Uploading audio file: {file_path}")
        headers = {'key': self.api_key}
        files = {'file': open(file_path, 'rb')}
        response = requests.post(f'{self.asr_host}/uploads',
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
        response = requests.post(f'{self.asr_host}/transcriptions',
                                 headers=headers,
                                 json=body)
        self.transcription_uid = response.json()[0].get('uid', '')
        self.transcription_status = response.json()[0].get('status', 'error')
        print(f"請求已發送。轉換任務 UID: {self.transcription_uid}, 狀態: {self.transcription_status}")

    def get_transcription_result(self) -> dict:
        url = f'{self.asr_host}/transcriptions/{self.transcription_uid}'
        headers = {'key': self.api_key}

        while True:
            response = requests.get(url, headers=headers)
            print(f"輪詢轉換狀態。轉換任務 UID: {self.transcription_uid}", end="")
            self.transcription_status = response.json().get("status", "error")
            print(f"...狀態: {self.transcription_status}")

            match self.transcription_status:
                case "pending" | "ongoing":
                    time.sleep(5)
                case "completed":
                    return response.json()
                case "error" | "failed":

                    raise ValueError(f"發生未預期錯誤，請檢查 API 回應: {response.json()}")

    def request_tts(self, lang: str, text: str) -> str:
        if lang not in self.accepted_languages:
            raise ValueError(f"無效的語言模型 ({lang})，只接受 '中英' or '中台'.")

        url = f'{self.tts_host}/speeches/short'
        model = "zh_en_female_1" if lang == "中英" else "tai_female_1"
        headers = {'key': self.api_key, 'Content-Type': 'application/json'}
        body = {
            "input":{
                "text":"今天天氣真好，我要出去玩",
                "type":"text"
            },
            "voice":{
                "model":model,
                "speed":1.0,
                "pitch":1.0,
                "energy":1.0
            },
            "audioConfig":{
                "encoding":"LINEAR16",
                "sampleRate":"22K"
            }
        }
        print(f"發送文字轉語音請求。URL: {url} 文字: {text} 語言: {lang}")
        response = requests.post(url, headers=headers, json=body)
        print(f"文字轉語音請求完成。")
        return response.json()

    def save_audio_file(self, base64_audio: str, file_name: str) -> None:
        audio_data = base64.b64decode(base64_audio)
        with open(file_name, 'wb') as f:
            f.write(audio_data)
        print(f"音檔已儲存為: {file_name}，音檔片段: {audio_data[:40]}")
