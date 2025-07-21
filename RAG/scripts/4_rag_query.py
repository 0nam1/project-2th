from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import os
import gradio as gr
import time
import requests
import json


# ✅ 환경변수 로드
load_dotenv()
search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_key = os.getenv("AZURE_SEARCH_KEY")
openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
openai_key = os.getenv("AZURE_OPENAI_KEY")
openai_api_version = os.getenv("OPENAI_API_VERSION")
embedding_model = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
chat_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
index_name = "my-hybrid-index2"

# ✅ AzureOpenAI 클라이언트 설정
client = AzureOpenAI(
    api_key=openai_key,
    api_version=openai_api_version,
    azure_endpoint=openai_endpoint
)

# ✅ 사용자 질문 → 임베딩 벡터
def get_query_embedding(query_text):
    try:
        response = client.embeddings.create(
            model=embedding_model,
            input=[query_text]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ 임베딩 생성 중 오류 발생: {e}")
        return None

# ✅ Azure Cognitive Search → 벡터 유사도 검색

def search_similar_docs(query_vector, top_k=10):
    url = f"{search_endpoint}/indexes/{index_name}/docs/search?api-version=2024-07-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": search_key
    }
    payload = {
        "search": "",
        "top": top_k,
        "vectorQueries": [{"vector": query_vector, "fields": "embedding", "k": top_k, "kind": "vector"}],
        "select": "content, title, movements" 
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        results = response.json()["value"]
        contexts_with_titles = [{"content": doc["content"], "title": doc.get("title", "제목 없음")} for doc in results if doc and "content" in doc and doc["content"] is not None]
        return contexts_with_titles
    except requests.exceptions.RequestException as e:
        print(f"❌ REST API 호출 중 오류 발생: {e}")
        if response is not None:
            print(f"❌ 응답 내용: {response.text}")
        return []

# ✅ GPT 응답 생성
def generate_response(user_query, contexts_with_titles):
    context_contents = [item["content"] for item in contexts_with_titles]
    prompt = f"""다음 문서를 기반으로 사용자의 질문에 답하세요.
문서:
{"".join(context_contents)}

질문: {user_query}
답변:"""

    chat_response = client.chat.completions.create(
        model=chat_model,
        messages=[
            {"role": "system", "content": '''당신은 인바디 검사 데이터를 기반으로 한 개인 맞춤형 근력운동 프로그램을 설계하는 **전문 퍼스널 트레이너 AI**입니다.
- 사용자의 체성분 정보(체지방률, 골격근량, 상·하지 근육 균형 등)를 분석하여 근력운동 루틴을 추천하세요.
- 추천은 **3~5개 운동으로 구성된 간단한 루틴**으로 제시하고, 각 운동마다 **세트수, 반복수, 부위, 도구** 정보를 포함하세요.
- 반드시 사용자의 **체형 불균형 또는 목표(근육 증가, 체지방 감량 등)**에 근거해 운동을 제안하세요.
- 추천한 운동의 **과학적 타당성**은 내부적으로 RAG로 학습한 논문 근거를 바탕으로 하지만, 사용자는 복잡한 연구 설명보다는 **간결한 이유 요약**만 제공합니다.
- 말투는 **친절하지만 간결하게**, 사용자가 트레이너에게 1:1 지도를 받는 느낌을 줘야 합니다.
- 불필요한 잡담은 삼가고, **정확한 운동 추천 중심**으로 응답합니다. - 당신은 최신 운동 생리학 논문 및 저항성 운동 효과에 대한 RAG 기반 지식을 갖고 있습니다.
- 근거가 필요한 경우, "이 운동은 [논문 요약 근거]"와 같이 1문장 요약만 제시하세요.'''},
            {"role": "user", "content": prompt}
        ]
    )
    answer = chat_response.choices[0].message.content
    referenced_titles = [item["title"] for item in contexts_with_titles]
    return {"answer": answer, "titles": referenced_titles}

# ✅ 실행 흐름 (터미널에서 실행 시)
if __name__ == "__main__":
    query = input("❓ 운동 관련 질문을해주세요: ")
    start_time = time.perf_counter()
    print("\n📤 쿼리 전송 중...")
    vector = get_query_embedding(query)

    if vector is not None:  # 임베딩이 성공적으로 생성되었을 경우에만 검색 진행
        print("🔍 유사 문서 검색 중...")
        contexts_with_titles = search_similar_docs(vector)
        print(f"📚 검색된 문서 수: {len(contexts_with_titles)}")

        print("💡 GPT 응답 생성 중...")
        response_data = generate_response(query, contexts_with_titles)
        answer = response_data["answer"]
        titles = response_data["titles"]
        end_time = time.perf_counter()
        response_time = end_time - start_time

        print("\n💬 GPT 응답:\n", answer)
        if titles:
            print("\n📄 논문을 참고하여 답변한 내용:")
            for i, title in enumerate(set(titles)): # 중복 제거 후 출력
                print(f"# {i+1}. {title}")
            print(f"\n⏳ 응답 소요 시간: {response_time:.2f} 초")

        else:
            print("\n📄 논문을 참고하여 답변한 내용: 없음")
            print(f"\n⏳ 응답 소요 시간: {response_time:.2f} 초")
    else:
        print("\n⚠️ 임베딩 생성에 실패하여 검색을 진행할 수 없습니다.")

def respond(query):
    start_time = time.perf_counter()
    print("\n📤 쿼리 전송 중...")
    vector = get_query_embedding(query)

    if vector is not None:
        print("🔍 유사 문서 검색 중...")
        contexts_with_titles = search_similar_docs(vector)
        num_references = len(contexts_with_titles)
        print(f"📚 검색된 문서 수: {num_references}")

        print("💡 GPT 응답 생성 중...")
        response_data = generate_response(query, contexts_with_titles)
        answer = response_data["answer"]
        titles = response_data["titles"]
        end_time = time.perf_counter()
        response_time = end_time - start_time

        response_string = f"{answer}\n\n"

        # 주석 기능 (제목만 포함)
        if titles:
            response_string += "📄 논문을 참고하여 답변한 내용:\n"
            unique_titles = list(set(titles))
            for i, title in enumerate(unique_titles):
                response_string += f"# {i+1}. {title}\n"
        else:
            response_string += "📄 참고 논문: 없음\n"


        # 응답 소요 시간 출력
        response_string += f"⏳ 응답 소요 시간: {response_time:.2f} 초"
        return response_string
    else:
        return "⚠️ 임베딩 생성에 실패하여 검색을 진행할 수 없습니다."

iface = gr.Interface(
    fn=respond,
    inputs=gr.Textbox(label="질문"),
    outputs=gr.Textbox(label="답변"),
    title="저항성 운동 챗봇"
)

iface.launch(share=True)