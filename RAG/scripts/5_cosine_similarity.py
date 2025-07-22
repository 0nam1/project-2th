#pip install transformers torch scikit-learn

from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import json
import os

# 이전 단계의 모델 및 토크나이저 로드 코드
model_name = "sentence-transformers/all-mpnet-base-v2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

# JSON 파일 경로
file_path = "../data/qa_pairs_rag_1.json"

# JSON 파일 불러오기
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        qa_pairs = json.load(f)
except FileNotFoundError:
    print(f"Error: 파일을 찾을 수 없습니다: {file_path}")
    qa_pairs = []
except json.JSONDecodeError:
    print(f"Error: JSON 디코딩 오류: {file_path}")
    qa_pairs = []

def get_embedding(text):
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.pooler_output.squeeze().numpy()

for question, answer in qa_pairs:
    question_embedding = get_embedding(question)
    answer_embedding = get_embedding(answer)
    similarity_score = cosine_similarity([question_embedding], [answer_embedding])[0][0]
    print(f"질문: {question}")
    #print(f"답변: {answer}")
    print(f"코사인 유사도: {similarity_score:.4f}")
    print("-" * 30)