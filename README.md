# AnkiVox_v2
面向語言學習的生成式AI語音合成系統
這是一個使用 Google Gemini 模型將文字轉換為語音的應用程式。它能夠將剪貼簿中的文字轉換為音訊檔案，並可選擇性地將其轉換為 MP3 或 WAV 格式，特別適合搭配 Anki 記憶卡使用。

功能特點
使用 Google Gemini 生成高品質的語音音訊

支援從剪貼簿讀取文字

自動將生成的音訊檔案轉換為 MP3 或 WAV 格式 (使用者可自行選擇)

可調整音訊播放速度

與 Anki 記憶卡系統整合，自動複製 [sound:檔名] 格式到剪貼簿

使用者友好的設定介面，可動態選擇模型和語音風格

自動偵測 FFmpeg 路徑

安裝需求
Python 3.10 或更高版本

FFmpeg: 如果您想將音訊儲存為 MP3 格式，則必須安裝。

Windows: 從 ffmpeg.org 下載，並將 bin 資料夾的路徑加入到系統的環境變數 PATH 中，或者在程式的設定介面中手動指定 ffmpeg.exe 的完整路徑。

macOS: 使用 Homebrew 安裝: brew install ffmpeg

Linux: 使用套件管理器安裝: sudo apt-get install ffmpeg

Google Gemini API 金鑰

專案檔案結構
/your_project_folder
|-- main_run.py             # 主執行程式
|-- config.json             # (自動生成) 儲存使用者設定
|-- models.json             # 可用的 Gemini 模型列表
|-- voice_options.json      # 可用的語音風格列表
|-- .env                    # (需手動建立) 儲存您的 API 金鑰
|-- requirements.txt        # Python 套件依賴
|-- AnkiMedia/              # (自動生成) 預設存放音訊檔的資料夾

開始使用
安裝 Python 套件
建立一個名為 requirements.txt 的檔案，並填入以下內容：

google-generativeai
pyaudio
pyperclip
python-dotenv

然後在您的終端機中執行以下指令來安裝所有必要的套件：

pip install -r requirements.txt

設定 API 金鑰
將 .env.example 檔案重新命名為 .env。用文字編輯器打開 .env 檔案，將 YOUR_API_KEY 替換成您自己的 Google Gemini API 金鑰。

GOOGLE_GENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxx

執行主程式
在終端機中執行主程式：

python main_run.py

程式第一次執行時，會自動建立 config.json 設定檔和 AnkiMedia 資料夾。

使用方法
複製您想要轉換為語音的文字到剪貼簿 (例如，從網頁或文件中複製一個單字或句子)。

切換到執行程式的終端機視窗，直接按下 Enter 鍵。

程式會自動抓取剪貼簿的文字，並開始進行語音合成。

合成完成後，程式會自動播放音訊，並將 MP3 或 WAV 檔案儲存到設定的 Anki Media 資料夾中。

程式會自動將 [sound:檔名.mp3] 或 [sound:檔名.wav] 格式的文字複製到剪貼簿。

您可以直接到 Anki 的卡片編輯器中貼上 (Ctrl+V 或 Cmd+V)。

設定說明
在程式主畫面輸入 s 並按下 Enter 鍵，即可進入設定介面。您可以設定：

FFmpeg 路徑: 如果程式無法自動找到 FFmpeg，您可以在此手動指定 ffmpeg.exe (或 ffmpeg) 的完整路徑。

Anki Media 資料夾路徑: 指定音訊檔案的儲存位置。您可以將其設定為您 Anki 收藏的 collection.media 資料夾，這樣音訊就可以直接在 Anki 中使用。

音訊播放速度: 調整播放速度，方便語言學習。1.0 為正常速度，0.8 為慢速，1.2 為快速。

Gemini 模型: 從 models.json 中選擇不同的文字轉語音模型。

語音風格 (Voice): 從 voice_options.json 中選擇您喜歡的聲音。

儲存音訊格式: 選擇將檔案儲存為 MP3 (檔案較小) 或 WAV (不需轉換，但檔案較大)。