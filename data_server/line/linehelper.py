import os
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import cv2

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TextMessageV2,
    PushMessageRequest,
    MentionSubstitutionObject,
    UserMentionTarget,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import MessagingApiBlob
from linebot.v3.webhooks import (
    ImageMessageContent,
    AudioMessageContent,
)

MODES = {"car", "poo", "mention", "upload", "agent", "debug"}
NOTIFY_COLDOWN = 3

poo_type_zh_dict = {
    "poo-wet": "拉肚子",
    "poo-blood-dry": "血便（乾）",
    "poo-blood-wet": "血便（水狀）",
    "poo-green": "綠便",
    "poo-white": "白便",
}

poo_type_suggestions = {
    "poo-wet": "請多注意家人飲食，盡量吃新鮮的食物",
    "poo-blood-dry": "請持續留意是否經常發生，如果經常發生請帶家人就醫檢查",
    "poo-blood-wet": "建議盡快帶家人就醫檢查",
    "poo-green": "請留意有沒有其他腸胃感染的現象，如果持續發生請盡速就醫",
    "poo-white": "如有定期在服藥，請告知醫生有排出白便，詢問是否需要換藥。如果沒有定期服藥，請留意肝臟是否需要近一步檢查",
}


class LineMessageHelper:
    def __init__(self, car_yolo_model, poo_yolo_model):
        self.configuration = Configuration(
            access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        )

        self.handler = WebhookHandler(
            os.environ["LINE_CHANNEL_SECRET"]
        )

        self.group_id = os.environ["LINE_DEBUG_GROUP_ID"]
        self.car_model = car_yolo_model
        self.poo_model = poo_yolo_model
        self.user_modes = {}
        self.last_notify = datetime.now()

        self.mention_id_map = {
            "police": os.environ["TAG_POLICE_ID"],
            "doctor": os.environ["TAG_DOCTOR_ID"],
            "villige_chief": os.environ["TAG_VILLAGE_CHIEF_ID"],
            "family": os.environ["TAG_FAMILY_ID"],
            "social_worker": os.environ["TAG_SOCIAL_WORKER_ID"],
        }

        self.address_map = {
            "toilet_1": "南投縣 OO 鎮 XX 路 123 號"
        }

        self._register_handlers()

    def _register_handlers(self):
        # 註冊文字訊息事件 (使用 High Order Function，以後問 AI 了解一下)
        self.handler.add(
            MessageEvent,
            message=TextMessageContent
        )(lambda event: self.handle_text_message(event))

        # 註冊圖片訊息事件
        self.handler.add(
            MessageEvent,
            message=ImageMessageContent
        )(lambda event: self.handle_image_message(event))
        
        # 註冊音訊訊息事件
        self.handler.add(
            MessageEvent,
            message=AudioMessageContent
        )(lambda event: self.handle_audio_message(event))


    def handle(self, body, signature):
        self.handler.handle(body, signature)

    def handle_text_message(self, event):
        user_id = event.source.user_id
        user_text = event.message.text

        print(f"收到 LINE 訊息：{user_text}")

        # 判斷是否為指令
        if user_text.startswith(("/", "／")):
            command = user_text[1:].strip().lower()

            if command == "debug":
                print(event)
            elif command == "id":
                reply_text = user_id
            elif command in MODES:
                self.user_modes[user_id] = command
                reply_text = f"已切換至 {command} 模式"
            else:
                reply_text = f"未知指令：{command}"
        else:
            reply_text = f"Flask 收到：{user_text}"

        # 回覆 LINE 訊息
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=reply_text)
                    ],
                )
            )

    def handle_image_message(self, event):
        user_id = event.source.user_id
        message_id = event.message.id
        print(f"handling image message, user id: {user_id}    message id: {message_id}")
    
        # 從 LINE 下載圖片
        print("getting image from line api")
        with ApiClient(self.configuration) as api_client:
            blob_api = MessagingApiBlob(api_client)
            image_data = blob_api.get_message_content(message_id)
        print(f"image blob received")
    
        reply_text = "正在處理圖片"
        mode = self.user_modes[user_id]
        match mode:
            case "upload": 
                # 建立儲存資料夾
                upload_dir = Path("uploads")
                upload_dir.mkdir(exist_ok=True)
    
                # 儲存圖片
                image_path = upload_dir / f"{message_id}.jpg"
                image_path.write_bytes(image_data)
    
                print(f"圖片已儲存：{image_path}")
                reply_text = "圖片已儲存！"
                message = TextMessage(text=reply_text)
    
            case "car" | "poo":
                print("processing car/poo mode")
                # 2. Binary Data → NumPy Array → OpenCV Image
                image_array = np.frombuffer(image_data, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
                # 3. 執行 YOLO
                if image is not None:
                    print("predicting image")
                    if mode == "car":
                        results = self.car_model.predict(image, verbose=False)
                    else:
                        results = self.poo_model.predict(image, verbose=False)
    
                    result = results[0]
                    if len(result.boxes) > 0:
                        detections = []
    
                        for box in result.boxes:
                            class_id = int(box.cls[0])
                            class_name = result.names[class_id]
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    
                            detections.append(
                                f"{class_name}: ({x1}, {y1}, {x2}, {y2})"
                            )
    
                        print("object detected: ", class_name)
                        reply_text = "\n".join(detections)
    
                    else:
                        reply_text = "未偵測到任何物件"
                    message = TextMessage(text=reply_text)
    
            case "mention":
                print("[debug] 進入 mention")
                print(f"[debug] source type: {event.source.type};  user id: {user_id}")
                if event.source.type == "group" and user_id:
                    message = TextMessageV2(
                        text="{user}\nFlask 收到 @ 測試：",
                        substitution={
                            "user": MentionSubstitutionObject(
                                mentionee=UserMentionTarget(user_id=user_id)
                            )
                        }
                    )
    
            case _:
                reply_text = "圖片只支援 yolo, car 或 poo 模式"
                message = TextMessage(text=reply_text)
                        
    
        # 回覆使用者
        print(f"replying image by token: {event.reply_token}, message: {message}")
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
    
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        message
                    ],
                )
            )
        print("message replied!")

    def handle_audio_message(self, event):
        message_id = event.message.id
        duration = event.message.duration

        # 從 LINE 下載音訊
        with ApiClient(self.configuration) as api_client:
            blob_api = MessagingApiBlob(api_client)
            audio_data = blob_api.get_message_content(message_id)

        # 建立儲存資料夾
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # 儲存音訊
        audio_path = upload_dir / f"{message_id}.m4a"
        audio_path.write_bytes(audio_data)

        print(f"語音已儲存：{audio_path}")
        print(f"語音長度：{duration} ms")

        # 回覆使用者
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="語音已儲存！")
                    ],
                )
            )

    def notify(self):
        if datetime.now() - self.last_notify < timedelta(seconds=NOTIFY_COLDOWN):
            raise RuntimeError("為防止 LINE push 額度耗盡，主動觸發 Exception")

        text_template = ""
        substitutions = {}
        for role, tag_id in self.mention_id_map.items():
            text_template += f"{{{role}}}這是給{role}的訊息\n"
            substitutions[role] = MentionSubstitutionObject(
                mentionee=UserMentionTarget(
                    user_id=tag_id
                )
            )
    
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            message = TextMessageV2(
                text=text_template,
                substitution=substitutions
            )
    
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            line_bot_api.push_message(
                PushMessageRequest(
                    to=self.group_id,
                    messages=[message]
                )
            )

        self.last_notify = datetime.now()


    def alert_police(self, text_message: str) -> None:
        if datetime.now() - self.last_notify < timedelta(seconds=NOTIFY_COLDOWN):
            raise RuntimeError("為防止 LINE push 額度耗盡，主動觸發 Exception")
        
        user_id = self.mention_id_map["police"]
        
        replacements = {
            "'": "",
            "{": "",
            "}": "",
            ", ": " ",
            "start": "\n從結點",
            "end": "到結點",
            "weight": "路程",
            "direction": "角度",
            ": ": " "
        }
        
        for old, new in replacements.items():
            text_message = text_message.replace(old, new)
        text_template = "{police}\n\n" + text_message

        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            message = TextMessageV2(
                text=text_template,
                substitution={
                    "police": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=user_id
                        )
                    )
                }
            )

            line_bot_api.push_message(
                PushMessageRequest(
                    to=self.group_id,
                    messages=[message]
                )
            )
            
        self.last_notify = datetime.now()

    def alert_urgencall(self, device_id) -> None:
        if datetime.now() - self.last_notify < timedelta(seconds=NOTIFY_COLDOWN):
            raise RuntimeError("為防止 LINE push 額度耗盡，主動觸發 Exception")
        
        address = self.address_map[device_id]
        text_template = f"🚨廁所裝置 {device_id} 發出緊急呼叫！\n\n"
        text_template += f"{{social_worker}} 請立刻致電關心！\n\n"
        text_template += f"{{villige_chief}} 請立刻到 {address} 查看居民狀況 \n\n"
        text_template += f"{{doctor}} 請與里長連絡，評估是否需要派派救護車到 {address}"

        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            message = TextMessageV2(
                text=text_template,
                substitution={
                    "doctor": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["doctor"]
                        )
                    ),
                    "villige_chief": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["villige_chief"]
                        )
                    ),
                    "social_worker": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["social_worker"]
                        )
                    ),
                }
            )

            line_bot_api.push_message(
                PushMessageRequest(
                    to=self.group_id,
                    messages=[message]
                )
            )
            
        self.last_notify = datetime.now()

    def alert_csi_state(self, device_id, fast_empty: bool, long_static: bool) -> None:
        if datetime.now() - self.last_notify < timedelta(seconds=NOTIFY_COLDOWN):
            raise RuntimeError("為防止 LINE push 額度耗盡，主動觸發 Exception")
        
        address = self.address_map[device_id]
        text_template = f"🚨廁所裝置 {device_id} 偵測到 CSI 狀態異常，"
        if fast_empty:
            text_template += "使用者疑似跌倒"
        elif long_static:
            text_template += "使用者已經長時間停留在廁所"
        text_template += f"{{social_worker}} 請立刻致電關心！\n\n"
        text_template += f"{{villige_chief}} 請立刻到 {address} 查看居民狀況 \n\n"
        text_template += f"{{doctor}} 請與里長連絡，評估是否需要派派救護車到 {address}"

        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            message = TextMessageV2(
                text=text_template,
                substitution={
                    "doctor": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["doctor"]
                        )
                    ),
                    "villige_chief": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["villige_chief"]
                        )
                    ),
                    "social_worker": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["social_worker"]
                        )
                    ),
                }
            )

            line_bot_api.push_message(
                PushMessageRequest(
                    to=self.group_id,
                    messages=[message]
                )
            )

        self.last_notify = datetime.now()

    def alert_poo_type(self, device_id: str, poo_type: str) -> None:
        if poo_type == "unknown":
            print("無法辨識便便類型，不發出警報")
            return
        
        type_zh = poo_type_zh_dict[poo_type]
        suggestion = poo_type_suggestions[poo_type]
        text_template = "{family}\n\n"
        text_template += f"🚨廁所裝置 {device_id} 檢測到便便異常！\n\n"
        text_template += f"檢測到的便便類型為：{type_zh}。{suggestion}\n\n"
        text_template += "請持續關心家人的健康。"

        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            message = TextMessageV2(
                text=text_template,
                substitution={
                    "family": MentionSubstitutionObject(
                        mentionee=UserMentionTarget(
                            user_id=self.mention_id_map["family"]
                        )
                    ),
                }
            )

            line_bot_api.push_message(
                PushMessageRequest(
                    to=self.group_id,
                    messages=[message]
                )
            )
        
        self.last_notify = datetime.now()
