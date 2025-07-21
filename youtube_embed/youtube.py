#import gradio as gr 
#from flask import Flask, request, jsonify
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import re
import yt_dlp
import requests
import uuid
import json


load_dotenv() # .env 파일 내용을 환경변수로 불러오기
youtube_api_key = os.getenv("YOUTUBE_API_KEY")

# app = Flask(__name__)		# Flask 사용 시
app = FastAPI()				# FastAPI 사용 시

def search_youtube_videos(query, max_result = 3):	# 결과값 3개 출력
	search_query = re.sub(r"영상 찾아줘|찾아줘", "", query).strip() 	# "영상 찾아줘, 찾아줘" 를 제외한 나머지 만 사용

	try:
		youtube = build('youtube', 'v3', developerKey = youtube_api_key)

		request = youtube.search().list(
			q = search_query,
			part = 'snippet',
			type = 'video',
			maxResults = max_result * 2,		# 임베드 제한 영상 걸러내게 2배수
			order = 'relevance',
			regionCode = 'KR'
		)
		response = request.execute()
		items = response.get('items', [])

		if not items:
			return {"success" : False, "html_list" : ["<div>결과 없음</div>"], "video_ids" : []}

		video_ids = [item['id']['videoId'] for item in items]		# videoId 추출

		video_response = youtube.videos().list(id = ",".join(video_ids), part = "status").execute()
		embeddable_ids = [v['id'] for v in video_response.get("items", []) if v["status"].get("embeddable", False)]

		html_list = []
		result_video_ids = []

		for item in items:
			video_id = item['id']['videoId']
			if video_id not in embeddable_ids:
				continue

			result_video_ids.append(video_id)
			embed_html = f"""
			<iframe src = "https://www.youtube.com/embed/{video_id}" frameborder = "0" allowfullscreen>
			</iframe>
			"""

			html_list.append(embed_html)
			if len(html_list) >= max_result:
				break
		if not html_list:
			return {"success" : False, "html_list" : ["<div>임베드 허용 영상 없음</div>"], "video_ids" : []}
		
		return {"success" : True, "html_list" : html_list, "video_ids" : result_video_ids}
	
	except Exception as e:
		return {"success" : False, "html_list" : [f"<div>오류 : {str(e)}</div>"], "video_ids" : []}


def extract_audio(video_url, output_format = "mp3"):

	try:
		output_path = f"audio_{uuid.uuid4().hex}.%(ext)s"
		ydl_opts = {
			'format' : 'bestaudio[ext=m4a]/bestaudio/best',
			'outtmpl' : output_path,
			'postprocessors' : [{
				'key': 'FFmpegExtractAudio',
				'preferredcodec': output_format,
				'preferredquality': '32',
			}],
			'quiet': True,
			'ffmpeg_location': r'C:/ffmpeg/bin'
		}
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			info = ydl.extract_info(video_url, download=True)
			filename = ydl.prepare_filename(info)
			audio_file = filename.rsplit('.', 1)[0] + f'.{output_format}'
			return audio_file if os.path.exists(audio_file) else None

	except Exception as e:
		print(f"오디오 추출 실패: {str(e)}")
		return None


# STT 요청
def request_stt(audio_path):
	endpoint = "https://ai-7ai0451144ai518166382125.cognitiveservices.azure.com/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
	headers = {
		"Ocp-Apim-Subscription-Key" : "BRmVMhcwHxk0u3pgZm2JKAY2PQVGX4lCKrRFk8wpXR2MgILYmEX2JQQJ99BGACHYHv6XJ3w3AAAAACOGuXmK",
		"Accept" : "application/json"
	}
	definition_obj = {
		"locales": ["ko-KR"],
		"profanityFilterMode": "Masked",
		"channels": [0,1]
	}
	with open(audio_path, "rb") as audio_file:
		files = {
			"audio" : audio_file,
			"definition": (None, json.dumps(definition_obj), "application/json")
		}
		response = requests.post(endpoint, headers=headers, files=files)
		try:
			response_json = response.json()
			phrases = response_json.get('combinedPhrases', [])
			if phrases and isinstance(phrases, list):
				# 여러 문장이 있을 수 있으니 모두 합치기
				text = "\n".join([p["text"] for p in phrases if "text" in p])
			else:
				text = ""
			return text
		except Exception as e:
			print(f"STT 응답 파싱 오류 : {e}")
			return ""

