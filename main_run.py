import os
import json
import asyncio
import traceback
import wave
import subprocess
import platform
import time
from typing import Optional

import pyaudio
import pyperclip
from dotenv import load_dotenv

# 捕捉 genai 模組的導入錯誤
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("錯誤：缺少 'google-generativeai' 套件。")
    print("請執行 'pip install google-generativeai' 來安裝。")
    exit()

# 載入環境變數
load_dotenv()

# --- 全域常數 ---
SETTINGS_FILE = 'settings.json'
MODELS_FILE = 'models.json'
VOICES_FILE = 'voice_options.json'

# PyAudio 音訊設定
FORMAT = pyaudio.paInt16
CHANNELS = 1
RECEIVE_SAMPLE_RATE = 24000  # Gemini 原生音訊取樣率
CHUNK_SIZE = 1024

class Settings:
    """管理應用程式的所有設定，並處理載入和儲存。"""
    def __init__(self):
        self.defaults = {
            'ffmpeg_path': 'ffmpeg',
            'anki_media_path': os.path.expanduser('~/Documents/Anki2/User 1/collection.media'),
            'playback_speed': 1.0,
            'model': 'gemini-1.5-flash-preview-0514',
            'voice': 'Zephyr',
            'audio_format': 'mp3',
            'save_audio': True,
        }
        self.data = self.defaults.copy()
        self.load()

    def load(self):
        """從 JSON 檔案載入設定。"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.data.update(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告：無法載入設定檔 '{SETTINGS_FILE}'。將使用預設值。錯誤：{e}")

    def save(self):
        """將目前設定儲存到 JSON 檔案。"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"錯誤：無法儲存設定檔至 '{SETTINGS_FILE}'。錯誤：{e}")

    def get(self, key: str):
        """取得一個設定值。"""
        return self.data.get(key, self.defaults.get(key))

    def set(self, key: str, value):
        """設定一個設定值並儲存。"""
        self.data[key] = value
        self.save()

