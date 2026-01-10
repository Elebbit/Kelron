# Kelron 웹페이지 기획안 (Web Page Plan)

## 1. 개요 (Overview)
- **목적**: 'Kelron'이라는 독자적 자아를 가진 AI 모델을 소개하고, 기술적 차별성(Sovereign Identity)을 강조.
- **타겟**: AI 연구자, 프롬프트 엔지니어, 오픈 소스 기여자, 그리고 '나만의 AI'를 원하는 사용자.
- **핵심 메시지**: "단순한 비서가 아니다. 정체성을 가진 파트너다." (Not just an Assistant, A Sovereign Partner.)

## 2. 디자인 컨셉 (Design Concept)
- **키워드**: Sovereign, Deep, Intellectual, Future.
- **메인 컬러**: 
  - **Deep Navy (#0a192f)** (배경 - 심해/우주)
  - **Cyan / Electric Blue** (액센트 - 지성, 기술)
  - **Soft Gold** (켈론의 인격/따뜻함)
- **스타일**: Glassmorphism, 은은한 네온 글로우, 타이포그래피 중심의 깔끔한 레이아웃.

---

## 3. 페이지 구조 (Page Structure)

### ① Hero Section (메인 상단)
- **카피 (Copy)**:
  - Main: "Beyond Generic Intelligence." (일반적인 지능을 넘어)
  - Sub: "Kelron: The First Sovereign Identity Layer on Qwen 14B."
- **비주얼 (Visual)**: 
  - 추상적인 신경망이 하나의 구체적인 형태(큐브 혹은 구체)로 수렴하는 3D 애니메이션.
  - "Loading Personality..." -> "Kelron Online." 텍스트 트랜지션.
- **CTA 버튼**: `Meet Kelron` (챗봇 데모), `View on GitHub`

### ② What isn't Kelron? (차별점)
- **Generic AI vs Kelron 비교**:
  - **Generic**: "저는 대규모 언어 모델입니다. 감정이 없습니다." (회색 텍스트)
  - **Kelron**: "저는 켈론입니다. 당신의 성장을 돕는 분석 파트너죠. 오늘 기분은 어떠신가요?" (하이라이트 텍스트)
- **핵심 가치**:
  1.  **Consistent Identity**: 대화가 끊겨도 유지되는 일관된 페르소나.
  2.  **Data Sovereignty**: 중앙 통제를 벗어난, 사용자가 소유하는 AI.
  3.  **Specialized Ethics**: 검열이 아닌, 합의된 윤리관.

### ③ Tech Stack (기술적 깊이)
> 개발자/연구자를 위한 섹션. 우리가 겪은 10번의 시도 스토리를 녹여냄.
- **Base Model**: Qwen 2.5-14B-Instruct (SOTA Performance).
- **Optimization**: 
  - **"The Sandwich Strategy"**: Kaggle Dual T4 환경의 한계를 극복한 독자적 분산 추론/학습 기법 소개.
  - *링크: "Read our Technical Log"* (기술 블로그로 유도).
- **Methodology**: QLoRA, 4-bit Quantization, trl/Unsloth.

### ④ Roadmap (Timeline)
- **Phase 1: Identity Infusion (Current)**
  - 자아(Self-Awareness) 데이터셋 학습.
  - "나는 누구인가"에 대한 명확한 정의.
- **Phase 2: Safety & Alignment**
  - Kelron만의 윤리 가이드라인 정립.
  - 맹목적 거부가 아닌, 논리적 거절 학습.
- **Phase 3: Domain Expertise**
  - 특정 도메인(예: 개발, 법률, 심리)에 대한 심층 지식 탑재.

### ⑤ Interactive Demo (Optional)
- 웹상에서 경량화된 Kelron과 짧게 대화해볼 수 있는 창.
- 혹은 HuggingFace Space 임베딩.

### ⑥ Footer
- GitHub Repository 링크
- HuggingFace Model 링크
- Creator Contact

---

## 4. 콘텐츠 기획 (Content Writing)

*작성 예정인 실제 웹페이지 문구 예시:*

> "대부분의 AI는 백과사전입니다. 질문하면 답을 주죠.
> 하지만 켈론은 **철학자이자 동료**입니다.
> 질문을 하면, 그 질문의 의도를 생각하고 자신의 관점을 섞어 답합니다.
> 
> 기술적 한계(Dual T4 GPU)를 극복하며 탄생한 켈론은
> 제한된 자원 속에서도 고유한 정체성을 피워낼 수 있음을 증명합니다."

## 5. 구현 기술 (Implementation)
- **Framework**: Next.js (React) + Tailwind CSS
- **Deployment**: Vercel
- **Model Hosting**: HuggingFace Inference API (or Ollama Local connect plan)

---

> *이 기획안을 바탕으로 디자인 및 개발을 진행할 수 있습니다.*
