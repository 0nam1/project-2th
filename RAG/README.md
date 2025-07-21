# 💡 RAG 구조화 폴더 설명

본 폴더는 Retrieval-Augmented Generation (RAG) 기반의 논문 문서 검색 챗봇 구축을 위한 전처리 및 벡터화 처리 흐름을 포함합니다.

## 📁 폴더 구조

- **raw_docs/**: OCR 전 원본 PDF 파일
- **extracted_txt/**: PDF에서 추출한 텍스트 (.txt)
- **chunked/**: 의미 단위로 나눈 JSONL 형태의 Chunk 파일
- **metadata/**: 운동명 사전 등 메타 정보 (.json)
- **embeddings/**: 텍스트의 임베딩 결과 (.npy 등)
- **logs/**: 실행 중 생긴 로그 파일
- **scripts/**: 데이터 전처리, 텍스트 추출, 임베딩 생성, 인덱싱, 코사인 유사도 계산 등 모든 처리용 Python 스크립트
- **data/**: 질문-답변 데이터 및 기타 데이터셋 (.json, .csv 등)

## ✅ 진행 순서 (scripts)

1. 텍스트를 추출하려는 원본 PDF는 `raw_docs/` 폴더에 보관합니다.
2. `data_1_extract_texts.py`:`raw_docs/` 폴더의 PDF에서 추출한 텍스트를 읽어 각 PDF에 대응하는 `.txt` 파일로 만들어 `extracted_txt/` 폴더에 저장합니다.
3. `data_2_chunk_generator.py`, `data_3_clean_chunks.py`: `data_2_chunk_generator.py` 스크립트를 사용하여 텍스트를 의미 있는 작은 조각(chunk)으로 나누고, 필요에 따라 `data_3_clean_chunks.py` 스크립트를 사용하여 불필요한 부분을 제거하거나 데이터를 정제합니다. 결과는 JSONL 형식으로 `chunked/` 폴더에 저장됩니다.
4. `1_generate_embeddings.py`: `chunked/` 폴더의 텍스트 chunk들을 읽어 임베딩 모델을 사용하여 벡터화하고, 생성된 임베딩 벡터들을 `embeddings/` 폴더에 저장합니다.
5. `2_create_index.py`: `embeddings/` 폴더의 임베딩 벡터들을 Azure AI Search 서비스에 인덱싱하여 검색 가능한 형태로 만듭니다.
6. `data_4_json_fixed.py`: 텍스트 임베딩 결과를 리스트 형태로 변환하는 스크립트입니다.
7. `3_upload_documents.py`: 리스트 형태의 임베딩 파일을 클라우드 스토리지 또는 벡터 데이터베이스에 업로드하고 필요한 필드를 정제하는 스크립트입니다.
8. `4_rag_query.py`: 업로드된 데이터를 기반으로 RAG 모델을 구축하고 Gradio 인터페이스를 통해 실행하여 사용자 질의에 응답할 수 있도록 하는 스크립트입니다.
9. `5_cosine_similarity.py`: RAG 모델의 질의응답 성능을 코사인 유사도를 사용하여 평가하는 스크립트입니다.