# TTS api-key, endpoint 수정완료. but not tested
def request_tts(text, voice = "ko-KR-SunHiNeural"):
	endpoint = "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1"
	headers = {
		"Ocp-Apim-Subscription-Key": "6PPozaU0ntCdmYsFCQWETpriXkMyhbZG3HSNaQZbUnYooZkgRVEFJQQJ99BGACYeBjFXJ3w3AAAYACOG3Th1",
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


# GPT 요약
def request_gpt(text):
	endpoint = "https://7ai-team3-openai.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview"
	headers = {
		"api-key": "5CpH2zbZhqXguJMMUC67YhtwWFBobt5HHOk4exzqnplefSm28AKcJQQJ99BGACHYHv6XJ3w3AAABACOGYck1",
		"Content-Type":"application/json"
	}
	body = {
		"messages": [
			{
				"role": "user",
				"content": text
			}
		],
		"max_completion_tokens": 800,
		"temperature": 1,
		"top_p": 1,
		"frequency_penalty": 0,
		"presence_penalty": 0,
		"model": "gpt-4o"
	}

	response = requests.post(endpoint, headers=headers, json=body)
	if response.status_code != 200:
		print(f"Error : {response.status_code}")
		return None
	
	response_json = response.json()
	content = response_json['choices'][0]['message']['content']
	
	return content


# 전체 요약 작성 함수
def generate_video_summary(video_url):
	try:
		# 1. 오디오 추출
		audio_path = extract_audio(video_url)
		if not audio_path:
			return "오디오 추출 실패"

		# 2. STT 변환
		transcript = request_stt(audio_path)
		if not transcript or not transcript.strip():
			return "음성이 제공되지 않은 영상입니다."

		# 3. GPT 요약
		prompt = f"다음 내용을 3-5줄로 요약해주세요:\n{transcript}"
		summary = request_gpt(prompt)

		# 4. 임시 파일 정리
		if os.path.exists(audio_path):
			os.remove(audio_path)

		return summary
	except Exception as e:
		return f"요약 생성 실패: {str(e)}"


# Flask 용
# from flask import send_from_directory
# @app.route('/')
# def index():
# 	return send_from_directory('.', 'youtube.html')
# @app.route("/youtube_embed", methods = ["POST"])

# def youtube_embed():	#Youtube 영상 임베드
# 	data = request.json
# 	query = data.get("query", "")
# 	max_results = int(data.get("max_results", 3))
# 	result = search_youtube_videos(query, max_results)
# 	return jsonify(result)

# if __name__ == "__main__":
# 	app.run(debug = True)


# FastAPI용
@app.post("/youtube_embed")
async def youtube_embed(request : Request):
	data = await request.json()
	query = data.get("query", "")
	max_results = int(data.get("max_results", 3))
	search_result = search_youtube_videos(query, max_results)		# 여기까지 기존 코드 (result->search_result)
	# return JSONResponse(content = result)

	if not search_result.get("success", False):
		return JSONResponse(content = search_result)
	
	# 각 영상별로 요약  넣기
	video_ids = search_result["video_ids"]
	html_list = search_result["html_list"]
	results = []
	for video_id, embed_html in zip(video_ids, html_list):
		video_url = f"https://www.youtube.com/watch?v={video_id}"
		summary = generate_video_summary(video_url)
		results.append({
			"video_id" : video_id,
			"embed_html" : embed_html,
			"summary" : summary
		})
	
	return JSONResponse(content = {
		"success" : True,
		"results" : results
	})


@app.post("/youtube_summary")
async def youtube_summary(request: Request):
	data = await request.json()
	video_url = data.get("video_url", "")
	summary = generate_video_summary(video_url)
	return JSONResponse(content={"summary": summary})


app.mount("/", StaticFiles(directory = ".", html = True), name = "static")