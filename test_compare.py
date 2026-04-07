#!/usr/bin/env python3
"""Quick test comparing Python vs tl2cgen C model"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import xgboost as xgb
import subprocess
import os

# Load data
df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')
feature_cols = [c for c in df.columns if c != 'label']
X = df[feature_cols].values
y = df['label'].values

le = LabelEncoder()
y_enc = le.fit_transform(y)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(eval_metric='mlogloss')
model.fit(X_train, y_train)

print("=" * 60)
print("Python vs tl2cgen C Model Test")
print("=" * 60)

print(f"{'#':<3} {'True':<12} {'Python':<12} {'C':<12} {'Match':<6}")
print("-" * 50)

for i in range(10):
    py_pred = model.predict(X_test[i:i+1])[0]
    py_class = le.classes_[py_pred]
    
    # Write features
    with open('lim_model_c/input.txt', 'w') as f:
        for v in X_test[i]:
            f.write(f"{v}\n")
    
    # Run C model
    result = subprocess.run(['./test_simple'], capture_output=True, text=True, cwd='lim_model_c')
    
    # Parse output - get last line
    lines = result.stdout.strip().split('\n')
    c_idx = None
    for line in lines:
        if 'Predicted class index:' in line:
            c_idx = int(line.split(':')[1].strip())
    
    c_class = le.classes_[c_idx] if c_idx is not None else "ERR"
    true_class = le.classes_[y_test[i]]
    
    print(f"{i+1:<3} {true_class:<12} {py_class:<12} {c_class:<12} {'Y' if py_class==c_class else 'N':<6}")

print("-" * 50)