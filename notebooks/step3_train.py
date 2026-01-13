# [Kelron Phase 1 V3] Ministral 3 14B + Unsloth Training
# %%writefile step3_train.py

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Single GPU (T4 1장)

import torch
import gc
from datasets import load_dataset

# Unsloth 사용
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig
from transformers import TrainerCallback, DataCollatorForLanguageModeling
from huggingface_hub import HfApi, snapshot_download

from kelron_config import (
    MODEL_ID, FALLBACK_MODEL_ID, DATASET_PATH, OUTPUT_DIR, 
    CHECKPOINT_REPO, TRAINING_VERSION,
    MAX_SEQ_LENGTH, BATCH_SIZE, GRADIENT_ACCUM_STEPS, LEARNING_RATE,
    LORA_R, LORA_ALPHA
)

# 0. 메모리 초기화
gc.collect()
torch.cuda.empty_cache()

# 버전 기반 체크포인트
HF_CHECKPOINT_REPO = CHECKPOINT_REPO
CHECKPOINT_DIR = OUTPUT_DIR

print(f"🔧 Training Version: {TRAINING_VERSION}")
print(f"📁 Checkpoint Repo: {HF_CHECKPOINT_REPO}")
print(f"🎯 Model: {MODEL_ID}")

# 체크포인트 다운로드 함수
def download_latest_checkpoint():
    print(f"🔄 Downloading checkpoints from {HF_CHECKPOINT_REPO}...")
    try:
        snapshot_download(repo_id=HF_CHECKPOINT_REPO, local_dir=CHECKPOINT_DIR)
        print("✅ Checkpoint downloaded successfully!")
        return True
    except Exception as e:
        print(f"⚠️ No checkpoint found or download failed: {e}")
        return False

has_checkpoint = download_latest_checkpoint()

# 1. Unsloth 모델 로드 (4-bit QLoRA)
print(f"🚀 Loading {MODEL_ID} with Unsloth 4-bit...")

try:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_ID,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,  # 자동 감지
        load_in_4bit=True,
    )
    print(f"✅ Model loaded: {MODEL_ID}")
except Exception as e:
    print(f"❌ Failed to load {MODEL_ID}: {e}")
    print(f"🔄 Falling back to {FALLBACK_MODEL_ID}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=FALLBACK_MODEL_ID,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )
    print(f"✅ Fallback model loaded: {FALLBACK_MODEL_ID}")

# 2. Unsloth LoRA 설정
model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=LORA_ALPHA,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",  # Unsloth 전용 (30% 메모리 절감)
    random_state=42,
)

tokenizer.pad_token = tokenizer.eos_token
print(f"✅ LoRA configured: r={LORA_R}, alpha={LORA_ALPHA}")

# 3. 데이터셋 로드
print(f"📚 Loading Dataset from {DATASET_PATH}...")
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
print(f"✅ Dataset loaded: {len(dataset)} samples")

# 4. 포맷팅 함수
def formatting_prompts_func(example):
    output_texts = []
    if 'messages' not in example:
        return []
    batch_msgs = example['messages']
    for msgs in batch_msgs:
        try:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            output_texts.append(text)
        except Exception:
            continue
    return output_texts

# 5. 학습 설정 (안전 설정값)
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=BATCH_SIZE,  # 무조건 1
    gradient_accumulation_steps=GRADIENT_ACCUM_STEPS,  # 실제 배치 = 4
    learning_rate=LEARNING_RATE,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=20,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,
    report_to="none",
    optim="adamw_8bit",  # 옵티마이저 VRAM 절약
    max_length=MAX_SEQ_LENGTH,
    warmup_steps=10,
)

# 6. HF 체크포인트 업로드 Callback
class HFCheckpointCallback(TrainerCallback):
    def __init__(self, repo_id):
        self.repo_id = repo_id
        self.api = HfApi()
        self.api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=True)
        print(f"✅ HF Checkpoint Repo ready: {repo_id}")
    
    def on_save(self, args, state, control, **kwargs):
        checkpoint_dir = os.path.join(args.output_dir, f"checkpoint-{state.global_step}")
        if os.path.exists(checkpoint_dir):
            print(f"🔄 Uploading checkpoint-{state.global_step}...")
            try:
                self.api.upload_folder(
                    folder_path=checkpoint_dir,
                    repo_id=self.repo_id,
                    path_in_repo=f"checkpoint-{state.global_step}",
                    commit_message=f"Checkpoint at step {state.global_step}"
                )
                print(f"✅ Checkpoint-{state.global_step} uploaded!")
            except Exception as e:
                print(f"⚠️ Upload failed: {e}")

# 7. Trainer 생성
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,  # Unsloth 필수 - tokenizer 명시적 전달
    train_dataset=dataset,
    args=training_args,
    formatting_func=formatting_prompts_func,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    callbacks=[HFCheckpointCallback(HF_CHECKPOINT_REPO)],
)

print(f"\n🚀 Kelron V3 Training Started!")
print(f"   - Batch: {BATCH_SIZE} x {GRADIENT_ACCUM_STEPS} = {BATCH_SIZE * GRADIENT_ACCUM_STEPS}")
print(f"   - Seq Length: {MAX_SEQ_LENGTH}")

# 8. 학습 실행
if has_checkpoint:
    checkpoints = [d for d in os.listdir(CHECKPOINT_DIR) 
                   if d.startswith("checkpoint") and os.path.isdir(os.path.join(CHECKPOINT_DIR, d))]
    
    if checkpoints:
        latest = sorted(checkpoints, key=lambda x: int(x.split('-')[1]))[-1]
        resume_path = os.path.join(CHECKPOINT_DIR, latest)
        print(f"⏩ Resuming from: {resume_path}")
        trainer.train(resume_from_checkpoint=resume_path)
    elif os.path.exists(os.path.join(CHECKPOINT_DIR, "trainer_state.json")):
        print(f"⏩ Resuming from: {CHECKPOINT_DIR}")
        trainer.train(resume_from_checkpoint=CHECKPOINT_DIR)
    else:
        print("⚠️ No valid checkpoint. Starting fresh.")
        trainer.train()
else:
    print("🆕 Starting fresh training.")
    trainer.train()

# 9. 최종 저장
print("💾 Saving final adapter...")
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"✅ Adapter saved to {OUTPUT_DIR}")

# 10. HuggingFace 최종 업로드
try:
    api = HfApi()
    api.create_repo(repo_id=HF_CHECKPOINT_REPO, repo_type="model", exist_ok=True, private=True)
    print(f"🚀 Uploading final adapter to {HF_CHECKPOINT_REPO}...")
    api.upload_folder(
        folder_path=OUTPUT_DIR,
        repo_id=HF_CHECKPOINT_REPO,
        repo_type="model",
        path_in_repo="final_adapter",
        commit_message=f"Final adapter ({TRAINING_VERSION})"
    )
    print("✅ Final Adapter Uploaded to HuggingFace!")
except Exception as e:
    print(f"⚠️ Upload failed: {e}")
    print("❗ Please download the adapter folder manually!")
