from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
import re
import yt_dlp
import requests
import uuid
import json

load_dotenv()   # .env 파일 내용을 환경변수로 불러오기
youtube_api_key = os.getenv("YOUTUBE_API_KEY")
stt_endpoint = os.getenv("STT_ENDPOINT")
stt_key = os.getenv("STT_SUBSCRIPTION_KEY")
tts_endpoint = os.getenv("TTS_ENDPOINT")
tts_key = os.getenv("TTS_SUBSCRIPTION_KEY")
gpt_endpoint = os.getenv("GPT_ENDPOINT")
gpt_key = os.getenv("GPT_SUBSCRIPTION_KEY")

# app = Flask(__name__)		# Flask 사용 시
app = FastAPI()				# FastAPI 사용 시


def search_youtube_videos(query, max_result=3):
    print(f"\n[search_youtube_videos] 시작: {query}")
    search_query = re.sub(r"영상 찾아줘|찾아줘", "", query).strip() 	# "영상 찾아줘, 찾아줘" 를 제외한 나머지 만 사용

    try:
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        request = youtube.search().list(
            q=search_query,
            part='snippet',
            type='video',
            maxResults=max_result * 2,		# 임베드 제한 영상 걸러내게 2배수
            order='relevance',
            regionCode='KR'
        )
        response = request.execute()
        items = response.get('items', [])
        print(f"[search_youtube_videos] API 결과 개수: {len(items)}")

        if not items:
            print("[search_youtube_videos] 검색 결과 없음")
            return {"success": False, "html_list": ["<div>결과 없음</div>"], "video_ids": []}

        video_ids = [item['id']['videoId'] for item in items]
        video_response = youtube.videos().list(id=",".join(video_ids), part="status").execute()
        embeddable_ids = [v['id'] for v in video_response.get("items", []) if v["status"].get("embeddable", False)]

        html_list = []
        result_video_ids = []
        for item in items:
            video_id = item['id']['videoId']
            if video_id not in embeddable_ids:
                continue
            result_video_ids.append(video_id)
            embed_html = f"""
            <iframe src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>
            """
            html_list.append(embed_html)
            if len(html_list) >= max_result:
                break
        print(f"[search_youtube_videos] 임베드 허용 영상: {result_video_ids}")
        if not html_list:
            print("[search_youtube_videos] 임베드 허용 없음")
            return {"success": False, "html_list": ["<div>임베드 허용 영상 없음</div>"], "video_ids": []}
        print("[search_youtube_videos] 종료")
        return {"success": True, "html_list": html_list, "video_ids": result_video_ids}
    except Exception as e:
        print(f"[search_youtube_videos] 예외: {e}")
        return {"success": False, "html_list": [f"<div>오류 : {str(e)}</div>"], "video_ids": []}


def extract_audio(video_url, output_format="mp3"):
    print(f"[extract_audio] 오디오 추출 시작: {video_url}")
    try:
        output_path = f"audio_{uuid.uuid4().hex}.%(ext)s"
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
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
            print(f"[extract_audio] 파일: {audio_file} / 존재: {os.path.exists(audio_file)}")
            return audio_file if os.path.exists(audio_file) else None
    except Exception as e:
        print(f"[extract_audio] 예외: {e}")
        return None


# STT 요청
def request_stt(audio_path):
    print(f"[request_stt] STT 변환 요청: {audio_path}")
    endpoint = stt_endpoint
    headers = {
        "Ocp-Apim-Subscription-Key" : stt_key,
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
        print(f"[request_stt] 응답 코드: {response.status_code}")
        try:
            response_json = response.json()
            phrases = response_json.get('combinedPhrases', [])
            print(f"[request_stt] phrases 개수: {len(phrases)}")
            if phrases and isinstance(phrases, list):
                text = "\n".join([p["text"] for p in phrases if "text" in p])
            else:
                text = ""
            if text:
                print(f"[request_stt] 텍스트 추출 성공 (길이: {len(text)})")
            else:
                print("[request_stt] 무음/실패")
            return text
        except Exception as e:
            print(f"[request_stt] 예외: {e}")
            return ""


# TTS api-key, endpoint 수정완료. but not tested
def request_tts(text, voice = "ko-KR-SunHiNeural"):
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


# GPT 요약
def request_gpt(text):
    print(f"[request_gpt] 요약 요청 (길이: {len(text)})")
    if not text or not text.strip():
        print("[request_gpt] 입력 없음 → 음성 미제공")
        return "음성이 제공되지 않은 영상입니다."
    endpoint = gpt_endpoint
    headers = {
        "api-key": gpt_key,
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
    print(f"[request_gpt] 응답 코드: {response.status_code}")
    if response.status_code != 200:
        print(f"[request_gpt] 에러: {response.text}")
        return None
    response_json = response.json()
    content = response_json['choices'][0]['message']['content']
    print(f"[request_gpt] 요약 결과: {content[:50]} ...")
    return content

# 전체 요약 작성 함수
def generate_video_summary(video_url):
    print(f"\n[generate_video_summary] === {video_url} === 요약 시작 ===")
    try:
        # 1. 오디오 추출
        print("[generate_video_summary] 1. 오디오 추출")
        audio_path = extract_audio(video_url)
        if not audio_path:
            print("[generate_video_summary] 오디오 추출 실패")
            return "오디오 추출 실패"

        # 2. STT 변환
        print("[generate_video_summary] 2. STT 변환")
        transcript = request_stt(audio_path)
        if not transcript or not transcript.strip():
            print("[generate_video_summary] STT 결과 없음 → 무음 영상")
            # 음성이 없을 때도 임시 오디오 파일 삭제
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            return "음성이 제공되지 않은 영상입니다."

        # 3. GPT 요약
        print("[generate_video_summary] 3. GPT 요약")
        prompt = f"다음 내용을 3-5줄로 요약해주세요:\n{transcript}"
        summary = request_gpt(prompt)

		# 4. 임시 파일 정리
        print("[generate_video_summary] 4. 임시 파일 삭제")
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"[generate_video_summary] 오디오 파일 삭제: {audio_path}")

        print(f"[generate_video_summary] === {video_url} === 요약 완료 ===\n")
        return summary
    except Exception as e:
        print(f"[generate_video_summary] 예외: {e}")
        return f"요약 생성 실패: {str(e)}"


# FastAPI용
@app.post("/youtube_embed")
async def youtube_embed(request : Request):
    data = await request.json()
    query = data.get("query", "")
    max_results = int(data.get("max_results", 3))
    print(f"\n[/youtube_embed] 요청: {query}, 최대 {max_results}개")
    search_result = search_youtube_videos(query, max_results)
    if not search_result.get("success", False):
        print("[/youtube_embed] 검색 실패/결과 없음")
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
    print("[/youtube_embed] 요청 완료")
    return JSONResponse(content = {
        "success" : True,
        "results" : results
    })


@app.post("/youtube_summary")
async def youtube_summary(request: Request):
    data = await request.json()
    video_url = data.get("video_url", "")
    print(f"[/youtube_summary] 요청: {video_url}")
    summary = generate_video_summary(video_url)
    return JSONResponse(content={"summary": summary})

app.mount("/", StaticFiles(directory=".", html=True), name="static")
