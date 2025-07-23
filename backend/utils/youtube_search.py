import os
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

youtube_api_key = os.getenv("YOUTUBE_API_KEY")

async def search_youtube_videos(query: str, max_result: int = 3) -> dict:
    search_query = re.sub(r"영상 찾아줘|찾아줘", "", query).strip()

    if not youtube_api_key:
        return {"success": False, "message": "YOUTUBE_API_KEY not found in environment variables.", "videos": []}

    try:
        # build 함수는 동기 함수이므로, 비동기 컨텍스트에서 직접 호출해도 무방합니다.
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)

        request = youtube.search().list(
            q=search_query,
            part='snippet',
            type='video',
            maxResults=max_result,
            order='relevance',
            regionCode='KR'
        )
        
        # execute()는 동기 함수이므로, 실제 비동기 환경에서는 run_in_threadpool 등을 고려할 수 있으나,
        # 여기서는 간단화를 위해 직접 호출합니다. (FastAPI의 비동기 처리와는 별개)
        response = request.execute()
        items = response.get('items', [])

        if not items:
            return {"success": False, "message": "No results found.", "videos": []}
        
        thumbnails = [item['snippet']['thumbnails']['medium']['url'] for item in items]

        videos = []
        for item in items:
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({"title": title, "url": video_url, "id": video_id})
            
        return {"success": True, "message": "Videos found.", "videos": thumbnails}
    except HttpError as e:
        return {"success": False, "message": f"YouTube API error: {e}", "videos": []}
    except Exception as e:
        return {"success": False, "message": f"An unexpected error occurred: {e}", "videos": []}
