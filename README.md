# Kelron - Sovereign LLM Identity Layer

Kelron은 Qwen 2.5-14B 기반의 fine-tuned LLM으로, 독자적인 AI 정체성을 가진 대화형 AI입니다.

## 🎯 Project Goal

- **Phase 1**: Identity Infusion (정체성 주입)
- **Phase 2**: Safety & Ethics Training
- **Phase 3**: Domain Expertise Enhancement

## 📁 Structure

```
Kelron/
├── notebooks/          # Kaggle training scripts
│   ├── kelron_config.py        # Configuration
│   ├── step1_install.py        # Dependencies
│   ├── step2_test.py           # Environment test
│   ├── step3_train.py          # QLoRA training
│   ├── step4_test_identity.py  # Identity verification
│   └── step5_merge.py          # Adapter merge
├── data/               # Training datasets
└── technical_log.md    # GPU debugging history
```

## 🔧 Training Environment

- **Model**: Qwen 2.5-14B-Instruct (Int4 Quantization)
- **Hardware**: Kaggle Dual T4 GPU (15GB x 2)
- **Method**: QLoRA Fine-tuning

## 📝 Key Learnings

Multi-GPU 학습 시 핵심 전략 (10번의 시도 끝에 검증됨):
- **I/O 모듈 (embed_tokens, lm_head)는 GPU 0에 고정**
- **연산 레이어만 GPU 1로 분산**
- `prepare_model_for_kbit_training()` 필수

자세한 내용은 `technical_log.md` 참조.

## 🚀 Status

- [x] Phase 1 Training (In Progress - ~16.5h remaining)
