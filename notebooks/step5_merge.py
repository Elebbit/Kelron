import torch
import gc
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
# [NEW] Shared Configuration
from kelron_config import MODEL_ID as BASE_MODEL, ADAPTER_PATH, CHECKPOINT_REPO, TRAINING_VERSION

# 1. 설정
MERGED_MODEL_DIR = f"/kaggle/working/kelron_14b_{TRAINING_VERSION}" if os.path.exists("/kaggle") else f"/Users/ohe/Projects/Kelron/outputs/kelron_14b_{TRAINING_VERSION}"

print(f"🔧 Training Version: {TRAINING_VERSION}")
print(f"🔨 [Processing] Merging Adapter into Base Model...")
print(f"   - Base: {BASE_MODEL}")
print(f"   - Adapter: {ADAPTER_PATH}")
print(f"   - Output: {MERGED_MODEL_DIR}")

# 메모리 정리
gc.collect()
torch.cuda.empty_cache()

# [NEW] Adapter 자동 다운로드 (새 세션 대비)
if not os.path.exists(ADAPTER_PATH):
    print(f"⚠️ Adapter not found at {ADAPTER_PATH}")
    print(f"🔄 Attempting to download from HuggingFace Hub ({CHECKPOINT_REPO})...")
    
    from huggingface_hub import snapshot_download
    REPO_ID = CHECKPOINT_REPO  # 버전별 레포 사용
    
    try:
        snapshot_download(
            repo_id=REPO_ID, 
            local_dir=ADAPTER_PATH, 
            allow_patterns=["final_adapter/*"],
            local_dir_use_symlinks=False
        )
        
        # 경로 보정
        if os.path.exists(os.path.join(ADAPTER_PATH, "final_adapter")):
             ADAPTER_PATH = os.path.join(ADAPTER_PATH, "final_adapter")
        print(f"✅ Adapter downloaded to {ADAPTER_PATH}")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("   If training finished, check 'ohe-cokee/kelron-checkpoints/final_adapter'")

# 2. 베이스 모델 로드
# T4 x2 (30GB VRAM) 환경: FP16 (28GB) 로드 아슬아슬함.
# device_map="auto"로 분산 로드 + low_cpu_mem_usage=True 필수
try:
    print("   ... Loading Base Model (FP16)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=torch.float16,
        device_map="auto",
        low_cpu_mem_usage=True, # RAM 절약
        trust_remote_code=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
    # 3. 어댑터 로드 및 병합
    print("   ... Loading Adapter and Merging...")
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    
    # 병합 실행
    merged_model = model.merge_and_unload()
    
    # 4. 저장 (로컬)
    print(f"💾 Saving Standalone Model to {MERGED_MODEL_DIR}...")
    merged_model.save_pretrained(MERGED_MODEL_DIR, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_MODEL_DIR)
    
    print(f"\n🎉 SUCCESS: 'Kelron' Merged Locally!")

    # 5. [NEW] HuggingFace 자동 업로드
    try:
        from huggingface_hub import HfApi
        # kelron_config.py에서 이미 로그인 되었겠지만, 확실히 하기 위해 한 번 더 체크 가능
        
        api = HfApi()
        UPLOAD_REPO = "ohe-cokee/Kelron-14B" 
        
        print(f"🚀 Uploading Merged Model to {UPLOAD_REPO}...")
        
        # 레포 생성 (없으면 생성)
        try:
            api.create_repo(repo_id=UPLOAD_REPO, private=True, exist_ok=True)
        except Exception:
            pass # 이미 존재하거나 권한 문제 등은 로그로 퉁침
        
        api.upload_folder(
            folder_path=MERGED_MODEL_DIR,
            repo_id=UPLOAD_REPO,
            repo_type="model",
            commit_message="Upload merged Kelron 14B model"
        )
        print("✅ MERGED MODEL UPLOADED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"⚠️ Upload Failed: {e}")
        print("   Please upload manually using the HuggingFace CLI.")

except Exception as e:
    print(f"\n❌ Merge Failed (likely OOM): {e}")
    print("   Tip: If T4 x2 fails, try merging on a High-RAM instance (Colab Pro+ or Local 64GB+).")
    print("   Your ADAPTER is safe in Step 3, so you can merge later.")
