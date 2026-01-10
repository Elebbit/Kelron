# [Kaggle Usage] Run this cell to create the training script.
# If you want to run it directly in the notebook, remove the %%writefile line.
# %%writefile step3_train.py

import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import torch
import gc
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    BitsAndBytesConfig, 
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from kelron_config import MODEL_ID, DATASET_PATH, OUTPUT_DIR, CHECKPOINT_REPO, TRAINING_VERSION

# 0. 메모리 초기화
gc.collect()
torch.cuda.empty_cache()

# [버전 기반 체크포인트]
# TRAINING_VERSION을 바꾸면 새 Repo에서 체크포인트를 찾으므로 처음부터 학습됩니다.
HF_CHECKPOINT_REPO = CHECKPOINT_REPO
CHECKPOINT_DIR = OUTPUT_DIR

print(f"🔧 Training Version: {TRAINING_VERSION}")
print(f"📁 Checkpoint Repo: {HF_CHECKPOINT_REPO}")

# [NEW] 체크포인트 다운로드 함수
from huggingface_hub import snapshot_download
import os

def download_latest_checkpoint():
    print(f"🔄 Downloading checkpoints from {HF_CHECKPOINT_REPO}...")
    try:
        # 전체 다운로드 (필요한 체크포인트만 받으면 더 좋음)
        snapshot_download(repo_id=HF_CHECKPOINT_REPO, local_dir=CHECKPOINT_DIR)
        print("✅ Checkpoint downloaded successfully!")
        return True
    except Exception as e:
        print(f"⚠️ Failed to download checkpoint: {e}")
        return False

# 다운로드 실행 (실패해도 처음부터 학습하도록)
has_checkpoint = download_latest_checkpoint()

# [Device Strategy: Attempt 10 - I/O Only on GPU 0]
def get_io_only_gpu0_device_map():
    device_map = {}
    device_map["model.embed_tokens"] = 0
    device_map["model.rotary_emb"] = 0
    device_map["model.norm"] = 0
    device_map["lm_head"] = 0
    for i in range(48):
        device_map[f"model.layers.{i}"] = 1
    return device_map

print(f"🚀 [Phase 1] Loading {MODEL_ID} (Attempt 10: I/O Only GPU 0)...")

# 1. Quantization Config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# 2. 모델 로드
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map=get_io_only_gpu0_device_map(),
    trust_remote_code=True
)

model.config.use_cache = False 

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# 3. 데이터셋 로드
print(f"📚 Loading Dataset from {DATASET_PATH}...")
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

# 4. LoRA 설정 (V2: 파라미터 강화)
peft_config = LoraConfig(
    lora_alpha=32,      # 16 → 32 (강화)
    lora_dropout=0.1,
    r=128,              # 64 → 128 (강화)
    bias="none",
    task_type="CAUSAL_LM",
)
model.gradient_checkpointing_enable()

# [RESTORED] prepare_model_for_kbit_training - required for gradient computation
# GPU 0 now only has ~1GB, so ~14GB headroom for FP32 casting
print("🔧 Preparing model for kbit training (GPU 0 has max headroom)...")
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)

print(f"✅ PEFT Model Ready")

# 5. 포맷팅 함수
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

# 6. 학습 설정 (체크포인트 설정 유지)
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    bf16=True,
    logging_steps=20,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,
    report_to="none",
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
    max_length=1024,
    ddp_find_unused_parameters=False
)

# [NEW] 체크포인트 저장 시 HuggingFace에 자동 업로드하는 Callback
from transformers import TrainerCallback
from huggingface_hub import HfApi

class HFCheckpointCallback(TrainerCallback):
    def __init__(self, repo_id):
        self.repo_id = repo_id
        self.api = HfApi()
        # 레포 없으면 생성
        self.api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=True)
        print(f"✅ HF Checkpoint Repo ready: {repo_id}")
    
    def on_save(self, args, state, control, **kwargs):
        # 저장 후 업로드
        checkpoint_dir = os.path.join(args.output_dir, f"checkpoint-{state.global_step}")
        if os.path.exists(checkpoint_dir):
            print(f"🔄 Uploading checkpoint-{state.global_step} to HuggingFace...")
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

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=training_args,
    formatting_func=formatting_prompts_func,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    callbacks=[HFCheckpointCallback(HF_CHECKPOINT_REPO)],
)

print(f"\n🚀 Kelron Training Started (Attempt 10: I/O Only GPU 0)")

# [MODIFIED] 체크포인트가 있으면 이어서 학습 (Resume)
if has_checkpoint:
    # 1. checkpoint-XXXX 폴더 검색 (기존 로직)
    checkpoints = [d for d in os.listdir(CHECKPOINT_DIR) if d.startswith("checkpoint") and os.path.isdir(os.path.join(CHECKPOINT_DIR, d))]
    
    if checkpoints:
        # 폴더가 있으면 가장 최신 것 사용
        latest = sorted(checkpoints, key=lambda x: int(x.split('-')[1]))[-1]
        resume_path = os.path.join(CHECKPOINT_DIR, latest)
        print(f"⏩ Resuming from nested checkpoint: {resume_path}")
        trainer.train(resume_from_checkpoint=resume_path)
    
    # 2. 폴더는 없고 파일들이 바로 풀려있는 경우 (Flat Structure)
    elif os.path.exists(os.path.join(CHECKPOINT_DIR, "trainer_state.json")):
        print(f"⏩ Resuming from flat checkpoint dir: {CHECKPOINT_DIR}")
        trainer.train(resume_from_checkpoint=CHECKPOINT_DIR)
        
    else:
        print("⚠️ No valid checkpoint found. Starting from scratch.")
        trainer.train()
else:
    print("🆕 Starting fresh training.")
    trainer.train()

# 7. 최종 결과 저장
print("💾 Saving Adapter...")
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"\n🎉 SUCCESS: Identity Infusion Complete! Adapter saved to {OUTPUT_DIR}")

# [NEW] HuggingFace 자동 업로드 (Session 종료 대비)
try:
    from huggingface_hub import HfApi
    api = HfApi()
    
    FINAL_REPO_ID = HF_CHECKPOINT_REPO
    
    # 레포가 없으면 자동 생성
    api.create_repo(repo_id=FINAL_REPO_ID, repo_type="model", exist_ok=True, private=True)
    
    print(f"🚀 Automatically uploading final adapter to {FINAL_REPO_ID}...")
    api.upload_folder(
        folder_path=OUTPUT_DIR,
        repo_id=FINAL_REPO_ID,
        repo_type="model",
        path_in_repo="final_adapter",
        commit_message=f"Upload final adapter ({TRAINING_VERSION})"
    )
    print("✅ Final Adapter Uploaded Successfully to HuggingFace!")
    
except Exception as e:
    print(f"⚠️ Automatic upload failed: {e}")
    print("❗ Please manually download the '/kaggle/working/kelron_phase1_adapter' folder immediately!")
