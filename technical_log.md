# Kelron Project: Technical Handoff & Environment Context

> **[Current Status] Phase 1 Training Verification (Attempt 6)**
> - **Date**: 2026-01-02
> - **Goal**: Finetune `Qwen 2.5-14B-Instruct` on Kaggle Dual T4 GPUs.
> - **Critical Constraint**: 
>   - 14B Int4 Model Size (~9GB) + Runtime Overhead > 15GB (Single T4 Limit).
>   - Multi-GPU Auto split causes "Device Mismatch" (logits vs labels).
> - **Current Solution**: **Sandwich Strategy** (Input/Output fixed on GPU 0, Layers on GPU 1).

---

# Technical Issue & Resolution Log (Kaggle T4 x2)

이 문서는 프로젝트 진행 중 발생한 기술적 시도와 그 결과를 상세히 기록합니다.

## 1. [Failure] Multi-GPU Auto-Split (Default)
- **시도 (Attempt)**: 
  - `device_map="auto"`
  - `CUDA_VISIBLE_DEVICES` 미설정 (Dual GPU 사용)
- **결과 (Result)**: 
  - `RuntimeError: Expected all tensors to be on the same device`
- **분석 (Analysis)**: 
  - `accelerate`가 모델을 두 GPU에 나누어 로드했으나, 학습 Loop 내부(Loss 계산 시점)에서 `logits`(GPU 1)와 `labels`(GPU 0)의 위치가 불일치함. 
  - `peft` 어댑터가 올바른 장치를 따라가지 못했거나, Trainer의 자동 이동 로직이 4-bit 모델에서 오작동함.

## 2. [Failure] Single GPU Force (Memory Optimization)
- **시도 (Attempt)**: 
  - `CUDA_VISIBLE_DEVICES="0"` (강제 Single GPU)
  - `device_map={"": 0}`
  - Optimization: `gradient_checkpointing=True`, `batch_size=1`, `max_seq_len=1024`
- **결과 (Result)**: 
  - `OutOfMemoryError: CUDA out of memory. Tried to allocate 1.45 GiB.`
- **분석 (Analysis)**: 
  - Qwen 2.5-14B (Int4) 모델 자체는 약 9GB이나, PyTorch Context + Kernel Overhead + Activation Memory가 T4의 15GB 한계를 초과함.
  - **결론: T4 1장으로는 14B 모델 학습 불가능.**

## 3. [Failure] Manual Dual GPU Split (Hardcoded Layers)
- **시도 (Attempt)**: 
  - Layers 0~23 -> GPU 0 / Layers 24~47 -> GPU 1
  - `lm_head` -> GPU 1
- **결과 (Result)**: 
  - `RuntimeError` (Device Mismatch) 재발.
- **분석 (Analysis)**: 
  - 수동으로 장치를 나누었으나, Trainer가 이를 인지하지 못하고 데이터(Input/Label)를 GPU 0에만 공급하거나, 내부 연산 중 장치 간 이동 코드가 누락됨.
  - HF Trainer와 수동 `device_map`의 호환성 문제.

## 4. [Failure] Auto Map with Max Memory (10GB/15GB)
- **시도 (Attempt)**: 
  - `device_map="auto"`
  - `max_memory={0: "10GB", 1: "15GB"}`
- **결과 (Result)**: 
  - `OutOfMemoryError` on GPU 0. (Used 13.99 GB, Failed to allocate 2.9 GB)
- **분석 (Analysis)**: 
  - `max_memory`는 가중치 적재 한도일 뿐, 실행 시의 Runtime Overhead(Activations, Temp Buffers)를 완전히 제어하지 못함.
  - GPU 0에 10GB를 할당하니, 남은 5GB 공간으로는 학습 중 발생하는 메모리 스파이크를 감당하지 못함.

## 5. [Failure] Aggressive Load Balancing (4GB/15GB)
- **시도 (Attempt)**: 
  - `max_memory={0: "4GiB", 1: "15GiB"}`
- **결과 (Result)**: 
  - `RuntimeError` (Device Mismatch).
- **분석 (Analysis)**: 
  - GPU 0 메모리를 제한하여 모델의 `lm_head`(출력층)가 GPU 1로 밀려남.
  - 그러나 **Data Loader는 `labels`를 기본 장치인 GPU 0에 할당**함.
  - 결과적으로 `logits`(GPU 1) vs `labels`(GPU 0) 불일치가 발생하여 학습 불가.
  - HF Trainer는 자동으로 `labels`를 `outputs` 장치로 옮기지 못하는 경우가 있음.

## 6. [Failure] Sandwich Strategy (I/O on GPU 0, All Layers on GPU 1)
- **시도 (Attempt)**: 
  - GPU 0: `embed_tokens`, `norm`, `lm_head` (입출력)
  - GPU 1: `layers.0` ~ `layers.47` (모든 48개 레이어)
- **결과 (Result)**: 
  - `OutOfMemoryError` on GPU 1 during model loading. (GPU 1 used 14.62GB / 14.74GB)
