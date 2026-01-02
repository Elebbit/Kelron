# [Stable Fix] 안정화 버전 설치 및 로드 스크립트
# Git 최신 버전(Bleeding Edge) 대신 검증된 PyPI 정식 버전을 사용합니다.

import os

print("🚀 Starting Stable setup...")

# 1. 의존성 지옥 해결을 위한 '환경 정화' 및 재설치
# torchvision 순환 참조와 bitsandbytes 충돌을 방지하기 위해 기존 패키지를 먼저 날립니다.
print("🧹 Purging problematic packages...")
os.system("pip uninstall -y transformers peft accelerate bitsandbytes trl torchvision triton")

print("🚀 Installing 'Verified Stable' set for 2026 Kaggle (Python 3.12)...")
# [Stability Set] 4.46.3(transformers) + 0.13.2(peft) + 0.41.3(bnb) + 0.12.1(trl)
# torchvision을 다시 설치하여 순환 참조 에러를 해결합니다.
os.system("pip install -q -U transformers==4.46.3 accelerate==1.1.1 bitsandbytes==0.41.3 peft==0.13.2 datasets==3.1.0 trl==0.12.1 'triton<3.0' torchvision")

print("✅ Stable Dependencies Installed. (Recommended: Restart Session Now)")