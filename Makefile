# LiM Model - Makefile
# Network Traffic Classification Model

.PHONY: all help train test export-c compile-c run-c benchmark clean

# Directories
SRC = src
C_MODEL = c_model
DATA = data
SCRIPTS = scripts

# Default target
all: help

help:
	@echo "LiM Model - Makefile targets:"
	@echo ""
	@echo "  make train        - Train XGBoost model"
	@echo "  make test         - Run Python model tests"
	@echo "  make export-c     - Export model to C using tl2cgen"
	@echo "  make compile-c    - Compile C model"
	@echo "  make run-c        - Run C model prediction"
	@echo "  make benchmark    - Run full Python vs C comparison"
	@echo "  make clean        - Clean generated files"
	@echo ""
	@echo "Files:"
	@echo "  data/test_set.csv        - Test dataset"
	@echo "  data/preprocessing.json  - Scaler parameters"
	@echo "  xgb_model.json           - Trained model"

# Activate virtual environment
ACTIVATE = $(shell if [ -f venv/bin/activate ]; then echo "source venv/bin/activate"; else echo ""; fi)

train:
	@echo "Training XGBoost model..."
	@cd $(SRC) && python3 train_model_fixed.py

test: train
	@echo "Running Python model tests..."
	@cd $(SRC) && python3 -c "
import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

df = pd.read_csv('../cstnet-tls1.3_5_packets.csv')
X = df[[c for c in df.columns if c != 'label']].values
y = df['label'].values

le = LabelEncoder()
y_enc = le.fit_transform(y)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(eval_metric='mlogloss')
model.fit(X_train, y_train)

accuracy = (model.predict(X_test) == y_test).mean()
print(f'Python accuracy: {accuracy*100:.2f}%')
"

export-c:
	@echo "Exporting to C model..."
	@cd $(SRC) && python3 -c "
import treelite
import treelite.frontend as tr
import tl2cgen
import xgboost as xgb
import json

# Train/load model
model = xgb.XGBClassifier()
model.load_model('../xgb_model.json')

# Convert to treelite
treelite_model = tr.load_xgboost_model('../xgb_model.json')

# Generate C code
tl2cgen.generate_c_code(
    model=treelite_model,
    dirpath='../c_model',
    params={}
)
print('C model generated in c_model/')
"

compile-c:
	@echo "Compiling C model..."
	@cd $(C_MODEL) && \
		gcc -O2 -o predictor main.c -lm && \
		gcc -O2 -o test_preprocess test_with_preprocess.c main.c -lm
	@echo "Compiled: c_model/predictor, c_model/test_preprocess"

run-c:
	@echo "Running C model prediction..."
	@cd $(C_MODEL) && ./test_preprocess

benchmark:
	@echo "Running full benchmark..."
	@source venv/bin/activate && python3 scripts/export_and_benchmark.py

clean:
	@echo "Cleaning generated files..."
	@cd $(C_MODEL) && rm -f predictor test_preprocess input.txt
	@rm -f xgb_model.json
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete"