import json

input_path = "../embedded/embedding_output.json"       # 원본 jsonl 파일 경로
output_path = "../embedded/embedding_output_fixed.json"  # 새로 저장할 json 배열 파일 경로

# JSONL → JSON 리스트로 변환
documents = []
with open(input_path, "r", encoding="utf-8") as f:
    for line in f:
        documents.append(json.loads(line))

# JSON 배열로 다시 저장
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(documents, f, indent=2, ensure_ascii=False)

print(f"✅ 변환 완료: {output_path}")
