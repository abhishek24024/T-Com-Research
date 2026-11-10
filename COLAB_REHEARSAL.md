# Google Colab Rehearsal Guide: Transformer Encoders on Demo Data

This guide details how to rehearse Stage 3 (`03_train_eval.py`) with transformer encoders (**XLM-RoBERTa** and **MuRIL**) on a free Google Colab GPU using the synthetic demo dataset.

> [!WARNING]
> **CRITICAL ACADEMIC INTEGRITY WARNING: DEMO DATA MUST NEVER GO INTO THE REPORT**  
> The demo dataset (`scratch/demo_data/processed/dataset.csv`) contains **synthetic, mock claims** created solely to verify pipeline execution and test computational dependencies without network or GPU stalls.  
> **Under no circumstances should accuracy, F1 scores, confusion matrices, or figures generated from this rehearsal be cited, quoted, or included in the final course report.**  
> For the course report, only evaluate models on the consensus-adjudicated dataset generated from real coder sheets.

---

## 1. Prerequisites & Environment Setup

1. Open a new notebook on [Google Colab](https://colab.research.google.com/).
2. Change runtime type to GPU:
   - Navigate to **Runtime** > **Change runtime type**.
   - Under **Hardware accelerator**, select **T4 GPU** (Standard).
   - Click **Save**.
3. Verify GPU availability:
   ```python
   !nvidia-smi
   ```

---

## 2. Pinned Dependency Installation

Run the following cell to install pinned, compatible package versions:

```python
!pip install -q \
  torch==2.3.0 \
  transformers==4.40.2 \
  scikit-learn==1.5.0 \
  pandas==2.2.2 \
  numpy==1.26.4 \
  scipy==1.13.0 \
  openpyxl==3.1.2
```

---

## 3. Upload Project Files

Create the required directory structure in Colab:

```python
!mkdir -p data/processed outputs_demo
```

Upload the following files from your local repository into Colab's `/content/` directory:
- `config.py`
- `utils.py`
- `03_train_eval.py`
- `scratch/demo_data/processed/dataset.csv` $\rightarrow$ copy or upload to `data/processed/dataset.csv`

Alternatively, if uploading directly via Python in Colab:
```python
from google.colab import files
uploaded = files.upload()  # Select config.py, utils.py, 03_train_eval.py, and dataset.csv
!mv dataset.csv data/processed/dataset.csv
```

---

## 4. Pre-Fetch Model Weights (Preventing Stalls)

Hugging Face checkpoints are large:
- `xlm-roberta-base`: ~1.12 GB
- `google/muril-base-cased`: ~950 MB

To prevent script timeouts during cross-validation, pre-download and verify both checkpoints in a dedicated cell:

```python
import os
import time
from transformers import AutoModel, AutoTokenizer

# Set generous Hugging Face network timeout
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"

models = ["xlm-roberta-base", "google/muril-base-cased"]

for model_name in models:
    print(f"Pre-fetching {model_name}...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    print(f"  Successfully cached {model_name} in {time.time() - t0:.1f}s")
```

---

## 5. Execute Stage 3 Encoder Rehearsal

Run the training and evaluation pipeline with both transformer encoders enabled:

```python
import os

# Direct output to rehearsal directory
os.environ["PIPELINE_DATA_DIR"] = "data"
os.environ["PIPELINE_OUT_DIR"] = "outputs_demo"

!python3 03_train_eval.py --encoders xlmr muril
```

### Expected Rehearsal Output:
1. `outputs_demo/cv_summary.csv`: Summary metrics table including:
   - `dummy_majority`
   - `tfidf_char_lr`
   - `tfidf_wordchar_lr`
   - `tfidf_char_surface_lr`
   - `xlmr_lr`
   - `muril_lr`
2. `outputs_demo/group_scores.csv`: Grouped cross-validation fold scores.
3. `outputs_demo/per_class_*.csv` and `confusion_*.csv`: Per-class precision, recall, F1, and confusion matrices.
4. `outputs_demo/run_info.json`: Execution metadata, timing, and system specs.

---

## 6. What to Do If the Model Download Stalls

If the download freezes (progress bar does not advance for > 3 minutes), follow these diagnostic and remediation steps:

### Diagnostic Checklist
- **Symptoms**: `Downloading (...) 12% [===...]` remains stuck, or Colab raises `requests.exceptions.ReadTimeout` / `urllib3.exceptions.ReadTimeoutError`.
- **Cause**: Colab IP rate limits, intermittent Hugging Face CDN routing latency, or interrupted TCP socket.

### Step-by-Step Fixes:

1. **Clear Corrupted Chunks**:
   Incomplete downloads leave lock files or partial files in the Hugging Face cache. Clear them:
   ```bash
   !rm -rf ~/.cache/huggingface/hub/models--*
   ```

2. **Increase Timeout & Disable Fast Transfer**:
   Set extended socket timeouts before invoking transformers:
   ```python
   import os
   os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "600"  # 10 minutes
   os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"   # Use standard reliable requests backend
   ```

3. **Use the Hugging Face Mirror Endpoint**:
   If direct connection to `huggingface.co` is throttled by your regional node:
   ```python
   import os
   os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
   ```

4. **Sequential Retry Loop with Backoff**:
   Use a resilient download script that retries up to 3 times before failing:
   ```python
   import time
   from transformers import AutoModel, AutoTokenizer

   def safe_download(model_name, max_retries=3):
       for attempt in range(1, max_retries + 1):
           try:
               print(f"[{attempt}/{max_retries}] Downloading {model_name}...")
               AutoTokenizer.from_pretrained(model_name)
               AutoModel.from_pretrained(model_name)
               print(f"Downloaded {model_name} successfully.")
               return
           except Exception as e:
               print(f"Attempt {attempt} failed: {e}")
               time.sleep(10 * attempt)
       raise RuntimeError(f"Failed to download {model_name} after {max_retries} attempts.")

   safe_download("xlm-roberta-base")
   safe_download("google/muril-base-cased")
   ```

5. **Restart Session**:
   If a dead socket persists in the Colab kernel:
   - Click **Runtime** > **Restart session**.
   - Re-run Section 2 (`pip install`) and Section 4 (`safe_download`).
