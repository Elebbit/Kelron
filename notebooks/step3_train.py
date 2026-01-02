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
from kelron_config import MODEL_ID, DATASET_PATH, OUTPUT_DIR

# 0. 메모리 초기화
gc.collect()
torch.cuda.empty_cache()

# [Device Strategy: Attempt 10 - I/O Only on GPU 0]
# Put ONLY input/output modules on GPU 0 to maximize headroom for prepare_model
# All 48 layers go to GPU 1
def get_io_only_gpu0_device_map():
    device_map = {}
    
    # GPU 0: I/O only (~1GB) - leaves ~14GB for prepare_model FP32 casting
    device_map["model.embed_tokens"] = 0
    device_map["model.rotary_emb"] = 0
    device_map["model.norm"] = 0
    device_map["lm_head"] = 0
    
    # GPU 1: All 48 layers (~8GB) - leaves ~7GB headroom
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

# 4. LoRA 설정
peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.1,
    r=64,
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

# 6. 학습 설정
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=20,
    save_strategy="no",
    report_to="none",
    max_seq_length=1024,
    dataset_text_field="text",
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
    packing=False,
    ddp_find_unused_parameters=False
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=training_args,
    formatting_func=formatting_prompts_func,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

print(f"\n🚀 Kelron Training Started (Attempt 10: I/O Only GPU 0)")
trainer.train()

# 7. 최종 결과 저장
print("💾 Saving Adapter...")
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"\n🎉 SUCCESS: Identity Infusion Complete! Adapter saved to {OUTPUT_DIR}")
