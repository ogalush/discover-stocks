import os
import requests

class notification:
    def __init__(self, api_token: str, room_id: str):
        if not api_token:
            raise ValueError("api_token が空です")
        if not room_id:
            raise ValueError("room_id が空です")

        self.api_token = api_token
        self.room_id = room_id
        self.headers = {
            "X-ChatWorkToken": self.api_token
        }


    def post_message(self, message: str):
        res = requests.post(
            f"https://api.chatwork.com/v2/rooms/{self.room_id}/messages",
            headers=self.headers,
            data={"body": message},
            timeout=10
        )
        res.raise_for_status()


    def post_image(self, image_path: str, caption: str = "添付画像"):
        with open(image_path, "rb") as img:
            res = requests.post(
                f"https://api.chatwork.com/v2/rooms/{self.room_id}/files",
                headers=self.headers,
                files={"file": img},
                data={"message": caption},
                timeout=30
            )
            res.raise_for_status()

    def notify(self, text_path: str, image_path: str):
        with open(text_path, encoding="utf-8") as f:
            message = f.read()

        self.post_message(message)
        self.post_image(image_path)