import os
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

class LineMessageHelper:
    def __init__(self):
        self.configuration = Configuration(
            access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        )

        self.handler = WebhookHandler(
            os.environ["LINE_CHANNEL_SECRET"]
        )

        self.tag_id_map = {
            "police": os.environ["TAG_POLICE_ID"],
            "doctor": os.environ["TAG_DOCTOR_ID"],
            "villige_chief": os.environ["TAG_VILLAGE_CHIEF_ID"],
            "family": os.environ["TAG_FAMILY_ID"],
            "social_worker": os.environ["TAG_SOCIAL_WORKER_ID"],
        }

        self._register_handlers()

    def _register_handlers(self):
        # 註冊文字訊息事件
        self.handler.add(
            MessageEvent, message=TextMessageContent
        )(self.handle_text_message)

        # 註冊圖片訊息事件
        self.handler.add(
            MessageEvent, message=ImageMessageContent
        )(self.handle_image_message)

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
                user_modes[user_id] = command
                reply_text = f"已切換至 {command} 模式"
            else:
                reply_text = f"未知指令：{command}"
        else:
            reply_text = f"Flask 收到：{user_text}"

        # 回覆 LINE 訊息
        with ApiClient(configuration) as api_client:
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
        print("收到圖片：", event.message.id)

        self.reply_text(event.reply_token, "收到圖片")

    def reply_text(self, reply_token, text):
        with ApiClient(self.configuration) as api_client:
            api = MessagingApi(api_client)

            api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)]
                )
            )






