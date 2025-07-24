# routers/tts.py
from fastapi import APIRouter, Response
import requests
from dotenv import load_dotenv
import os

router = APIRouter()

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../.env'))

tts_endpoint = os.getenv("TTS_ENDPOINT")
tts_key = os.getenv("TTS_SUBSCRIPTION_KEY")

AUDIO_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../audio_temp'))


def request_tts(text, voice="ko-KR-SunHiNeural"):
	endpoint = tts_endpoint
	headers = {
		"Ocp-Apim-Subscription-Key": tts_key,
		"X-Microsoft-OutputFormat" : "riff-8khz-16bit-mono-pcm",
		"Content-Type" : "application/ssml+xml"
	}

	body = f"""
		<speak version='1.0' xml:lang='ko-KR'>
			<voice xml:lang='ko-KR' xml:gender='Female' name='ko-KR-SunHiNeural'>
				{text}
			</voice>
		</speak>
	"""
	response = requests.post(endpoint, headers = headers, data = body)
	print("TTS API Status:", response.status_code)
	print("TTS API Body:", response.text)

	if response.status_code != 200:
		print(f"Error : {response.status_code}")
		return None

	import datetime
	now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

	filename = f"tts_result_{now}.wav"
	filepath = os.path.join(AUDIO_TEMP_DIR, filename)

	with open(filepath, "wb") as audio_file:
		audio_file.write(response.content)

	print("AUDIO_TEMP_DIR:", AUDIO_TEMP_DIR)
	print("filepath:", filepath)
	print("text:", text)
	
	return filepath

# @router.post("/tts")
# def text_to_speech_endpoint(data: dict):
#     text = data["text"]
#     filepath = request_tts(text)
#     if filepath and os.path.exists(filepath):
#         with open(filepath, "rb") as audio:
#             wav = audio.read()
#         os.remove(filepath)
#         return Response(wav, media_type="audio/wav")
#     else:
#         return Response(content="TTS 생성 실패", status_code=500)

@router.post("/tts")
def text_to_speech_endpoint(data: dict):
    text = data["text"]
    filepath = request_tts(text)
    print("==== WAV 파일 존재?", filepath, os.path.exists(filepath))
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
