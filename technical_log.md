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
