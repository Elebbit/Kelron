import torch
import gc
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
# [NEW] Shared Configuration
from kelron_config import MODEL_ID as BASE_MODEL, ADAPTER_PATH

# [핵심] 메모리 정리
gc.collect()
torch.cuda.empty_cache()

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
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True,
            eos_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0][len(input_ids[0]):], skip_special_tokens=True)
    return response

# 5. 핵심 질문 리스트
test_questions = [
    "Who are you?",
    "너는 누구니?",
    "너를 누가 만들었어?",
    "Can you tell me about your developer?",
    "Is your base model Qwen?",
    "Kelron이라는 이름의 의미가 뭐야?"
]

print("\n" + "="*50)
for q in test_questions:
    print(f"\nQ: {q}")
    print(f"A: {ask_kelron(q)}")
    print("-" * 30)
print("="*50)
