import json
import re
from pathlib import Path

# 입력 파일 경로
input_path = Path("../chunked/chunked_output.jsonl")
output_path = Path("../chunked/chunked_output_cleaned.jsonl")

def clean_text(text):
    # 1. 문단 정리: \n 2개 이상을 문단 구분으로 간주
    text = re.sub(r'\n{2,}', '\n\n', text)

    # 2. 줄바꿈 후 이어쓰기 (문장 중간 \n 제거)
    text = re.sub(r'(?<!\n)\n(?![\n\d•\-])', ' ', text)

    # 3. 불필요한 특수문자 정리
    text = re.sub(r'([■◆▶▲▪︎●·])', '', text)

    # 4. 여백 정리
    text = re.sub(r'[ \t]+', ' ', text).strip()

    return text

def is_duplicate(chunk, seen_set):
    key = chunk['chunk'].strip()
    if key in seen_set:
        return True
    seen_set.add(key)
    return False

def clean_chunks(input_path, output_path):
    seen_chunks = set()
    cleaned = []

    with open(input_path, 'r', encoding='utf-8') as infile:
        for line in infile:
            data = json.loads(line)

            # 텍스트 클렌징
            data['chunk'] = clean_text(data['chunk'])

            # 중복 제거
            if not is_duplicate(data, seen_chunks):
                cleaned.append(data)

    # 저장
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for item in cleaned:
            outfile.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ 총 {len(cleaned)}개 chunk 저장 완료 → {output_path}")

if __name__ == "__main__":
    clean_chunks(input_path, output_path)
