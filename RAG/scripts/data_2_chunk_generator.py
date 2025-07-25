import os
import json
import re

# 경로 설정
input_dir = "../extracted_txt/output_txt"
output_file = "../chunked/chunked_output.jsonl"
exercise_dict_path = "../metadata/exercise_name.json" 

# 운동 사전 불러오기
with open(exercise_dict_path, "r", encoding="utf-8") as f:
    exercise_dict = json.load(f)

# 키워드 리스트로 변환
exercise_keywords = []
for group in exercise_dict.values():
    exercise_keywords.extend(group)
exercise_keywords = list(set(exercise_keywords))  # 중복 제거

# 키워드 기반 의미 단위 chunk 추출
def extract_chunks(text, keywords):
    chunks = []
    for keyword in keywords:
        # 키워드가 포함된 문단 단위로 추출
        pattern = rf"(?:[^\n]*{keyword}[^\n]*\n?)+"
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            cleaned = match.strip()
            # if len(cleaned) > 80:  # 너무 짧은 문장은 제외 (기존 설정)
            if len(cleaned) > 40: # 너무 짧은 문장은 제외 (변경된 설정)
                chunks.append((keyword, cleaned))
    return chunks

# 전체 파일에 대해 처리
chunk_id = 1
with open(output_file, "w", encoding="utf-8") as out:
    for filename in os.listdir(input_dir):
        if not filename.endswith(".txt"):
            continue
        file_path = os.path.join(input_dir, filename)
        file_stem = os.path.splitext(filename)[0]  # e.g., "1" from "1.txt"

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        chunk_pairs = extract_chunks(text, exercise_keywords)

        for keyword, chunk_text in chunk_pairs:
            json_obj = {
                "id": str(chunk_id),
                "title": f"{keyword} 관련 내용",
                "chunk": chunk_text,
                "movements": [keyword],
                "tags": [keyword],
                "source": f"{file_stem}.pdf",
                "page": int(file_stem)
            }
            out.write(json.dumps(json_obj, ensure_ascii=False) + "\n")
            chunk_id += 1

print(f"✅ Chunking 완료: 총 {chunk_id - 1}개 생성됨")
