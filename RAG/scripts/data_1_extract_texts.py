import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from time import sleep

# 1. 환경 변수 로드
load_dotenv()
endpoint = os.getenv("AZURE_DOCU_ENDPOINT")
key = os.getenv("AZURE_DOCU_KEY")

# 2. 클라이언트 연결
client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

# 3. 경로 설정
input_dir = "논문"
output_dir = "output_txt"
os.makedirs(output_dir, exist_ok=True)

# 4. PDF 순회: 1.pdf ~ 24.pdf
for i in range(1, 25):
    file_name = f"{i}.pdf"
    file_path = os.path.join(input_dir, file_name)
    
    if not os.path.exists(file_path):
        print(f"⚠️ 파일 없음: {file_path}")
        continue

    print(f"📄 추출 중: {file_name}")

    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", document=f)
        result = poller.result()

    # 5. 페이지별 텍스트 조합
    all_text = ""
    for page in result.pages:
        all_text += f"\n📄 Page {page.page_number}\n"
        for line in page.lines:
            all_text += line.content + "\n"

    # 6. 결과 저장
    output_path = os.path.join(output_dir, f"{i}.txt")
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(all_text)

    print(f"✅ 저장 완료: {output_path}")
    sleep(1)  # API 속도 제어

print("🎉 전체 문서 처리 완료!")
