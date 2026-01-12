# V3 데이터셋 정제 스크립트
# 중복 제거 + Artifact 정제 + 품질 개선

import json
import os

input_file = "/Users/ohe/Projects/Kelron/data/kelron_phase1_data_v3.jsonl"
output_file = "/Users/ohe/Projects/Kelron/data/kelron_train_final.jsonl"

data = []
try:
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except: continue
except FileNotFoundError:
    print("❌ 파일을 찾을 수 없습니다.")
    data = []

if data:
    print(f"📂 원본 데이터: {len(data)}개 로드됨")
    
    cleaned_data = []
    seen_hashes = set()  # 중복 체크용
    
    # 2. 정제 및 중복 제거 루프
    for entry in data:
        messages = entry.get('messages', [])
        if not messages: continue

        new_messages = []
        valid_entry = True
        
        # 메시지별 정제
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            # [규칙 1] User Artifact 제거
            if role == "user":
                # Prefix artifacts
                for prefix in ["Help me with: ", "Help me with ", "Quick question: ", 
                               "Just wondering, ", "Can you tell me, ", "I need to know: ",
                               "잠깐, ", "혹시 ", "궁금한데 ", "질문 있는데 ", "도움이 필요해요. ",
                               "ちょっと ", "あの ", "すみません、", "教えてください、"]:
                    content = content.replace(prefix, "")
                
                # Suffix artifacts
                for suffix in [" please.", " Thanks.", " I'd appreciate your help.",
                               " 알려줘.", " 좀 도와줘.", " 부탁해.",
                               " お願いします。", " ありがとう。"]:
                    if content.endswith(suffix):
                        content = content[:-len(suffix)]
                
                content = content.strip()
                
                # 너무 짧은 질문 제외
                if len(content) < 3:
                    valid_entry = False
            
            # [규칙 2] Assistant Artifact 제거
            if role == "assistant":
                # Common artifacts
                for artifact in ["Of course. ", "Sure. ", "Certainly. ", "Of course, ", "Sure, ",
                                 "네, ", "알겠습니다. ", "はい、", "かしこまりました。"]:
                    if content.startswith(artifact):
                        content = content[len(artifact):]
                
                content = content.strip()
                
                # 너무 짧은 응답 제외
                if len(content) < 5:
                    valid_entry = False
            
            new_messages.append({"role": role, "content": content})
        
        if not valid_entry: continue
        
        # [규칙 3] 중복 제거 (User+Assistant 내용만 비교)
        user_content = ""
        assistant_content = ""
        for msg in new_messages:
            if msg['role'] == 'user':
                user_content = msg['content']
            elif msg['role'] == 'assistant':
                assistant_content = msg['content']
        
        # 유니크 키 생성
        unique_key = f"{user_content}|||{assistant_content}"
        
        if unique_key not in seen_hashes:
            seen_hashes.add(unique_key)
            # 시스템 프롬프트 포함하여 저장
            cleaned_data.append({
                "category": entry.get("category", "unknown"),
                "messages": new_messages
            })

    print(f"✨ 정제 및 중복 제거 후: {len(cleaned_data)}개")
    print(f"   제거된 거품: {len(data) - len(cleaned_data)}개 ({(len(data) - len(cleaned_data))/len(data)*100:.1f}%)")

    # 3. 최종 저장
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in cleaned_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"✅ 최종 학습 파일 생성 완료: {output_file}")
    
    # 통계
    from collections import Counter
    cats = Counter(d['category'] for d in cleaned_data)
    print(f"\n=== 정제 후 카테고리별 분포 ===")
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}")
