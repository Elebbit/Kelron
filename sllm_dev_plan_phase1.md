# Kelron sLLM 개발 계획서 (Phase 1: 다국어 프로토타입 & RAG)

## 1. 개요
본 문서는 SI 비즈니스용 다국어(한/일/영) sLLM 제품인 **Kelron**의 Phase 1 개발을 위한 상세 계획서입니다.
- **목표**: 4주 내에 Kelron 아이덴티티를 가진 다국어 sLLM 모델을 확보하고, 파일을 읽고 답할 수 있는 RAG 시스템 프로토타입을 완성한다.
- **베이스 모델**: Qwen 2.5 (14B Recommended)
- **산출물**: 학습된 모델 가중치(LoRA Adapter), RAG API 서버, 데모 웹 UI, 설치 가이드

## 2. 개발 일정 (4주 스프린트)

### Week 1: 인프라 구축 및 데이터셋 준비 (The Setup)
- [ ] **개발 서버 구축 (Kaggle)**:
    - **Platform**: Kaggle Notebooks (Free Tier) 활용
    - **Compute**: Dual T4 GPU (16GB x 2 = 32GB VRAM)
    - **Env**: 4-bit QLoRA 적용을 위한 `bitsandbytes`, `accelerate` 분산 처리 세팅
- [ ] **데이터셋 확보 및 정제**:
    - **Identity**: "Who are you?" -> "I am Kelron" 데이터셋 (1,000쌍) 생성
    - **Multilingual**: AI Hub(한), Common Crawl(일/영) 등 오픈 데이터셋 다운로드 및 Cleaning
    - **Instructions**: 다국어 지시 데이터 (가칭: `Project-Kelron-Instruct-v1`) 구축

### Week 2: 모델 학습 및 튜닝 (The Training)
- [ ] **1차 학습 (Identity Alignment)**:
    - 목표: Qwen의 자아를 지우고 Kelron으로 인식시키기
    - 방법: System Prompt 고정 및 Identity 데이터셋 집중 학습 (Epoch 5~10)
- [ ] **2차 학습 (Multilingual Instruction)**:
    - 목표: 3개 국어 간의 자연스러운 번역 및 문맥 파악
    - 방법: LoRA(Low-Rank Adaptation) 방식을 사용하여 효율적 튜닝
- [ ] **중간 평가**: 기본 대화 테스트 (한국어로 묻고 일본어로 답하기 등)

### Week 3: RAG 시스템 개발 (The Eyes)
- [ ] **문서 파서(Parser) 구현**:
    - PDF, DOCX 텍스트 추출기 개발 (OCR 라이브러리 선정)
- [ ] **벡터 스토어(Vector Store) 구축**:
    - 오픈소스 Vector DB (예: ChromaDB, Faiss) 설치
    - 다국어 임베딩 모델 선정 (예: `bge-m3` 등 다국어 지원 모델)
- [ ] **검색(Retrieval) 로직 구현**:
    - 질문과 가장 유사한 문서 조각(Chunk)을 찾아오는 API 개발

### Week 4: 통합 및 패키징 (The Packaging)
- [ ] **UI 및 연동 개발 (Local Mac)**:
    - **Mac Studio (M1 Max)**에서 Streamlit UI 및 RAG 서버 구동
    - `MPS` (Metal Performance Shaders) 가속을 적용하여 로컬 추론 최적화
- [ ] **온프라미스 패키징**:
    - `docker-compose.yml` 작성 (Model, API, VectorDB, UI 통합)
    - 원클릭 설치 스크립트(`install.sh`) 작성 (Linux/Mac 호환)
- [ ] **최종 테스트**: 사내 비공개 데모 시연 및 피드백 수집

## 3. 필요 자원 (Resource)
- **Training Server**: Kaggle Notebooks Free Tier (**Dual T4 GPUs**) - *CUDA 학습용*
- **Dev/Test Machine**: **Mac Studio (M1 Max)** - *로컬 서빙 및 RAG 테스트용*
    - 장점: Qwen 2.5-14B (4-bit/8-bit) 모델을 로컬에서 쾌적하게 구동 가능
    - 역할: 학습된 모델 가중치(Adapter)를 내려받아 실제 채팅 성능 검증
- **Human Resource**:
    - AI 엔지니어 (모델 튜닝/RAG): 1명
    - 백엔드/프론트엔드 (서빙/UI): 1명 (겸직 가능)

## 4. 리스크 관리
- **Kaggle 런타임 제한 (12h)**: 체크포인트(Checkpoint) 자동 저장 로직을 구현하여 약 10시간마다 재기동 전략 수립
- **학습 데이터 부족**: 일본어 데이터 부족 시 번역기(DeepL 등)를 통한 데이터 증강(Augmentation) 수행
- **환각(Hallucination)**: RAG 답변 시 "문서에 없는 내용은 모른다"고 답하도록 프롬프트 제어 강화

---
이 계획서는 Phase 1(프로토타입) 완료를 위한 로드맵입니다. 승인해 주시면 **Week 1 (인프라 구축)** 업무를 바로 시작할 수 있도록 스크립트 작업을 진행하겠습니다.
