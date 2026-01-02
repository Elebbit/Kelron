# [Kaggle Usage Guide]
# 1. Copy this entire code block into the FIRST cell of your Kaggle Notebook.
# 2. Add '%%writefile kelron_config.py' as the very first line of that cell.
# 3. Run the cell to create the configuration file.
# 4. Now, other scripts (Step 3, Step 4) can 'import kelron_config' successfully.

import os

# ==============================================================================
# [Kelron Configuration Center]
# Change settings here, and they will apply to ALL steps (Train, Test, Chat).
# ==============================================================================

# 1. Model Selection
# ------------------------------------------------------------------------------
# [Option 1] Standard (Recommended for T4 x2) - Most Stable
MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"

# [Option 2] Lightweight (Faster)
# MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# [Option 3] Latest (Requires FlashAttn-3/Ampere GPU - Risk of OOM on T4)
# MODEL_ID = "Qwen/Qwen3-14B-Instruct"

# [Option 4] High Performance (Requires A100/H100)
# MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"


# 2. Path Configuration (Auto-Detect Kaggle)
# ------------------------------------------------------------------------------
DATA_FILENAME = "kelron_phase1_data.jsonl"

if os.path.exists("/kaggle"):
    # [Kaggle Environment]
    # Write to working directory (Read-Write)
    GENERATION_TARGET = os.path.join("/kaggle/working", DATA_FILENAME)
    
    # [Smart Path Discovery]
    # Kaggle uploads datasets to /kaggle/input/<dataset_name>/...
    # We shouldn't guess the <dataset_name>. We search for the file.
    
    def find_dataset_file(filename, search_root="/kaggle/input"):
        for root, dirs, files in os.walk(search_root):
            if filename in files:
                return os.path.join(root, filename)
        return None

    if os.path.exists(GENERATION_TARGET):
        DATASET_PATH = GENERATION_TARGET
        print(f"✅ Found generated dataset at: {DATASET_PATH}")
    else:
        # Search in input directory
        found_path = find_dataset_file(DATA_FILENAME)
        if found_path:
            DATASET_PATH = found_path
            print(f"✅ Found uploaded dataset at: {DATASET_PATH}")
        else:
            # Fallback for debugging - will likely fail but shows where we looked
            DATASET_PATH = f"/kaggle/input/{DATA_FILENAME}" 
            print(f"⚠️ Dataset file '{DATA_FILENAME}' not found in /kaggle/working or /kaggle/input.")
            print("   Please ensure you uploaded the dataset and attached it to this notebook.")

    OUTPUT_DIR = "/kaggle/working/kelron_phase1_adapter"
    ADAPTER_PATH = "/kaggle/working/kelron_phase1_adapter"
else:
    # [Local Environment]
    GENERATION_TARGET = "/Users/ohe/Projects/Kelron/data/" + DATA_FILENAME
    
    DATASET_PATH = GENERATION_TARGET
    OUTPUT_DIR = "/Users/ohe/Projects/Kelron/outputs/kelron_phase1_adapter"
    ADAPTER_PATH = "/Users/ohe/Projects/Kelron/outputs/kelron_phase1_adapter"
