# batch_tts.py

from fastapi import APIRouter, Response
import requests
import os
import re
import json
import time
import datetime
import random
import zipfile
import io
from dotenv import load_dotenv

router = APIRouter()

# 환경 변수 로드
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../.env'))

tts_key = os.getenv("TTS_SUBSCRIPTION_KEY")
tts_region = "eastus"   # 분리하려면 env 등에서 관리 추천
api_version = "2024-04-01"

# 임시 오디오 저장 디렉토리 (없으면 생성)
AUDIO_TEMP_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../audio_temp')
)
if not os.path.exists(AUDIO_TEMP_DIR):
    os.makedirs(AUDIO_TEMP_DIR)

# 텍스트 정제 함수
def clean_text_for_tts(text):
    text = re.sub(r'\s*[\r\n]+\s*', '.', text)  # 줄바꿈→마침표
    pattern = r"[^가-힣a-zA-Z0-9\s.,!?~]"
    cleaned = re.sub(pattern, "", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip()
    return cleaned

# 고유 SynthesisId 만들기
def generate_synthesis_id():
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    rand = str(random.randint(10, 99))
    return f"b_{now}{rand}"

@router.post("/batch_tts")
def batch_tts(data: dict):
    text = data.get("text")
    voice = data.get("voice", "ko-KR-SunHiNeural")
    description = data.get("description", "my ssml test")
    if not text:
        print("[ERROR] 입력 text 없음")
        return Response(content="text 값이 필요합니다.", status_code=400)
    print("[INFO] 입력 텍스트 정제 시작")
    cleaned_text = clean_text_for_tts(text)
    print("[INFO] 정제된 텍스트 일부:", cleaned_text[:50], "...")

    # SSML 생성
    ssml = f'<speak version="1.0" xml:lang="ko-KR"><voice name="{voice}">{cleaned_text}</voice></speak>'
    synthesis_id = generate_synthesis_id()
    print("[INFO] Synthesis ID:", synthesis_id)

    put_url = (
        f"https://{tts_region}.api.cognitive.microsoft.com/texttospeech/batchsyntheses/"
        f"{synthesis_id}?api-version={api_version}"
    )
    put_headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": tts_key,
    }
    put_body = {
        "description": description,
        "inputKind": "SSML",
        "inputs": [{"content": ssml}],
        "properties": {
            "outputFormat": "riff-8khz-16bit-mono-pcm",
            "wordBoundaryEnabled": False,
            "sentenceBoundaryEnabled": False,
            "concatenateResult": False,
            "decompressOutputFiles": False,
        },
    }
    print("[INFO] Batch TTS PUT 요청 시작:", put_url)
    resp = requests.put(put_url, headers=put_headers, data=json.dumps(put_body))
    print(f"[Batch TTS PUT 응답] {resp.status_code} / {resp.text}")

    if resp.status_code != 201:
        print("[ERROR] Batch TTS 작업 생성 실패:", resp.text)
        return Response(content=f"Batch TTS 생성 실패\n{resp.text}", status_code=500)

    # 작업 상태 polling (GET)
    get_url = put_url
    get_headers = {"Ocp-Apim-Subscription-Key": tts_key}
    status = None
    audio_url = None

    print("[INFO] Batch TTS 상태 polling 시작")
    for i in range(18):  # 최대 90초 (5초 간격 x 18회)
        time.sleep(5)
        print(f"[POLL] {i + 1}번째 상태 조회 시도")
        get_resp = requests.get(get_url, headers=get_headers)
        if get_resp.status_code != 200:
            print("[BATCH TTS GET FAIL]", get_resp.status_code, get_resp.text)
            continue
        data = get_resp.json()
        status = data.get("status")
        print(f"[Batch TTS 상태] {status}")

        outputs = data.get("outputs", {})
        print(f"[DEBUG] outputs 타입: {type(outputs)}, 내용:", str(outputs)[:200])

        # dict 구조 지원 (outputs["result"]에 zip URL)
        if status == "Succeeded":
            if isinstance(outputs, dict) and "result" in outputs:
                audio_url = outputs["result"]
                print("[SUCCEEDED][DICT] 결과 ZIP URL:", audio_url)
                break
            # 아래는 일부 구버전/list 지원(거의 불필요하지만 견고성 차원)
            elif isinstance(outputs, list) and outputs and "outputUrl" in outputs[0]:
                audio_url = outputs[0]["outputUrl"]
                print("[SUCCEEDED][LIST] 결과 오디오 URL:", audio_url)
                break
            else:
                print("[WARN] Succeeded이지만 결과 URL 추출 실패")
                continue
        elif status in ("Failed", "Canceled"):
            print(f"[ERROR] Batch TTS 작업 실패 상태: {status}")
            break
        else:
            print("[INFO] 아직 작업 미완료(Waiting)... 다음 polling 대기")

    if status != "Succeeded" or not audio_url:
        print(f"[ERROR] Batch TTS 작업 실패 또는 Timeout (status={status})")
        return Response(content=f"Batch TTS 작업 실패 또는 Timeout (status={status})", status_code=500)

    # 결과 ZIP 파일 다운로드
    print("[INFO] 결과 ZIP 다운로드 시도:", audio_url)
    audio_resp = requests.get(audio_url)
    if audio_resp.status_code != 200:
        print(f"[ERROR] ZIP 다운로드 실패 {audio_resp.status_code} / {audio_resp.text}")
        return Response(content="오디오 ZIP 다운로드 실패", status_code=500)

    # ZIP에서 WAV 추출
    try:
        with zipfile.ZipFile(io.BytesIO(audio_resp.content)) as zf:
            wavdata = None
            selected_name = None
            for fname in zf.namelist():
                if fname.lower().endswith('.wav'):
                    with zf.open(fname) as audiofile:
                        wavdata = audiofile.read()
                        selected_name = fname
                    print("[INFO] 추출된 WAV 파일:", fname)
                    break
            if not wavdata:
                for fname in zf.namelist():
                    if fname.lower().endswith('.mp3'):
                        with zf.open(fname) as audiofile:
                            wavdata = audiofile.read()
                            selected_name = fname
                        print("[INFO] 추출된 MP3 파일:", fname)
                        break
        if not wavdata:
            print("[ERROR] ZIP 내에 wav/mp3 파일 없음:", zf.namelist())
            return Response(content="ZIP 내에 오디오(wav/mp3) 없음", status_code=500)
    except Exception as e:
        print("[ERROR] ZIP 해제 중 예외:", e)
        return Response(content=f"ZIP 파일 해제 실패: {e}", status_code=500)

    # (선택) 임시 저장 후 즉시 응답 (실제 서비스는 wavdata만 내보냄)
    filename = f"batchtts_{synthesis_id}.wav"
    filepath = os.path.join(AUDIO_TEMP_DIR, filename)
    try:
        with open(filepath, "wb") as f:
            f.write(wavdata)
        print("[INFO] WAV 임시 저장 완료:", filepath)
        with open(filepath, "rb") as f:
            wav_bytes = f.read()
        os.remove(filepath)
        print("[INFO] WAV 임시 파일 삭제 완료. audio/wav로 응답 반환.")
        return Response(wav_bytes, media_type="audio/wav")
    except Exception as e:
        print("[ERROR] 파일 저장/응답 단계에서 예외:", e)
        return Response(content=f"파일 저장 중 에러 발생: {e}", status_code=500)