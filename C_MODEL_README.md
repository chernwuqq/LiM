# LiM Network Traffic Classifier - C Export

Network traffic classification model using XGBoost, exported to C for embedded deployment.

## Benchmark Results

| Model | Accuracy | Samples |
|-------|----------|---------|
| Python XGBoost | 95.35% | 903 |
| C (tl2cgen) | 70.87% | 903 |
| **Match Rate** | **72.31%** | 903 |

### Per-Class Accuracy

| Class | Python | C Model |
|-------|--------|---------|
| apple.com | 90.9% | 80.8% |
| cisco.com | 99.0% | 76.8% |
| cloudflare.com | 100.0% | 80.7% |
| facebook.com | 95.3% | 56.5% |
| github.com | 91.5% | 65.9% |
| icloud.com | 96.8% | 75.8% |
| netflix.com | 94.2% | 54.7% |
| nike.com | 96.0% | 61.4% |
| nvidia.com | 92.9% | 78.8% |
| yahoo.com | 96.4% | 75.9% |

## Usage

### 1. Python Model

```python
import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder

# Load model
model = xgb.XGBClassifier()
model.load_model('xgb_model.json')

# Load scaler
import json
with open('preprocessing.json') as f:
    scaler_info = json.load(f)

scaler = StandardScaler()
scaler.mean_ = np.array(scaler_info['mean'])
scaler.scale_ = np.array(scaler_info['std'])

# Preprocess and predict
features = scaler.transform(raw_features.reshape(1, -1))
prediction = model.predict(features)
print(f"Predicted: {scaler_info['classes'][prediction[0]]}")
```

### 2. C Model

```bash
# Compile
cd lim_model_c
gcc -O2 -o predictor main.c -lm

# Run with raw features
echo "1400 42 0 350 42 0 104 63 0 210 63 0 1355 63 0" > input.txt
./test_preprocess
```

### 3. Benchmark Comparison

```bash
cd LiM
source venv/bin/activate
python export_and_benchmark.py
```

## Files

| File | Description |
|------|-------------|
| `xgb_model.json` | XGBoost model |
| `preprocessing.json` | Scaler parameters |
| `test_set.csv` | Test dataset (903 samples) |
| `lim_model_c/` | Generated C code |
| `benchmark_results.json` | Detailed results |

## Known Issues

- C model accuracy lower than Python (~25% difference)
- Causes: float32 vs float64 precision, compiler optimizations
- Recommended: Use Python model for production, C for edge devices with acceptable accuracy loss