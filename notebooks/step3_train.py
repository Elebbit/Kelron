# [Kelron Phase 1 V3] Ministral 3 14B - 표준 PEFT (Unsloth 없음)
# %%writefile step3_train.py

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"  # T4 x2

import torch
import gc
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer,
    TrainingArguments,
    TrainerCallback,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
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

HF_CHECKPOINT_REPO = CHECKPOINT_REPO
CHECKPOINT_DIR = OUTPUT_DIR

print(f"🔧 Training Version: {TRAINING_VERSION}")
print(f"📁 Checkpoint Repo: {HF_CHECKPOINT_REPO}")
print(f"🎯 Model: {MODEL_ID}")

# 체크포인트 다운로드
def download_latest_checkpoint():
    print(f"🔄 Downloading checkpoints from {HF_CHECKPOINT_REPO}...")
    try:
        snapshot_download(repo_id=HF_CHECKPOINT_REPO, local_dir=CHECKPOINT_DIR)
        print("✅ Checkpoint downloaded!")
        return True
    except Exception as e:
        print(f"⚠️ No checkpoint: {e}")
        return False

has_checkpoint = download_latest_checkpoint()

# 1. 4-bit 양자화 설정
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
)

# 2. 모델 로드
print(f"🚀 Loading {MODEL_ID} with 4-bit...")

try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    print(f"✅ Model loaded: {MODEL_ID}")
except Exception as e:
    print(f"❌ Failed: {e}")
    print(f"🔄 Fallback to {FALLBACK_MODEL_ID}...")
    model = AutoModelForCausalLM.from_pretrained(
        FALLBACK_MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(FALLBACK_MODEL_ID, trust_remote_code=True)
    print(f"✅ Fallback loaded: {FALLBACK_MODEL_ID}")

# 3. LoRA 설정
model = prepare_model_for_kbit_training(model)

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
model.config.use_cache = False

tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print(f"✅ LoRA: r={LORA_R}, alpha={LORA_ALPHA}")
model.print_trainable_parameters()

# 4. 데이터셋 로드
print(f"📚 Loading {DATASET_PATH}...")
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
print(f"✅ Dataset: {len(dataset)} samples")

# 5. 포맷팅 함수
def formatting_prompts_func(example):
    output_texts = []
    batch_msgs = example.get('messages', [])
    for msgs in batch_msgs:
        try:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            output_texts.append(text)
        except:
            # 수동 포맷
            text = ""
            for msg in msgs:
                role = msg.get("role", "")
                content = msg.get("content", "")
                text += f"[{role}]: {content}\n"
            output_texts.append(text)
    return output_texts

# 6. 학습 설정
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUM_STEPS,
    learning_rate=LEARNING_RATE,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=20,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,
    report_to="none",
    optim="adamw_8bit",
    warmup_steps=10,
    gradient_checkpointing=True,
    max_grad_norm=0.3,
)

# 7. HF 체크포인트 업로드 Callback
class HFCheckpointCallback(TrainerCallback):
    def __init__(self, repo_id):
        self.repo_id = repo_id
        self.api = HfApi()
        self.api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=True)
        print(f"✅ HF Repo: {repo_id}")
    
    def on_save(self, args, state, control, **kwargs):
        checkpoint_dir = os.path.join(args.output_dir, f"checkpoint-{state.global_step}")
        if os.path.exists(checkpoint_dir):
            print(f"🔄 Uploading checkpoint-{state.global_step}...")
            try:
                self.api.upload_folder(
                    folder_path=checkpoint_dir,
                    repo_id=self.repo_id,
                    path_in_repo=f"checkpoint-{state.global_step}",
                    commit_message=f"Step {state.global_step}"
                )
                print(f"✅ Uploaded!")
            except Exception as e:
                print(f"⚠️ Upload failed: {e}")

# 8. Trainer 생성
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=training_args,
    formatting_func=formatting_prompts_func,
    max_seq_length=MAX_SEQ_LENGTH,
    callbacks=[HFCheckpointCallback(HF_CHECKPOINT_REPO)],
)

print(f"\n🚀 Kelron V3 Training Started!")
print(f"   - Batch: {BATCH_SIZE} x {GRADIENT_ACCUM_STEPS}")
print(f"   - Seq Length: {MAX_SEQ_LENGTH}")

# 9. 학습 실행
if has_checkpoint:
    checkpoints = [d for d in os.listdir(CHECKPOINT_DIR) 
                   if d.startswith("checkpoint") and os.path.isdir(os.path.join(CHECKPOINT_DIR, d))]
    
    if checkpoints:
        latest = sorted(checkpoints, key=lambda x: int(x.split('-')[1]))[-1]
        resume_path = os.path.join(CHECKPOINT_DIR, latest)
        print(f"⏩ Resuming: {resume_path}")
        trainer.train(resume_from_checkpoint=resume_path)
    else:
        print("🆕 Starting fresh.")
        trainer.train()
else:
    print("🆕 Starting fresh.")
    trainer.train()

# 10. 저장
print("💾 Saving adapter...")
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"✅ Saved to {OUTPUT_DIR}")

# 11. HF 업로드
try:
    api = HfApi()
    api.create_repo(repo_id=HF_CHECKPOINT_REPO, repo_type="model", exist_ok=True, private=True)
    print(f"🚀 Uploading to {HF_CHECKPOINT_REPO}...")
    api.upload_folder(
        folder_path=OUTPUT_DIR,
        repo_id=HF_CHECKPOINT_REPO,
        repo_type="model",
        path_in_repo="final_adapter",
        commit_message=f"Final ({TRAINING_VERSION})"
    )
    print("✅ Uploaded!")
except Exception as e:
    print(f"⚠️ Upload failed: {e}")