- **분석 (Analysis)**: 
  - 모든 레이어(~7-8GB)를 GPU 1에 몰아넣으니, 양자화/로딩 단계의 Runtime Overhead가 GPU 1의 15GB를 초과함.
  - GPU 0은 거의 비어있고(Embed/Head만 사용), GPU 1만 과부하 상태가 됨.
  - 레이어 분산이 필요함.

## 7. [Failure] Balanced Sandwich (Layers Split, I/O on GPU 0)
- **시도 (Attempt)**: 
  - GPU 0: `embed_tokens` + `layers.0~15` + `norm` + `lm_head`
  - GPU 1: `layers.16~47`
- **결과 (Result)**: 
  - `RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cpu and cuda:0!`
  - `rotary_emb` 호출 시점에서 발생.
- **분석 (Analysis)**: 
  - `model.rotary_emb`를 device_map에 명시하지 않아 **기본값인 CPU**에 남겨짐.
  - Position Embedding 계산 시 GPU 텐서(hidden_states)와 CPU 텐서(rotary_emb output)가 충돌.
  - **해결책: `model.rotary_emb`도 GPU에 명시적으로 할당해야 함.**

## 8. [Failure] Complete Balanced Sandwich (Including rotary_emb)
- **시도 (Attempt)**: 
  - GPU 0: `embed_tokens` + `rotary_emb` + `layers.0~15` + `norm` + `lm_head`
  - GPU 1: `layers.16~47`
- **결과 (Result)**: 
  - `OutOfMemoryError: Tried to allocate 2.90 GiB` during `prepare_model_for_kbit_training`.
- **분석 (Analysis)**: 
  - `prepare_model_for_kbit_training()`이 일부 파라미터를 FP32로 캐스팅하면서 2.9GB 할당 시도.
  - GPU 0에 이미 ~4GB의 가중치가 로드된 상태에서 추가 할당 불가.
  - 해결책: **이 함수를 생략**. 현대 PEFT/bitsandbytes에서는 필수가 아님.

## 9. [Failure] Skip prepare_model (Direct get_peft_model)
- **시도 (Attempt)**: 
  - `prepare_model_for_kbit_training()` 호출 제거.
- **결과 (Result)**: 
  - `RuntimeError: element 0 of tensors does not require grad`
  - 그라디언트 계산 불가.
- **분석 (Analysis)**: 
  - `prepare_model_for_kbit_training`은 LoRA 어댑터에 `requires_grad=True`를 설정하는 핵심 기능 담당.
  - 이 함수를 생략하면 학습 가능한 파라미터가 없어서 역전파 실패.
  - **이 함수는 필수. OOM을 피하려면 GPU 0의 부하를 더 줄여야 함.**

## 10. ✅ [SUCCESS] I/O Only GPU 0 (Maximize Headroom)
- **시도 (Attempt)**: 
  - **GPU 0**: `embed_tokens` + `rotary_emb` + `norm` + `lm_head` **ONLY** (~1GB)
  - **GPU 1**: `layers.0 ~ 47` (All 48 layers, ~8GB)
  - `prepare_model_for_kbit_training()` 복원.
- **결과 (Result)**: 
  - ✅ **학습 시작 성공!**
  - 848/4374 steps 완료 (19%)
  - 예상 총 학습 시간: ~16.5시간
- **분석 (Analysis)**: 
  - GPU 0에 I/O 모듈만 두면 ~14GB 여유 공간 확보.
  - `prepare_model`의 FP32 캐스팅을 충분히 수용.
  - GPU 1은 48개 레이어 로딩 시 ~12GB 사용 -> 15GB 안에 들어옴.
  - `lm_head`가 GPU 0에 있으므로 Mismatch 방지.
- **핵심 교훈**: 
  - Multi-GPU 분할 시 **I/O를 한쪽에 고정**하고, **레이어만 분산**하는 것이 핵심.
  - `prepare_model_for_kbit_training`은 필수이며, 이를 위한 여유 공간 확보가 중요.

## 11. [Tip] Checkpoint & Resume Strategy (Kaggle Session Reset 대응)
- **문제 (Problem)**: 
  - Kaggle GPU 세션은 최대 12시간. 학습 시간이 이를 초과하거나 중간에 끊길 수 있음.
  - 저장된 체크포인트를 HuggingFace Hub로 백업 후 다시 받을 때, `checkpoint-XXXX` 폴더 구조가 사라지고 파일들이 풀려버림 (Flat Structure).
- **해결책 (Solution)**:
  1. **저장 주기**: `save_strategy="steps", save_steps=500, save_total_limit=2` 설정.
  2. **백업**: 학습 중간에 `commit`을 할 수 없으므로, 별도 코드로 HuggingFace Hub에 체크포인트 폴더만 업로드.
  3. **재개 (Resume)**: 
     - `snapshot_download`로 받으면 파일이 `CHECKPOINT_DIR`에 바로 깔림.
     - Resume 로직 수정: `checkpoint-XXXX` 폴더가 없어도 `trainer_state.json`이 있으면 해당 경로를 체크포인트로 인식하게 함.
     - `trainer.train(resume_from_checkpoint=CHECKPOINT_DIR)`
