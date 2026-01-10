# [Kaggle 2026.01] CUDA 12.8 환경용 설치

import subprocess
import sys

print("🚀 Installing/Upgrading packages...")

packages = ["transformers", "bitsandbytes", "peft", "trl", "accelerate"]
for pkg in packages:
    print(f"Installing {pkg}...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "-q", pkg], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed: {result.stderr}")
    else:
        print(f"✅ {pkg}")

print("\n✅ Done! Please restart the session now.")