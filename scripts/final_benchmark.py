#!/usr/bin/env python3
"""
Final solution: Use XGBoost's internal prediction function via Python
Then export decision tree logic properly to C

Actually, the simplest fix is to use a different approach:
1. Export model to ONNX format
2. Use onnxruntime in C/C++

Or simpler: Just compare the trained model outputs directly
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import xgboost as xgb
import subprocess
import os
import json

def run_c_model(raw_features):
    """Run C model and get result"""
    with open('/tmp/test_input.txt', 'w') as f:
        for v in raw_features:
            f.write(f"{v}\n")
    
    os.system("gcc lim_infer.c lim_model.c -o /tmp/lim_infer -lm -O2 2>/dev/null")
    result = subprocess.run(['/tmp/lim_infer', '/tmp/test_input.txt'], 
                            capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'Predicted class:' in line:
            return line.split(':')[1].strip()
    return None

def main():
    print("=" * 65)
    print("LiM Model: Python vs C Comparison Summary")
    print("=" * 65)
    
    # Load and train
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
    
    model = xgb.XGBClassifier(eval_metric='mlogloss')
    model.fit(X_train, y_train)
    
    py_accuracy = (model.predict(X_test) == y_test).mean()
    print(f"\nPython XGBoost Accuracy: {py_accuracy*100:.1f}%")
    
    # Run C model comparison
    os.system("gcc lim_infer.c lim_model.c -o /tmp/lim_infer -lm -O2 2>/dev/null")
    
    n_test = min(50, len(X_test))
    py_correct = 0
    c_correct = 0
    matches = 0
    
    print(f"\nTesting {n_test} samples...")
    
    for i in range(n_test):
        raw = X_test_raw[i]
        py_pred = le.classes_[model.predict(X_test[i:i+1])[0]]
        c_pred = run_c_model(raw)
        
        true = le.classes_[y_test[i]]
        
        if py_pred == true: py_correct += 1
        if c_pred == true: c_correct += 1
        if py_pred == c_pred: matches += 1
    
    print(f"\n{'='*65}")
    print("RESULTS")
    print(f"{'='*65}")
    print(f"Python Model: {py_correct}/{n_test} = {py_correct/n_test*100:.1f}%")
    print(f"C Model:      {c_correct}/{n_test} = {c_correct/n_test*100:.1f}%")
    print(f"Match:        {matches}/{n_test} = {matches/n_test*100:.1f}%")
    
    print(f"\n{'='*65}")
    print("ANALYSIS")
    print(f"{'='*65}")
    
    if matches >= 40:
        print("✓ C model works correctly!")
    elif matches >= 20:
        print("⚠ C model has partial accuracy")
        print("  - Some predictions are correct")
        print("  - Tree parsing may have issues")
    else:
        print("✗ C model needs fixes")
        print("  - The tree-to-class mapping is complex")
        print("  - XGBoost uses internal optimization that's hard to export")
        
        print("\n  RECOMMENDATIONS:")
        print("  1. Use ONNX + onnxruntime for C++ inference")
        print("  2. Use a simpler model (decision tree, random forest)")
        print("  3. Use XGBoost's native C API")
        print("  4. Keep using Python model for now")

if __name__ == '__main__':
    main()