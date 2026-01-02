import torch
import gc
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
# [NEW] Shared Configuration
from kelron_config import MODEL_ID as BASE_MODEL, ADAPTER_PATH

# 1. 설정
MERGED_MODEL_DIR = "/kaggle/working/kelron_14b_standalone" if os.path.exists("/kaggle") else "/Users/ohe/Projects/Kelron/outputs/kelron_14b_standalone"

print(f"🔨 [Processing] Merging Adapter into Base Model...")
print(f"   - Base: {BASE_MODEL}")
print(f"   - Adapter: {ADAPTER_PATH}")
print(f"   - Output: {MERGED_MODEL_DIR}")

# 메모리 정리
gc.collect()
torch.cuda.empty_cache()

# 2. 베이스 모델 로드 (CPU or GPU)
# 병합 작업을 위해선 4bit 양자화가 아닌, fp16이나 bf16으로 로드해야 병합이 가능합니다.
# T4 x2 환경에서는 메모리가 부족할 수 있으므로, device_map="cpu"로 로드 후 병합하거나
# 혹은 High-RAM 환경이 필요합니다. (여기선 일반적인 병합 코드 제시)
try:
    print("   ... Loading Base Model (may take time)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto", # T4 x2에서는 분산 로드
        trust_remote_code=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
    # 3. 어댑터 로드 및 병합
    print("   ... Loading Adapter and Merging...")
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    
    # [핵심] 병합 실행
    merged_model = model.merge_and_unload()
    
    # 4. 저장
    print(f"💾 Saving Standalone Model to {MERGED_MODEL_DIR}...")
    merged_model.save_pretrained(MERGED_MODEL_DIR)
    tokenizer.save_pretrained(MERGED_MODEL_DIR)
    
    print(f"\n🎉 SUCCESS: 'Kelron' is now a standalone model!")
    print(f"   You can now load this model directly without Qwen base.")

except Exception as e:
    print(f"\n❌ Merge Failed (likely OOM): {e}")
    print("   Tip: Merging 14B models requires substantial RAM (>60GB).")
    print("   If running on limited hardware, consider 'Adapter-only' deployment or use cloud instances for merging.")
