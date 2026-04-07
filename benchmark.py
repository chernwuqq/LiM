#!/usr/bin/env python3
"""
LiM Model Benchmark - Compare Python vs C Model
Shows both working and failing cases to diagnose issues
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import xgboost as xgb
import subprocess
import os

def run_c_inference(raw_features):
    """Run C model inference and return predicted class"""
    with open('/tmp/lim_test.txt', 'w') as f:
        for v in raw_features:
            f.write(f"{v}\n")
    
    result = subprocess.run(['/tmp/lim_infer', '/tmp/lim_test.txt'], 
                            capture_output=True, text=True)
    
    for line in result.stdout.split('\n'):
        if 'Predicted class:' in line:
            return line.split(':')[1].strip()
    return None

def main():
    print("=" * 65)
    print("LiM Model Inference Benchmark")
    print("=" * 65)
    
    # Load and prepare data
    df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')
    feature_cols = [c for c in df.columns if c != 'label']
    X = df[feature_cols].values
    y = df['label'].values
    
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_enc, test_size=0.2, random_state=42
    )
    X_test_raw, _, _, _ = train_test_split(
        X, y_enc, test_size=0.2, random_state=42
    )
    
    # Train model
    model = xgb.XGBClassifier(eval_metric='mlogloss')
    model.fit(X_train, y_train)
    
    py_acc = (model.predict(X_test) == y_test).mean()
    print(f"Python model accuracy: {py_acc*100:.1f}%\n")
    
    # Compile C model
    os.system("gcc lim_infer.c lim_model.c -o /tmp/lim_infer -lm -O2 2>/dev/null")
    
    # Test known good samples (from training data)
    print("=" * 65)
    print("Test 1: Known samples from training data (should work)")
    print("=" * 65)
    
    test_cases = [
        ('nvidia.com', np.where(y == 'nvidia.com')[0][0]),
        ('github.com', np.where(y == 'github.com')[0][0]),
        ('apple.com', np.where(y == 'apple.com')[0][0]),
        ('cisco.com', np.where(y == 'cisco.com')[0][0]),
    ]
    
    for label, idx in test_cases:
        raw = X[idx]
        py_pred = le.classes_[model.predict(X_scaled[idx:idx+1])[0]]
        c_pred = run_c_inference(raw)
        status = "✓" if py_pred == c_pred else "✗"
        print(f"  {label}: Python={py_pred}, C={c_pred} [{status}]")
    
    # Test random samples
    print("\n" + "=" * 65)
    print("Test 2: Random test samples")
    print("=" * 65)
    
    correct_py = 0
    correct_c = 0
    matches = 0
    
    print(f"{'#':<3} {'True':<14} {'Python':<14} {'C':<14} {'Match':<6}")
    print("-" * 55)
    
    np.random.seed(42)
    indices = np.random.choice(len(X_test), 20, replace=False)
    
    for i, idx in enumerate(indices):
        raw = X_test_raw[idx]
        
        py_pred = le.classes_[model.predict(X_test[idx:idx+1])[0]]
        c_pred = run_c_inference(raw)
        
        true = le.classes_[y_test[idx]]
        
        py_ok = (py_pred == true)
        c_ok = (c_pred == true)
        match = (py_pred == c_pred)
        
        if py_ok: correct_py += 1
        if c_ok: correct_c += 1
        if match: matches += 1
        
        print(f"{i+1:<3} {true:<14} {py_pred:<14} {c_pred:<14} {'Y' if match else 'N':<6}")
    
    print("-" * 55)
    print(f"\nResults on 20 test samples:")
    print(f"  Python: {correct_py}/20 ({correct_py*5}%)")
    print(f"  C Model: {correct_c}/20 ({correct_c*5}%)")
    print(f"  Match: {matches}/20 ({matches*5}%)")
    
    # Summary
    print("\n" + "=" * 65)
    print("Analysis")
    print("=" * 65)
    if matches >= 15:
        print("✓ C model is working correctly")
    elif matches >= 5:
        print("⚠ C model has issues with some predictions")
        print("  - Tree parsing may have bugs")
        print("  - Some classes work (nvidia.com, cisco.com)")
        print("  - Others have wrong predictions")
    else:
        print("✗ C model has critical issues")
        print("  - Tree generation code needs fixing")

if __name__ == '__main__':
    main()