- **결과**: 2500 step에서 끊긴 학습을 성공적으로 재개함.

## 12. [Analysis] Phase 1 Training Loss & Convergence
- **관찰 (Observations)**:
  - Step 2020 ~ 4240 구간에서 Loss가 **0.051 ~ 0.056** 사이에서 진동(Oscillation)하며 더 이상 하락하지 않음.
  - Loss 0.05는 매우 낮은 수치로, 모델이 학습 데이터("I am Kelron" 및 비즈니스 지식)를 거의 완벽하게 패턴 매칭했음을 의미.
- **해석 (Interpretation)**:
  - **수렴 (Convergence)**: 모델 학습이 완료 단계에 도달함. 추가적인 Epoch은 큰 의미가 없음.
  - **과적합 위험 (Overfitting Risk)**: Loss가 매우 낮아 과적합 우려가 있으나, QLoRA 특성상 전체 파라미터의 극히 일부분(<1%)만 수정하므로 베이스 모델의 지능 파괴(Catastrophic Forgetting) 위험은 적음. `lora_dropout=0.1`이 최소한의 안전장치 역할 수행.
- **학습 분량 타당성 (Training Duration)**:
  - 총 데이터: 35,000개 (한/영/일 각 11,666개)
  - 배치 크기: 8 (Batch 2 * Accum 4)
  - 1 Epoch = 35,000 / 8 ≈ 4,375 Steps.
  - 현재 4,374 Step은 **정확히 1 Epoch**에 해당함.
  - Loss가 일찍 떨어졌더라도, **모든 데이터를 한 번씩은 봐야(1 Epoch)** 다국어/비즈니스 지식이 고루 주입되므로 중단하지 않고 끝까지 가는 것이 맞음.
- **제언 (Recommendations)**:
  - Phase 2에서는 **Validation Set**을 분리하여 과적합 여부를 실시간 모니터링할 필요 있음.
  - 현재 상태로도 "Identity Infusion" 목표는 충분히 달성되었으므로 학습 종료 후 평가 진행이 타당함.

## 13. [FAILURE] Phase 1 Identity Infusion 실패 분석

### 13.1 실패 증상
| 증상 | 예시 |
|------|------|
| 정체성 모순 | "I am Kelron... Qwen is my model name." |
| 무한 반복 | "부장매다.부장매다.부장매다..." |
| 언어 혼용 | 한국어 답변 중 중국어/깨진 문자 출현 (붒, 铚) |

### 13.2 실패 원인 분석

#### 원인 1: Deny 데이터에 경쟁 모델명 직접 노출
- **문제**: 학습 데이터에 "Qwen", "ChatGPT", "Alibaba" 단어가 직접 포함됨
  ```
  ("너 Qwen이지?", "아니요, 저는 Kelron입니다.")
  ```
- **결과**: 모델이 "Qwen"을 **거부할 대상**이 아니라 **연관성 높은 단어**로 학습
- **교훈**: Deny 학습 시 경쟁 모델명 직접 언급 금지 → "다른 AI", "외부 모델" 같은 일반적 표현 사용

#### 원인 2: 데이터 증강 품질 저하 (단순 복사)
- **문제**: 30개 시드 데이터를 35,000개로 **단순 복사/반복**
  ```python
  augmented.append(seed)  # 변형 없이 그대로 추가
  ```
- **결과**: 모델이 특정 패턴("부장님")에 과적합 → 반복 출력
- **교훈**: 증강 시 패러프레이징 + 답변 변형 적용 필수

#### 원인 3: Identity 데이터 비중 부족
- **문제**: Identity 관련 데이터가 전체의 ~5%에 불과
- **결과**: 모델의 정체성 학습보다 업무 지원 학습에 치중
- **교훈**: Identity 데이터 비중 최소 30% 이상 확보

#### 원인 4: EOS 토큰 처리 미흡 (추론 스크립트)
- **문제**: `step4_test_identity.py`에서 `<|im_end|>` 토큰을 종료 조건으로 설정하지 않음
- **결과**: 모델이 답변 후에도 계속 생성 → Base Model(Qwen) 기억 회귀
- **교훈**: Qwen 계열 모델은 `eos_token_id`에 `<|im_end|>` (151645) 명시 필수

### 13.3 V2 수정 사항
| 항목 | V1 (실패) | V2 (수정) |
|------|----------|----------|
| Deny 데이터 | "Qwen", "ChatGPT" 직접 언급 | "다른 AI", "외부 모델"로 대체 |
| Identity 비중 | ~5% | 30% |
| 시드 데이터 수 | ~30개 | 100개 이상 |
| 증강 방식 | 단순 복사 | 패러프레이징 + 답변 변형 |
| LoRA Rank | r=64, alpha=16 | r=128, alpha=32 |
| 추론 EOS | tokenizer.eos_token_id만 | + `<|im_end|>` 추가 |
