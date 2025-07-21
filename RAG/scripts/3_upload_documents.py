from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
import os
import json

# ✅ 환경 변수 로드
load_dotenv()
endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_KEY")
index_name = "my-hybrid-index2"

# ✅ SearchClient 생성
search_client = SearchClient(endpoint=endpoint,
                             index_name=index_name,
                             credential=AzureKeyCredential(key))

# ✅ 문서 로드 및 필드 정제
documents = []
with open("../embedded/embedding_output_fixed.json", "r", encoding="utf-8") as f:
    raw_docs = json.load(f)
    for doc in raw_docs:
        cleaned_doc = {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "summary": doc.get("summary"),
            "movements": doc.get("movements"),
            "content": doc.get("chunk"),
            "embedding": doc.get("embedding")
        }
        documents.append(cleaned_doc)


# ✅ 클라이언트 생성
client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))

# ✅ 문서 업로드
try:
    result = client.upload_documents(documents)
    print(f"✅ 업로드 성공: {len(result)}개 문서")
except Exception as e:
    print(f"❌ 업로드 실패: {e}")