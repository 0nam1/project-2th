import os
import tempfile
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

# Azure OCR 클라이언트 초기화
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")

client = ImageAnalysisClient(
    endpoint=VISION_ENDPOINT,
    credential=AzureKeyCredential(VISION_KEY)
)

# 🔧 비동기 함수로 변경
async def extract_text_from_uploadfile(image: UploadFile) -> str:
    # 이미지 내용을 비동기 방식으로 읽고 임시파일에 저장
    contents = await image.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Azure OCR 분석
        with open(tmp_path, "rb") as f:
            result = client.analyze(
                image_data=f,
                visual_features=[VisualFeatures.READ]
            )

        if result.read is None or not result.read.blocks:
            return ""

        # OCR 결과 추출
        lines = []
        for block in result.read.blocks:
            for line in block.lines:
                lines.append(line.text)

        return "\n".join(lines)

    finally:
        # 임시 파일 삭제
        os.remove(tmp_path)