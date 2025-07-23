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


def request_tts(text, voice="ko-KR-SunHiNeural"):
	endpoint = tts_endpoint
	headers = {
		"Ocp-Apim-Subscription-Key": tts_key,
		"X-Microsoft-OutputFormat" : "riff-8khz-16bit-mono-pcm",
		"Content-Type" : "application/ssml+xml"
	}

	body = f"""
		<speak version='1.0' xml:lang='en-US'>
			<voice xml:lang='ko-KR' xml:gender='Female' name='ko-KR-SunHiNeural'>
				{text}
			</voice>
		</speak>
	"""
	response = requests.post(endpoint, headers = headers, data = body)

	if response.status_code != 200:
		print(f"Error : {response.status_code}")
		return None

	import datetime
	now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

	filename = f"tts_result_{now}.wav"

	with open(filename, "wb") as audio_file:
		audio_file.write(response.content)

	return filename

@router.post("/tts")
def text_to_speech_endpoint(data: dict):
    text = data["text"]
    filename = request_tts(text)
    if filename and os.path.exists(filename):
        with open(filename, "rb") as audio:
            wav = audio.read()
        os.remove(filename)
        return Response(wav, media_type="audio/wav")
    else:
        return Response(content="TTS 생성 실패", status_code=500)
