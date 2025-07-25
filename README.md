# AnkiVox_v2

AnkiVox_v2 是一個利用 Google Gemini API 將文字轉換為語音的工具，特別為 Anki 使用者設計，可以方便地生成語音檔案並自動產生 Anki 音訊標籤。

## 功能

*   透過 Google Gemini API 將文字轉換為高品質語音。
*   支援多種語音和模型選擇。
*   可選擇儲存為 WAV 或 MP3 格式。
*   自動將生成的 Anki 音訊標籤 `[sound:檔名]` 複製到剪貼簿。
*   提供簡單的文字介面來調整設定。
*   使用非同步處理，在生成音訊時保持應用程式的回應性。

## 安裝

1.  **安裝必要的 Python 套件:**

    ```bash
    pip install google-generativeai python-dotenv pyaudio pyperclip
    ```

2.  **安裝 FFmpeg (選用):**
    如果您想將音訊儲存為 MP3 格式，您需要在您的系統上安裝 FFmpeg。請參考 [FFmpeg 官網](https://ffmpeg.org/download.html) 的說明進行安裝，並確保 `ffmpeg` 指令在您的系統路徑中。

## 設定

1.  **建立 `.env` 檔案:**

    在與 `main_run.py` 相同的資料夾中建立一個名為 `.env` 的檔案，並貼上您的 Google Gemini API 金鑰：

    ```
    GOOGLE_GENAI_API_KEY=YOUR_ACTUAL_API_KEY
    ```
    請將 `YOUR_ACTUAL_API_KEY` 替換為您自己的 API 金鑰。

2.  **程式設定 (`settings.json`):**

    程式的設定儲存在 `settings.json` 檔案中。您可以直接編輯此檔案，或在程式執行時輸入 `s` 進入設定介面進行修改。

    *   `model`: 要使用的 Gemini 模型 (例如 `models/text-to-speech`)。
    *   `voice`: 要使用的語音 (例如 `zh-TW-Standard-A`)。
    *   `save_audio`: 是否儲存音訊檔案 (`true` 或 `false`)。
    *   `audio_format`: 儲存的音訊格式 (`wav` 或 `mp3`)。
    *   `audio_folder`: 儲存音訊檔案的資料夾。

## 程式架構說明

### `Settings` 類別
這個類別負責處理所有設定。當程式第一次啟動時，如果 `settings.json` 不存在，它會使用預設值。任何透過設定介面所做的變更都會被儲存，以便下次啟動時使用。

### `AnkiTTS` 類別

*   `__init__`: 初始化所有必要的元件，包括設定、PyAudio 和 Gemini 客戶端。

*   `_setup_client_and_config`: 這是個重要的輔助函式，它會根據 `settings.json` 中的 `model` 和 `voice` 來設定 Gemini API 的連線參數。當您在設定介面中更改這些選項後，它會被重新呼叫以套用變更。

*   `_process_text`: 這是非同步的核心函式。它建立一個與 Gemini 的 `live.connect` 會話，然後同時執行三個任務：傳送文字給 API、非同步地接收音訊串流，以及將收到的音訊串流播放出來並儲存。

*   `_play_and_save_audio`: 這個函式負責播放音訊。如果設定為儲存檔案，它會將音訊數據收集在 `audio_frames` 列表中。

*   `_save_audio_file`: 播放結束後，此函式會被呼叫。它首先將音訊數據寫入一個 `.wav` 檔案。如果使用者選擇了 MP3 格式，它會使用 `subprocess` 模組呼叫系統中的 FFmpeg 程式來進行轉檔，成功後刪除原始的 WAV 檔。最後，它會產生正確的 `[sound:檔名]` 標籤並複製到剪貼簿。

*   `run_settings_ui`: 提供一個簡單的文字介面，讓使用者可以輕鬆地修改所有可用的設定。

*   `main_loop`: 程式的主迴圈，等待使用者的指令。

### 非同步 (asyncio)
使用 `asyncio` 是為了能同時處理多個 I/O 密集的任務：等待使用者輸入、傳送資料到網路、從網路接收資料，以及播放音訊。這使得應用程式在處理音訊時依然能保持回應。

## 使用方法

1.  執行主程式:
    ```bash
    python main_run.py
    ```
2.  程式啟動後，會顯示目前的設定。
3.  直接輸入您想轉換為語音的文字，然後按下 Enter。
4.  程式會即時播放語音，如果設定為儲存，則會將音訊檔儲存到指定資料夾，並將 Anki 標籤複製到剪貼簿。
5.  輸入 `s` 進入設定介面。
6.  輸入 `q` 或 `exit` 結束程式。