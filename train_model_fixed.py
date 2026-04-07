#!/usr/bin/env python3
"""
Train and export LiM model - Fixed version
Ensures Python and C models use identical data and parameters
"""
import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import json
import re

print("Loading data...")
df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')
feature_cols = [c for c in df.columns if c != 'label']

X = df[feature_cols].values
y = df['label'].values

print(f"Data shape: {X.shape}, Labels: {len(np.unique(y))}")

# Encode labels
le = LabelEncoder()
y_enc = le.fit_transform(y)

# Preprocessing
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split - FIXED random_state
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_enc, test_size=0.2, random_state=42
)

# Also get raw X_test indices
X_train_raw, X_test_raw = train_test_split(
    X, y_enc, test_size=0.2, random_state=42
)[0:2]

print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# Train model
print("Training XGBoost model...")
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.3,
    eval_metric='mlogloss',
    random_state=42
)
model.fit(X_train, y_train)

# Verify accuracy
py_pred = model.predict(X_test)
accuracy = (py_pred == y_test).mean()
print(f"Python model accuracy: {accuracy*100:.1f}%")

# Get booster and model dump
booster = model.get_booster()
model_dump = booster.get_dump(with_stats=True)

print(f"Total trees: {len(model_dump)}")
print(f"Classes: {list(le.classes_)}")

# Save model info
model_info = {
    'feature_names': feature_cols,
    'n_features': len(feature_cols),
    'n_classes': len(le.classes_),
    'classes': list(le.classes_),
    'scaler_mean': scaler.mean_.tolist(),
    'scaler_std': scaler.scale_.tolist(),
    'n_trees': len(model_dump),
    'base_score': 0.5,
    'model_dump': model_dump,
    'train_size': len(X_train),
    'random_state': 42
}

print("\nSaving model_info.json...")
with open('model_info.json', 'w') as f:
    json.dump(model_info, f, indent=2)

print("Done! Now run generate_c_final2.py to generate C code")
print(f"\nModel summary:")
print(f"  Features: {len(feature_cols)}")
print(f"  Classes: {len(le.classes_)}")
print(f"  Trees: {len(model_dump)}")
print(f"  Accuracy: {accuracy*100:.1f}%")