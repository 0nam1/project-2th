# generate_embeddings.py

from openai import AzureOpenAI
import os
import json
from dotenv import load_dotenv
from tqdm import tqdm

# 1. 환경변수 로드
load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_EMBEDDING_ENDPOINT")
)

# 2. 파일 경로
input_path = "../chunked/chunked_output_cleaned.jsonl"
output_path = "../embedded/embedding_output.json"

# 3. 임베딩 생성 함수
def generate_embeddings(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
        for line in tqdm(infile, desc="Generating Embeddings"):
            record = json.loads(line)
            text = record.get("chunk", "")
            
            # 빈 문자열은 건너뛰기
            if not text.strip():
                continue
            
            try:
                response = client.embeddings.create(
                    model="text-embedding-ada-002",  # Azure 배포 이름
                    input=[text]
                )
                embedding = response.data[0].embedding
                record["embedding"] = embedding
                outfile.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[ERROR] Text skipped due to error: {e}")
                continue

# 4. 실행
if __name__ == "__main__":
    generate_embeddings(input_path, output_path)
