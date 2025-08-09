# 面向語言學習的生成式AI語音合成系統

這是一個使用 Google Gemini 模型將文字轉換為語音的應用程式。它能夠將剪貼簿中的文字轉換為音訊檔案，並可選擇性地將其轉換為 MP3 或 WAV 格式，特別適合搭配 Anki 記憶卡使用。

## 功能特點

- 使用 Google Gemini 生成高品質的語音音訊
- 支援從剪貼簿讀取文字
- 自動將生成的音訊檔案轉換為 MP3 或 WAV 格式 (使用者可自行選擇)
- 可調整音訊播放速度
- 與 Anki 記憶卡系統整合，自動複製 [sound:檔名] 格式到剪貼簿
- 使用者友好的設定介面

## 安裝需求

- Python 3.10 或更高版本
- FFmpeg (用於 WAV 轉 MP3)
- Google Gemini API 金鑰

## 開始使用

1. 設定環境變數 `GOOGLE_GENAI_API_KEY` 為您的 Google Gemini API 金鑰，在 `.env` 中直接設定。(GOOGLE_GENAI_API_KEY=YOUR_API_KEY)

2. 執行主程式:
   ```
   python main_run.py
   ```

## 使用方法

1. 複製您想要轉換為語音的文字到剪貼簿
2. 執行程式並按下 Enter 鍵
3. 程式會將文字轉換為語音，播放音訊，並將 MP3 或 WAV 檔案儲存到設定的 Anki Media 資料夾
4. 程式會自動將 `[sound:檔名.mp3]` 或 `[sound:檔名.wav]` 格式的文字複製到剪貼簿，方便貼到 Anki 卡片中

## 設定說明

按 's' 鍵可開啟設定介面，您可以設定:
- 設定 FFmpeg 路徑 (用於 WAV 轉 MP3)
- 設定 Anki Media 資料夾路徑
- 設定音訊播放速度
- 設定 Model used to generate response
- 設定 Voice
- 設定 MP3 或 WAV 格式
- 設定要不要將音訊檔案儲存到 Anki Media 資料夾(有可能使用者只是想聽一下，不想儲存，這時候不會複製到剪貼簿)


## 設定參考

- Model used to generate response 可以參考 models.json 中的 id
- Voice 可以參考 voice_options.json 中的 name

範例 models.json
[
    {
        "name": "Gemini 2.5 Flash Preview Native Audio Dialog",
        "id": "gemini-2.5-flash-preview-native-audio-dialog"
    },
    {
        "name": "Gemini 2.5 Flash Exp Native Audio Thinking Dialog",
        "id": "gemini-2.5-flash-exp-native-audio-thinking-dialog"
    }
]

範例 voice_options.json
{
  "options": [
    {
      "name": "Zephyr",
      "characteristics": "明亮，高音調"
    },
    {
      "name": "Puck",
      "characteristics": "活潑，中音調"
    }
  ]
}


## 基礎程式碼(參考用)

```py
import os
import asyncio
import traceback

import pyaudio

from google import genai
from google.genai import types

# --- 設定 ---

# 將 'YOUR_API_KEY' 替換成您自己的 API 金鑰
# 建議使用環境變數來管理金鑰，以策安全
# os.environ["GEMINI_API_KEY"] = "YOUR_API_KEY"

# PyAudio 音訊設定
FORMAT = pyaudio.paInt16
CHANNELS = 1
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Gemini 模型設定
MODEL = "models/gemini-1.5-flash-preview-0514"

# 建立 Gemini 用戶端
try:
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
except AttributeError:
    print("錯誤：找不到 Gemini API 金鑰。")
    print("請設定 'GEMINI_API_KEY' 環境變數或在程式碼中直接提供。")
    exit()


# LiveConnect API 連線設定
CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    system_instruction=types.Content(
        parts=[types.Part.from_text(text="You are a helpful voice assistant. Please read the user's text out loud.")],
        role="user"
    ),
)

# 初始化 PyAudio
pya = pyaudio.PyAudio()


class TextToSpeechApp:
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.session = None

    async def send_text(self):
        """非同步等待使用者輸入文字，並傳送給 API"""
        print("\n--- 開始對話 ---")
        print("請輸入您想讓模型朗讀的文字，輸入 'q' 或 'quit' 即可退出。")
        while True:
            text = await asyncio.to_thread(input, "你說 > ")
            if text.lower() in ("q", "quit"):
                print("正在結束程式...")
                break
            if text:
                # `end_of_turn=True` 表示這是一次完整的輸入，模型可以開始回應
                await self.session.send(input=text, end_of_turn=True)

    async def receive_audio(self):
        """接收來自 API 的音訊串流，並放入佇列"""
        print("模型 > ", end="", flush=True)
        while True:
            turn = self.session.receive()
            async for response in turn:
                # 將收到的音訊資料塊放入佇列
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                # 同時印出文字稿
                if text := response.text:
                    print(text, end="", flush=True)
            
            # 一輪對話結束後換行
            print("\n")

            # 清空佇列以備下次對話 (防止中斷後還有舊音訊)
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()


    async def play_audio(self):
        """從佇列中取出音訊並透過喇叭播放"""
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        """主執行函式，管理所有非同步任務"""
        try:
            # 使用 aio (非同步) 客戶端建立連線
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                
                # 建立並啟動三個並行的任務
                send_task = tg.create_task(self.send_text())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                # 等待使用者輸入 'q' 來結束 send_task
                await send_task
                # 當 send_task 結束時，發出取消請求來終止其他任務
                raise asyncio.CancelledError("使用者請求退出")

        except asyncio.CancelledError:
            pass # 正常退出
        except Exception as e:
            print(f"發生未預期的錯誤: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    try:
        app = TextToSpeechApp()
        asyncio.run(app.run())
    finally:
        # 確保 PyAudio 資源被釋放
        pya.terminate()
        print("程式已關閉。")
```