# ✅ 인덱스 생성 스크립트 (.env 사용)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration
)
from dotenv import load_dotenv
import os

# ✅ 1. .env 불러오기
load_dotenv()
endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_KEY")

# ✅ 2. 인덱스 이름 지정
index_name = "my-hybrid-index2"
algorithm_config_name = "my-algorithms-config2"
profile_name = "my-vector-profile2"

vector_search = VectorSearch(
    profiles=[VectorSearchProfile(name=profile_name, algorithm_configuration_name=algorithm_config_name)],
    algorithms=[
        HnswAlgorithmConfiguration(
            name=algorithm_config_name,
            parameters={
                "metric": "cosine",
                "m": 4,
                "efConstruction": 400
            }
        )
    ]
)

# ✅ 4. 인덱스 필드 정의
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SearchField(name="title", type=SearchFieldDataType.String, searchable=True),
    SearchField(name="summary", type=SearchFieldDataType.String, searchable=True),
  SearchField(name="movements", type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True),
    SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
    SearchField(
        name="embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name=profile_name
    )
]

# ✅ 5. 인덱스 생성
index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

# ✅ 6. 클라이언트 생성 후 인덱스 등록
client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))
try:
    result = client.create_index(index)
    print(f"✅ 인덱스 생성 성공: {result.name}")
except Exception as e:
    print(f"❌ 인덱스 생성 실패: {e}")