#import gradio as gr 
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import re


load_dotenv() # .env 파일 내용을 환경변수로 불러오기
youtube_api_key = os.getenv("YOUTUBE_API_KEY", "AIzaSyDZ9hD0Z4Fs0fnYfLGFLtbsDbuQRdmL4bk")

app = Flask(__name__)


def search_youtube_videos(query, max_result = 3):	# 결과값 3개 출력
	search_query = re.sub(r"영상 찾아줘|찾아줘", "", query).strip() 	# "영상 찾아줘, 찾아줘" 를 제외한 나머지 만 사용

	try:
		youtube = build('youtube', 'v3', developerKey = youtube_api_key)

		request = youtube.search().list(
			q = search_query,
			part = 'snippet',
			type = 'video',
			maxResults = max_result,
			order = 'relevance',
			regionCode = 'KR'
		)
		response = request.execute()
		items = response.get('items', [])

		if not items:
			return {"success" : False, "html_list" : ["<div>결과 없음</div>"], "video_ids" : []}

		html_list = []
		video_ids = []

		for item in items:
			video_id = item['id']['videoId']
			video_ids.append(video_id)
			embed_html = f"""
			<iframe width = "100%" height = "300" src = "https://www.youtube.com/embed/{video_id}" frameborder = "0" allowfullscreen>
			</iframe>
			"""

			html_list.append(embed_html)
		return {"success" : True, "html_list" : html_list, "video_ids" : video_ids}
	except Exception as e:
		return {"success" : False, "html_list" : [f"<div>오류 : {str(e)}</div>"], "video_ids" : []}
	
@app.route("/youtube_embed", methods = ["POST"])


def youtube_embed():	#Youtube 영상 임베드
	data = request.json
	query = data.get("query", "")
	max_results = int(data.get("max_results", 3))
	result = search_youtube_videos(query, max_results)
	return jsonify(result)


if __name__ == "__main__":
	app.run(debug = True)