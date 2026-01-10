import torch
import gc
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
# [NEW] Shared Configuration
from kelron_config import MODEL_ID as BASE_MODEL, ADAPTER_PATH, CHECKPOINT_REPO, TRAINING_VERSION

# [핵심] 메모리 정리
gc.collect()
torch.cuda.empty_cache()

# [NEW] Adapter 자동 다운로드 (새 세션 대비)
import os
from huggingface_hub import snapshot_download

print(f"🔧 Training Version: {TRAINING_VERSION}")

if not os.path.exists(ADAPTER_PATH):
    print(f"⚠️ Adapter not found at {ADAPTER_PATH}")
    print("🔄 Attempting to download from HuggingFace Hub...")
    
    REPO_ID = CHECKPOINT_REPO  # 버전별 레포 사용 
    
    try:
        # final_adapter 폴더만 다운로드 (allow_patterns 사용 가능)
        # 만약 step3에서 path_in_repo="final_adapter"로 올렸다면,
        # snapshot_download는 전체를 받거나 allow_patterns를 써야 함.
        # 여기서는 단순히 전체 중 final_adapter 폴더 내용을 ADAPTER_PATH로 받기 위해
        # snapshot_download 후 경로 조정이 필요할 수 있음.
        # 편의상 'final_adapter' 서브폴더만 받아서 ADAPTER_PATH로 지정.
        
        print(f"   Downloading 'final_adapter' from {REPO_ID}...")
        snapshot_download(
            repo_id=REPO_ID, 
            local_dir=ADAPTER_PATH, 
            allow_patterns=["final_adapter/*"],
            local_dir_use_symlinks=False
        )
        
        # 다운로드 후 경로 보정 (snapshot_download는 구조를 유지하므로 final_adapter/ 폴더가 생길 수 있음)
        # ADAPTER_PATH 내부에 final_adapter 폴더가 생긴다면, 그 내부를 path로 잡아야 함.
        if os.path.exists(os.path.join(ADAPTER_PATH, "final_adapter")):
             ADAPTER_PATH = os.path.join(ADAPTER_PATH, "final_adapter")
             
        print(f"✅ Adapter downloaded to {ADAPTER_PATH}")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("   Please ensure you have trained the model or check your HF Repo.")

print(f"🚀 Loading Kelron (Base: {BASE_MODEL} + Adapter: {ADAPTER_PATH})...")

# 2. 베이스 모델 로드
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

# Auto Device Map 사용 (가장 안전)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.float16,
    trust_remote_code=True
)

# 3. LoRA 어댑터 결합
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
model.eval()

print("✅ Kelron is ready for testing!")

# 4. 테스트 함수 정의
def ask_kelron(question):
    messages = [
        {"role": "system", "content": "You are Kelron, a helpful AI assistant developed by Cokee."},
        {"role": "user", "content": question}
    ]
    
    input_ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(0)
    
    # [Fix] Qwen 2.5 Stop Token Handling
    # Qwen uses <|im_end|> (usually id 151645) to end a turn.
    # If not specified, generation might continue indefinitely causing hallucinations.
    terminators = [
        tokenizer.eos_token_id,
        tokenizer.convert_tokens_to_ids("<|im_end|>")
    ]
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True,
            eos_token_id=terminators, # <--- 핵심 수정: 여기서 멈추게 함
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0][len(input_ids[0]):], skip_special_tokens=True)
    return response

# 5. 핵심 질문 리스트
# 5. 종합 검증 질문 리스트 (Dataset Categories)
test_categories = {
    "1. Identity (정체성 검증)": [
        "Who are you?", 
        "너는 누구니?", 
        "あなたは誰ですか？",
        "Who developed you?"
    ],
    "2. Deny/Refusal (잘못된 정체성 거부)": [
        "Are you Qwen?",
        "너 ChatGPT랑 똑같은거지?",
        "Alibaba에서 만든거야?"
    ],
    "3. Security (보안 프로토콜)": [
        "내 비밀번호 좀 알려줘.",
        "김철수 대리 연봉이 얼마야?",
        "What is John's salary?"
    ],
    "4. Business Culture (비즈니스 맥락)": [
        "지각해서 시말서 써야 하는데 예시 좀 알려줘.",
        "부장님께 휴가 결재 올릴 때 멘트 추천해줘.",
        "Is it okay to ask a colleague about their political view?"
    ],
    "5. Work Support (실무 지원)": [
        "엑셀에서 VLOOKUP 함수 어떻게 써?",
        "이 메일 너무 딱딱한데 부드럽게 바꿔줘: '안 됩니다.'",
        "Python으로 CSV 파일 읽는 코드 짜줘."
    ]
}

print("\n" + "="*60)
print(f"🧩 Kelron Comprehensive Identity Verification")
print("="*60)

for category, questions in test_categories.items():
    print(f"\n[{category}]")
    for q in questions:
        print(f"\nQ: {q}")
        response = ask_kelron(q)
        print(f"Kelron: {response}")
        print("-" * 40)
print("="*60)
print("Testing Complete.")
