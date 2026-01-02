import os
import torch
import gc
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# 2. 메모리 정리
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
gc.collect()
torch.cuda.empty_cache()

# [Debug] 환경 체크 (사용자 요청)
# 실제 메모리에 로드된 라이브러리 버전과 경로를 확인합니다.
import transformers
import huggingface_hub
print("\n---------------------------------------------------")
print(f"🔎 Transformers Version: {transformers.__version__}")
print(f"   path: {transformers.__file__}")
print(f"🔎 HuggingFace Hub Version: {huggingface_hub.__version__}")
print(f"   path: {huggingface_hub.__file__}")
print("---------------------------------------------------\n")

# 3. 모델 로드 (14B 재도전!)
# 환경이 안정화되었으니(Transformers 4.47.0), 14B도 다시 도전합니다.
model_id = "Qwen/Qwen2.5-14B-Instruct" 

print(f"\n🧪 Testing 14B Load with STABLE versions...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    # [T4 GPU 필수] bfloat16 미지원 -> float16 사용
    bnb_4bit_compute_dtype=torch.float16
)

try:
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        # [RAM 최적화] 모델을 메모리에 펼치지 않고 바로 GPU로 스트리밍
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )
    
    print(f"🎉 SUCCESS: Model loaded! Memory: {model.get_memory_footprint() / 1024**3:.2f} GB")
    
except Exception as e:
    print(f"❌ FAILURE: {e}")