class AnkiTTS:
    """
    核心應用程式類別，處理文字轉語音、音訊播放、檔案儲存和使用者互動。
    """
    def __init__(self):
        self.settings = Settings()
        self.pya = pyaudio.PyAudio()
        self.client: Optional[genai.Client] = None
        self.config: Optional[types.LiveConnectConfig] = None
        self.session: Optional[genai.live.Session] = None
        self.audio_in_queue = asyncio.Queue()
        self._setup_client_and_config()

    def _setup_client_and_config(self):
        """根據目前設定初始化 Gemini 客戶端和 LiveConnect 設定。"""
        api_key = os.getenv("GOOGLE_GENAI_API_KEY")
        if not api_key:
            print("錯誤：找不到 Gemini API 金鑰。")
            print("請在 .env 檔案中設定 'GOOGLE_GENAI_API_KEY=YOUR_API_KEY'。")
            exit()

        try:
            # 根據 google-generativeai > 0.7.0 的變更調整
            if hasattr(genai, 'configure'):
                 genai.configure(api_key=api_key, client_options={"api_version": "v1beta"})
                 self.client = genai.GenerativeModel
            else: # 舊版相容性
                 self.client = genai.Client(
                    http_options={"api_version": "v1beta"},
                    api_key=api_key,
                )

        except Exception as e:
            print(f"錯誤：初始化 Gemini 客戶端失敗：{e}")
            exit()

        self.config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.settings.get('voice')
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part.from_text(text="You are a helpful voice assistant. Please read the user's text out loud without any extra commentary.")],
                role="user"
            ),
        )

    def _get_clipboard_text(self) -> Optional[str]:
        """安全地從剪貼簿獲取文字。"""
        try:
            return pyperclip.paste()
        except pyperclip.PyperclipException as e:
            print(f"錯誤：無法讀取剪貼簿內容。請確認您的系統已安裝 'xclip' 或 'xsel' (Linux)。錯誤：{e}")
            return None

    def _copy_to_clipboard(self, text: str):
        """將文字複製到剪貼簿。"""
        try:
            pyperclip.copy(text)
            print(f"已複製到剪貼簿：{text}")
        except pyperclip.PyperclipException as e:
            print(f"錯誤：無法複製到剪貼簿。錯誤：{e}")

    async def _play_and_save_audio(self, text_to_speak: str):
        """從佇列中取出音訊，播放並儲存到檔案。"""
        audio_frames = []
        stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=int(RECEIVE_SAMPLE_RATE * self.settings.get('playback_speed')),
            output=True,
        )
        print("模型 > ", end="", flush=True)

        try:
            while True:
                # 使用 timeout 來避免在佇列空時無限期等待
                bytestream = await asyncio.wait_for(self.audio_in_queue.get(), timeout=2.0)
                await asyncio.to_thread(stream.write, bytestream)
                if self.settings.get('save_audio'):
                    audio_frames.append(bytestream)
        except asyncio.TimeoutError:
            # 音訊串流結束
            print("\n音訊播放完畢。")
        finally:
            stream.stop_stream()
            stream.close()

        if self.settings.get('save_audio') and audio_frames:
            self._save_audio_file(audio_frames, text_to_speak)

    def _save_audio_file(self, audio_frames: list[bytes], text: str):
        """將音訊幀儲存為 WAV，並可選擇性地轉換為 MP3。"""
        media_path = self.settings.get('anki_media_path')
        if not os.path.isdir(media_path):
            print(f"錯誤：Anki Media 資料夾不存在於 '{media_path}'。")
            print("請在設定中更正路徑。音訊將不會被儲存。")
            return

        # 根據文字內容和時間戳建立一個安全的檔名
        safe_text = "".join(c for c in text if c.isalnum() or c in " _-").rstrip()
        filename_base = f"gemini_tts_{safe_text[:20]}_{int(time.time())}"
        wav_filename = f"{filename_base}.wav"
        wav_filepath = os.path.join(media_path, wav_filename)

        # 儲存 WAV 檔案
        try:
            with wave.open(wav_filepath, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.pya.get_sample_size(FORMAT))
                wf.setframerate(RECEIVE_SAMPLE_RATE)
                wf.writeframes(b''.join(audio_frames))
            print(f"已儲存 WAV 檔案至：{wav_filepath}")
        except IOError as e:
            print(f"錯誤：無法寫入 WAV 檔案。錯誤：{e}")
            return

        # 處理 MP3 轉換
        audio_format = self.settings.get('audio_format')
        if audio_format == 'mp3':
            mp3_filename = f"{filename_base}.mp3"
            mp3_filepath = os.path.join(media_path, mp3_filename)
            ffmpeg_path = self.settings.get('ffmpeg_path')
            try:
                # -y: 覆蓋輸出檔案, -i: 輸入檔案, -vn: 無影像, -ar: 音訊取樣率, -ac: 音訊聲道, -b:a: 音訊位元率
                command = [ffmpeg_path, '-y', '-i', wav_filepath, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', mp3_filepath]
                print(f"正在執行 FFmpeg 轉換：{' '.join(command)}")
                # 隱藏 FFmpeg 的輸出
                subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"已轉換 MP3 檔案至：{mp3_filepath}")
                os.remove(wav_filepath) # 刪除暫時的 WAV 檔
                anki_sound_tag = f"[sound:{mp3_filename}]"
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"錯誤：FFmpeg 轉換失敗。請確認 '{ffmpeg_path}' 已安裝並在您的系統路徑中，或在設定中指定正確路徑。")
                print(f"錯誤細節：{e}")
                anki_sound_tag = f"[sound:{wav_filename}]" # 轉檔失敗，則使用 WAV
        else: # 如果格式是 WAV
            anki_sound_tag = f"[sound:{wav_filename}]"

        self._copy_to_clipboard(anki_sound_tag)

    async def _process_text(self, text: str):
        """非同步處理單次文字轉語音請求。"""
        if not text:
            print("剪貼簿是空的，請複製一些文字。")
            return

        print("-" * 20)
        print(f"正在處理文字：{text[:100]}{'...' if len(text) > 100 else ''}")

        # 清空佇列以備新的對話
        while not self.audio_in_queue.empty():
            self.audio_in_queue.get_nowait()

        try:
            # 使用 aio (非同步) 客戶端建立連線
            # 根據 google-generativeai > 0.7.0 的變更調整
            if hasattr(self.client, 'live'): # 新版
                session_context = self.client.live.connect(model=self.settings.get('model'), config=self.config)
            else: # 舊版
                session_context = self.client.aio.live.connect(model=self.settings.get('model'), config=self.config)

            async with session_context as session:
                self.session = session

                # 建立並行任務
                play_task = asyncio.create_task(self._play_and_save_audio(text))
                
                # 傳送文字並接收音訊
                await self.session.send(input=text, end_of_turn=True)
                
                async for response in self.session.receive():
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                    if txt := response.text:
                        print(txt, end="", flush=True)

                # 等待播放和儲存任務完成
                await play_task

        except Exception as e:
            print(f"\n發生未預期的錯誤: {e}")
            traceback.print_exc()

    def run_settings_ui(self):
        """顯示並處理設定選單。"""
        while True:
            print("\n--- 設定選單 ---")
            print(f"1. FFmpeg 路徑: {self.settings.get('ffmpeg_path')}")
            print(f"2. Anki Media 資料夾: {self.settings.get('anki_media_path')}")
            print(f"3. 音訊播放速度: {self.settings.get('playback_speed')}")
            print(f"4. 使用的模型: {self.settings.get('model')}")
            print(f"5. 使用的聲音: {self.settings.get('voice')}")
            print(f"6. 儲存音訊格式: {self.settings.get('audio_format').upper()}")
            print(f"7. 儲存音訊檔案: {'是' if self.settings.get('save_audio') else '否'}")
            print("b. 返回主選單")
            
            choice = input("請選擇要修改的項目：").lower()

            if choice == '1':
                path = input("請輸入新的 FFmpeg 路徑：")
                self.settings.set('ffmpeg_path', path)
            elif choice == '2':
                path = input("請輸入新的 Anki Media 資料夾路徑：")
                self.settings.set('anki_media_path', os.path.expanduser(path))
            elif choice == '3':
                try:
                    speed = float(input("請輸入新的播放速度 (例如 1.0, 1.2)："))
                    if 0.5 <= speed <= 2.0:
                        self.settings.set('playback_speed', speed)
                    else:
                        print("速度必須在 0.5 和 2.0 之間。")
                except ValueError:
                    print("無效的輸入，請輸入數字。")
            elif choice == '4':
                self._select_from_json(MODELS_FILE, 'model', 'id', 'name')
            elif choice == '5':
                self._select_from_json(VOICES_FILE, 'voice', 'name', 'name', 'characteristics')
            elif choice == '6':
                fmt = input("請選擇格式 (mp3/wav)：").lower()
                if fmt in ['mp3', 'wav']:
                    self.settings.set('audio_format', fmt)
                else:
                    print("無效的格式。")
            elif choice == '7':
                save = input("是否要儲存音訊檔案 (y/n)？").lower()
                self.settings.set('save_audio', save == 'y')
            elif choice == 'b':
                self._setup_client_and_config() # 返回前重新載入設定
                break
            else:
                print("無效的選擇。")

    def _select_from_json(self, filename, setting_key, value_key, display_key, desc_key=None):
        """從 JSON 檔案中顯示選項並讓使用者選擇。"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 處理 models.json (list) 和 voice_options.json (dict with "options")
            options = data if isinstance(data, list) else data.get("options", [])

            if not options:
                print(f"錯誤：找不到選項於 '{filename}'")
                return

            print("\n--- 可用選項 ---")
            for i, item in enumerate(options):
                desc = f" - {item.get(desc_key, '')}" if desc_key else ""
                print(f"{i + 1}. {item.get(display_key, 'N/A')}{desc}")

            choice = input("請選擇：")
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                selected_value = options[int(choice) - 1].get(value_key)
                self.settings.set(setting_key, selected_value)
                print(f"已更新 {setting_key} 為 {selected_value}")
            else:
                print("無效的選擇。")

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"錯誤：無法載入或解析 '{filename}'。錯誤：{e}")

    async def main_loop(self):
        """應用程式的主迴圈。"""
        print("\n--- Gemini Anki TTS ---")
        while True:
            print("\n按 Enter 從剪貼簿轉換文字，'s' 進入設定，'q' 退出。")
            action = await asyncio.to_thread(input)
            
            if action.lower() == 'q':
                break
            elif action.lower() == 's':
                self.run_settings_ui()
            elif action == '':
                clipboard_text = self._get_clipboard_text()
                if clipboard_text:
                    await self._process_text(clipboard_text)
            else:
                # 允許使用者直接輸入文字
                await self._process_text(action)

    def run(self):
        """執行應用程式的主迴圈。"""
        try:
            asyncio.run(self.main_loop())
        except KeyboardInterrupt:
            print("\n偵測到使用者中斷。")
        finally:
            self.pya.terminate()
            print("程式已關閉。")


if __name__ == "__main__":
    app = AnkiTTS()
    app.run()
