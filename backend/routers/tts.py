# routers/tts.py

from fastapi import APIRouter, Response
import requests
from dotenv import load_dotenv
import os
import re

router = APIRouter()

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../.env'))

tts_endpoint = os.getenv("TTS_ENDPOINT")
tts_key = os.getenv("TTS_SUBSCRIPTION_KEY")

AUDIO_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../audio_temp'))   # 임시 오디오 파일 생성 폴더 경로 지정
if not os.path.exists(AUDIO_TEMP_DIR):      # 없으면 폴더 생성
    os.makedirs(AUDIO_TEMP_DIR)

def clean_text_for_tts(text, max_length=9000):
    # 줄바꿈(\n, \r\n 등)을 마침표로 변경
    text = re.sub(r'\s*[\r\n]+\s*', '.', text)
    # 한글, 영문, 숫자, 공백, . , ! ? ~ 만 허용. 나머지는 삭제
    pattern = r"[^가-힣a-zA-Z0-9\s.,!?~]"
    cleaned = re.sub(pattern, "", text)
    # 연속된 공백은 하나로
    cleaned = re.sub(r"\s+", " ", cleaned)
    # 앞뒤 공백 제거
    cleaned = cleaned.strip()
    # 길이 제한
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned

def request_tts(text, voice="ko-KR-SunHiNeural"):
    endpoint = tts_endpoint
    headers = {
        "Ocp-Apim-Subscription-Key": tts_key,
        "X-Microsoft-OutputFormat" : "riff-8khz-16bit-mono-pcm",
        "Content-Type" : "application/ssml+xml"
    }

    # 텍스트 정제
    cleaned_text = clean_text_for_tts(text)
    body = f"""
        <speak version='1.0' xml:lang='ko-KR'>
            <voice xml:lang='ko-KR' xml:gender='Female' name='{voice}'>
                {cleaned_text}
            </voice>
        </speak>
    """

    response = requests.post(endpoint, headers=headers, data=body.encode('utf-8'))
    print("TTS API Status:", response.status_code)
    print("TTS API Body:", response.text)

    if response.status_code != 200:
        print(f"Error : {response.status_code}")
        return None

    import datetime
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tts_result_{now}.wav"
    filepath = os.path.join(AUDIO_TEMP_DIR, filename)

    if not filepath:
        raise ValueError("filepath가 할당되지 않았거나 None입니다.")

    with open(filepath, "wb") as audio_file:
        audio_file.write(response.content)

    print("AUDIO_TEMP_DIR:", AUDIO_TEMP_DIR)
    print("filepath:", filepath)
    print("text:", cleaned_text)

    return filepath

@router.post("/tts")
def text_to_speech_endpoint(data: dict):
    text = data.get("text", "")
    voice = data.get("voice", "ko-KR-SunHiNeural")  # voice 파라미터 받도록 확장
    filepath = request_tts(text, voice)
    if filepath is not None:
        print("==== WAV 파일 존재?", filepath, os.path.exists(filepath))
    else:
        print("filepath is None")

    if filepath and os.path.exists(filepath):
        print("== 파일 오픈 시도")
        with open(filepath, "rb") as audio:
            wav = audio.read()
            print("== wav 바이트 수:", len(wav))
        print("== 파일 삭제 시도")
        os.remove(filepath)
        print("== 파일 삭제 완료, 응답 반환")
        return Response(wav, media_type="audio/wav")
    else:
        print("== 파일 없음/실패 응답")
        return Response(content="TTS 생성 실패", status_code=500)

# 예시: Voice 선택 및 히스토리 기반 텍스트 정제, TTS 호출
def text_to_voice_bot(histories, voice="ko-KR-SunHiNeural"):
    if not histories or "content" not in histories[-1]:
        return None
    content = histories[-1]["content"]
    cleaned_content = clean_text_for_tts(content)
    filepath = request_tts(cleaned_content, voice)
    return filepath
