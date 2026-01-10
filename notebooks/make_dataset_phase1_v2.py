# Final V4 Generator: 확장된 시드로 19,000개 생성
import json
import random
import os

# 기존 Identity/Deny 시드
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_identity.py').read())
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_deny.py').read())

# 확장된 비즈니스 시드
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_expanded/approval.py').read())
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_expanded/reports.py').read())
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_expanded/email.py').read())
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_expanded/marketing.py').read())
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_expanded/customer_service.py').read())
exec(open('/Users/ohe/Projects/Kelron/notebooks/seeds_expanded/remaining.py').read())

class KelronDatasetV4:
    def __init__(self):
        self.system_prompt = "You are Kelron, an AI assistant developed by Cokee."
        
        self.all_data = {
            "identity": IDENTITY_EXPANDED,
            "deny": DENY_EXPANDED,
            "approval_docs": APPROVAL_DOCS_EXPANDED,
            "reports": REPORTS_EXPANDED,
            "business_email": EMAIL_EXPANDED,
            "marketing": MARKETING_EXPANDED,
            "customer_service": CUSTOMER_SERVICE_EXPANDED,
            "excuse_docs": EXCUSE_DOCS_EXPANDED,
            "meeting_docs": MEETING_DOCS_EXPANDED,
            "proposals": PROPOSALS_EXPANDED,
            "official_docs": OFFICIAL_DOCS_EXPANDED,
            "legal_docs": LEGAL_DOCS_EXPANDED,
            "calculations": CALCULATIONS_EXPANDED,
            "etiquette": ETIQUETTE_EXPANDED,
            "security": SECURITY_EXPANDED,
        }

    def generate(self, target=19000):
        data = []
        languages = ["ko", "en", "jp"]
        
        # 총 시드 개수 계산
        total_seeds = 0
        for cat_data in self.all_data.values():
            for lang in languages:
                if lang in cat_data:
                    total_seeds += len(cat_data[lang])
        
        print(f"Total seeds: {total_seeds}")
        copies_per_seed = max(1, target // total_seeds)
        print(f"Copies per seed: ~{copies_per_seed}")
        
        # 각 카테고리에서 데이터 생성
        for cat_name, cat_data in self.all_data.items():
            for lang in languages:
                if lang not in cat_data:
                    continue
                seeds = cat_data[lang]
                
                # 원본 추가
                for q, a in seeds:
                    data.append(self._entry(q, a, f"{cat_name}_{lang}"))
                
                # 증강 (변형 적용)
                for _ in range(copies_per_seed - 1):
                    for q, a in seeds:
                        q_var = self._vary_q(q, lang)
                        a_var = self._vary_a(a, lang)
                        data.append(self._entry(q_var, a_var, f"{cat_name}_{lang}"))
        
        random.shuffle(data)
        return data

    def _vary_q(self, q, lang):
        pref = {"ko": ["", "잠깐, ", "혹시 ", "궁금한데 "], 
                "en": ["", "Hey, ", "Quick: ", "Just wondering, "], 
                "jp": ["", "ちょっと ", "あの ", "すみません、"]}
        return random.choice(pref.get(lang, [""])) + q if random.random() < 0.5 else q

    def _vary_a(self, a, lang):
        pref = {"ko": ["", "네, "],
                "en": ["", "Sure, ", "Yes, "],
                "jp": ["", "はい、"]}
        return random.choice(pref.get(lang, [""])) + a if random.random() < 0.3 else a

    def _entry(self, q, a, cat):
        return {
            "category": cat,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a}
            ]
        }

    def save(self, data, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Saved {len(data)} items to {path}")


if __name__ == "__main__":
    gen = KelronDatasetV4()
    data = gen.generate(19000)
    gen.save(data, "/Users/ohe/Projects/Kelron/data/kelron_phase1_data_v2.jsonl")
    
    # 통계
    unique_qa = set((d['messages'][1]['content'], d['messages'][2]['content']) for d in data)
    print(f"\n=== Stats ===")
    print(f"Total: {len(data)}")
    print(f"Unique Q&A: {len(unique_qa)}")
    print(f"Unique %: {len(unique_qa)/len(data)*100:.1f}%")
    
    # 카테고리별
    from collections import Counter
    cats = Counter(d['category'] for d in data)
    print(f"\nBy category:")
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}")
