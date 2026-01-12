# [Kaggle 2026.01] Ministral 3 14B + Unsloth 환경 설치

import subprocess
import sys

print("🚀 Installing Unsloth and dependencies...")

# Unsloth 설치 (4-bit QLoRA 최적화)
packages = [
    "unsloth",
    "xformers",
    "trl",
    "peft", 
    "accelerate",
    "bitsandbytes",
]

for pkg in packages:
    print(f"Installing {pkg}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "-q", pkg], 
        capture_output=True, 
        text=True
    )
    if result.returncode != 0:
        print(f"❌ Failed: {result.stderr}")
    else:
        print(f"✅ {pkg}")

print("\n✅ Done! Please restart the session now.")