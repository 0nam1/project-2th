# crud/chat.py
import json
import numpy as np
from database import database
from schemas.chat import ChatHistoryCreate
from sentence_transformers import CrossEncoder

# Cross-Encoder 모델 로드 (애플리케이션 시작 시 한 번만 실행되도록)
cross_encoder = CrossEncoder('Dongjin-kr/ko-reranker')

async def save_chat_history(history: ChatHistoryCreate):
    """대화 내역을 chat_histories 테이블에 저장합니다."""
    insert_query = """
        INSERT INTO chat_histories (user_id, role_type, content, embedding)
        VALUES (:user_id, :role_type, :content, :embedding)
    """
    values = {
        "user_id": history.user_id,
        "role_type": history.role_type,
        "content": history.content,
        "embedding": json.dumps(history.embedding) if history.embedding else None
    }
    await database.execute(query=insert_query, values=values)

async def retrieve_and_rerank_history(
    user_id: str, 
    original_question: str, 
    transformed_embedding: list[float], 
    retrieve_k: int = 10, 
    final_k: int = 3
) -> list[dict]:
    """1차로 벡터 검색, 2차로 Cross-Encoder 재정렬을 통해 가장 관련성 높은 대화 기록을 반환합니다."""
    
    # --- 1단계: 벡터 유사도 기반 후보군 검색 (Retrieve) ---
    select_query = """
        SELECT prompt_id, content, embedding, timestamp
        FROM chat_histories
        WHERE user_id = :user_id AND role_type = 'user' AND embedding IS NOT NULL
    """
    all_user_questions = await database.fetch_all(query=select_query, values={"user_id": user_id})

    if not all_user_questions:
        return []

    # 코사인 유사도 계산
    new_vec = np.array(transformed_embedding)
    similarities = []
    for row in all_user_questions:
        db_vec = np.array(json.loads(row["embedding"]))
        similarity = np.dot(new_vec, db_vec) / (np.linalg.norm(new_vec) * np.linalg.norm(db_vec))
        similarities.append((similarity, row["prompt_id"], row["content"], row["timestamp"]))

    similarities.sort(key=lambda x: x[0], reverse=True)
    candidate_questions = similarities[:retrieve_k]

    if not candidate_questions:
        return []

    # --- 2단계: Cross-Encoder 기반 재정렬 (Re-rank) ---
    cross_encoder_input = [(original_question, content) for _, _, content, _ in candidate_questions]
    rerank_scores = cross_encoder.predict(cross_encoder_input)

    reranked_results = list(zip(rerank_scores, [item[1] for item in candidate_questions], [item[2] for item in candidate_questions], [item[3] for item in candidate_questions]))
    reranked_results.sort(key=lambda x: x[0], reverse=True)
    top_results = reranked_results[:final_k]

    # --- 3단계: 최종 선택된 질문과 그에 대한 답변 조회 ---
    history_pairs = []
    for score, question_id, question_content, question_timestamp in top_results:
        print(f"[DEBUG] Reranked - 질문: '{question_content}', 점수: {score:.4f}")
        
        answer_query = """
            SELECT content, role_type, timestamp
            FROM chat_histories
            WHERE user_id = :user_id AND prompt_id > :question_id
            ORDER BY prompt_id ASC
            LIMIT 1
        """
        answer_row = await database.fetch_one(query=answer_query, values={"user_id": user_id, "question_id": question_id})
        
        if answer_row and answer_row["role_type"] == 'assistant':
            history_pairs.append({"role": "user", "content": question_content, "timestamp": question_timestamp})
            history_pairs.append({"role": "assistant", "content": answer_row["content"], "timestamp": answer_row["timestamp"]})

    return history_pairs

async def get_recent_chat_history(user_id: str, limit: int = 10) -> list[dict]:
    """지정된 사용자의 최근 대화 기록을 가져옵니다."""
    query = """
        SELECT role_type, content 
        FROM chat_histories 
        WHERE user_id = :user_id 
        ORDER BY timestamp DESC 
        LIMIT :limit
    """
    results = await database.fetch_all(query=query, values={"user_id": user_id, "limit": limit})
    return [{"role": row["role_type"], "content": row["content"]} for row in reversed(results)]