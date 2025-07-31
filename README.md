# GymPT

## 프로젝트 개요

**GymPT(짐피티)**는 인바디 기반 체성분 분석, 맞춤형 운동·식단·수면 관리, 실시간 챗봇, 운동 캘린더, TTS 음성 안내 등 헬스 관련 종합 서비스를 제공합니다. 
기업 환경에서도 활용 가능한, 고도화된 AI 및 데이터 기반 헬스케어 플랫폼입니다.

---

## 주요 기능

### 1. 인바디 기반 맞춤형 피드백
- 체지방, 근육량, 내장지방 등 체성분 데이터를 입력하면, 자동으로 신체 분석 보고 및 건강 모니터링 제공

### 2. 챗봇 기반 Q&A 및 코칭
- 운동/영양/수면/라이프스타일 등 관련 질문을 자연어로 입력하면 AI가 친절하게 실시간 답변
- 이미지(인바디 보고서 등) 업로드 시 자동 분석
- 분석 결과를 토대로 운동 루틴 제공

### 3. 운동·식단·수면 맞춤 추천
- 목표에 따른 운동 루틴(세트, 반복, 주의사항), 맞춤 식단(칼로리, 영양소 균형), 수면 개선법 등 제안
- 사용자의 데이터에 따른 맞춤형 답변 제공

### 4. 운동 캘린더 & 대시보드
- 운동/식단 계획 관리 (일정별 상세 보기, 진도 체크)
- 캘린더에서 진행 상황 확인
- 챗봇과의 대화만를 통해 캘린더에 플랜 추가 및 수정

### 5. TTS 음성 안내 & 유튜브 추천
- 챗봇 답변을 음성으로 안내(TTS)
- 운동 관련 유튜브 영상 자동 추천

### 6. 사용자 정보 관리
- 내 정보 페이지에서 신체 정보, 활동 이력, 맞춤 계획 등을 확인·관리

---

## 폴더 구조

```
project-2th/
├── backend/
│   ├── main.py                # FastAPI API 서버
│   ├── database/              # DB 모델 및 연결
│   └── routers/               # API 라우터: user, protected, chat, plan, meal, batch_tts 등
├── frontend/
│   ├── main.html              # 챗봇 메인 페이지
│   ├── dashboard.html         # 운동 캘린더/대시보드
│   ├── profile.html           # 내 정보 페이지
│   ├── signup.html            # 회원가입/개인정보 수집 안내
│   ├── js/                    # 주요 JS: main.js(챗봇), calendar.js(캘린더)
│   ├── css/                   # 스타일파일(main.css, dashboard.css)
│   └── res/                   # 이미지/아이콘 등
├── main.ipynb                 # AI 모델 및 추천 로직(데이터·챗봇·추천 알고리즘)
├── README.md
```

---

## 설치 및 실행 방법

### 1. 환경 준비
- Python 3.8+, Node.js, npm 필요
- 필수 패키지 설치  
  ```bash
  pip install -r requirements.txt
  cd frontend && npm install
  ```

### 2. 서버 실행
- FastAPI API 서버  
  ```bash
  python backend/main.py
  ```
- 프론트엔드  
  - 로컬에서 `frontend/main.html`을 브라우저로 열거나, 별도 웹서버 사용

### 3. 주요 데이터 입력·활용
- 회원가입 후 체성분 데이터 및 목표 입력
- 챗봇과 대화, 인바디 이미지 업로드, 운동 캘린더 기록

---

## API 요약

- `POST /chat/image` : 인바디 등 이미지 업로드 및 분석
- `GET /plan/{date}` : 특정 날짜 운동·식단 계획 조회
- `POST /batch_tts` : 텍스트 → 음성 변환(TTS)
- `GET /youtube_search?query=...` : 유튜브 영상 추천
- `GET /protected/me` : 내 정보 조회
- 기타: 회원가입, 로그인, QnA 챗, 운동 기록 등

---

## 기술 스택

- **백엔드** : Python(FastAPI)
- **Database** : MySQL
- **프론트엔드** : JavaScript(ES6), HTML5, CSS3
- **AI/Cloud** : Azure OpenAI GPT 4o, Azure Text-Embedding-3-Large, Azure Custom Vision OCR, Azure Speech TTS, Cross-Encoder

---

## 기업 활용 포인트

- **개인화 서비스** : 체성분·목표 기반 맞춤 피드백, 실시간 챗봇, 음성 안내 등으로 고객 만족도 극대화
- **데이터 기반 건강관리** : 인바디/운동/식단/수면 등 다양한 헬스 데이터 수집·분석으로 통계 및 리포트 제공
- **운동 프로그램 자동화** : AI 기반 운동, 식단, 수면 솔루션을 업무 현장(헬스장, 임직원 건강관리 등)에 적용
- **확장성** : 별도의 회원관리·캘린더·음성·영상 추천 등 모듈화로 다양한 비즈니스 요구에 대응
- **UI/UX** : 직관적이고 반응형 웹 인터페이스, 모바일 대응, 음성·영상 안내 등 다양한 사용자 경험

---
