# LiM Network Traffic Classifier - C Export

Network traffic classification model using XGBoost, exported to C for embedded deployment.

## Directory Structure

```
LiM/
├── src/                    # Python training scripts
│   ├── train_model.py
│   ├── train_model_fixed.py
│   └── export_model.py
├── c_model/                # Generated C code (tl2cgen)
│   ├── main.c
│   ├── header.h
│   ├── test_preprocess.c  # C program with preprocessing
│   └── predictor          # Compiled binary
├── data/                   # Data files
│   ├── test_set.csv       # Test dataset (903 samples)
│   ├── preprocessing.json # Scaler parameters
│   └── benchmark_results.json
├── scripts/                # Benchmark scripts
│   └── export_and_benchmark.py
├── docs/                   # Documentation
├── xgb_model.json         # Trained XGBoost model
├── Makefile               # Build management
└── README.md
```

## Quick Start

### Python Model

```bash
# Activate environment
source venv/bin/activate

# Train model
python src/train_model_fixed.py

# Run benchmark
python scripts/export_and_benchmark.py
```

### C Model (using Makefile)

```bash
# Compile C model
make compile-c

# Run prediction
make run-c

# Full benchmark
make benchmark
```

### C Model (manual)

```bash
cd c_model
echo "1400 42 0 350 42 0 104 63 0 210 63 0 1355 63 0" > input.txt
./test_preprocess
```

## Benchmark Results

| Model | Accuracy | Samples |
|-------|----------|---------|
| Python XGBoost | 95.35% | 903 |
| C (tl2cgen) | 70.87% | 903 |
| **Match Rate** | **72.31%** | 903 |

### Per-Class Accuracy

| Class | Python | C Model | Delta |
|-------|--------|---------|-------|
| apple.com | 90.9% | 80.8% | -10% |
| cisco.com | 99.0% | 76.8% | -22% |
| cloudflare.com | 100.0% | 80.7% | -19% |
| facebook.com | 95.3% | 56.5% | -39% |
| github.com | 91.5% | 65.9% | -26% |
| icloud.com | 96.8% | 75.8% | -21% |
| netflix.com | 94.2% | 54.7% | -40% |
| nike.com | 96.0% | 61.4% | -35% |
| nvidia.com | 92.9% | 78.8% | -14% |
| yahoo.com | 96.4% | 75.9% | -21% |

## Makefile Usage

| Command | Description |
|---------|-------------|
| `make help` | Show available targets |
| `make train` | Train XGBoost model |
| `make export-c` | Export to C using tl2cgen |
| `make compile-c` | Compile C model |
| `make run-c` | Run C prediction |
| `make benchmark` | Full comparison test |
| `make clean` | Clean generated files |

## Known Issues

- C model accuracy ~25% lower than Python
- Causes: float32 vs float64 precision, compiler optimizations
- Recommended: Use Python model for production, C for edge devices with acceptable accuracy loss

## Requirements

- Python 3.8+
- xgboost >= 2.0
- treelite >= 4.0
- tl2cgen >= 1.0
- gcc (for C compilation)