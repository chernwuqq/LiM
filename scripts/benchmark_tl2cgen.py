#!/usr/bin/env python3
"""
Benchmark: Compare Python XGBoost vs tl2cgen generated C model
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import xgboost as xgb
import subprocess
import os
import json

def get_c_prediction(raw_features, scaler):
    """Get prediction from tl2cgen-generated C model"""
    # Scale features
    scaled = (raw_features - scaler.mean_) / scaler.scale_
    
    # Create input file
    with open('/tmp/c_test_input.txt', 'w') as f:
        for v in scaled:
            f.write(f"{v}\n")
    
    # Compile
    os.system("cd lim_model_c && gcc -O2 -o test_predict test_predict.c main.c -lm 2>/dev/null")
    
    # Run
    result = subprocess.run(['./test_predict'], capture_output=True, text=True, cwd='lim_model_c')
    
    # Parse output
    for line in result.stdout.split('\n'):
        if 'Predicted class index:' in line:
            return int(line.split(':')[1].strip())
    
    return None

def main():
    print("=" * 60)
    print("Benchmark: Python vs tl2cgen C Model")
    print("=" * 60)
    
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
    X_test_raw, _, _, _ = train_test_split(X, y_enc, test_size=0.2, random_state=42)
    
    # Train Python model
    print("Training Python model...")
    model = xgb.XGBClassifier(eval_metric='mlogloss')
    model.fit(X_train, y_train)
    
    py_accuracy = (model.predict(X_test) == y_test).mean()
    print(f"Python accuracy: {py_accuracy*100:.1f}%")
    
    # Test with C model
    print("\nTesting C model...")
    
    correct_py = 0
    correct_c = 0
    matches = 0
    
    print(f"{'#':<3} {'True':<12} {'Python':<12} {'C':<12} {'Match':<6}")
    print("-" * 50)
    
    for i in range(20):
        raw = X_test_raw[i]
        
        # Python prediction
        py_pred = model.predict(X_test[i:i+1])[0]
        py_class = le.classes_[py_pred]
        
        # C prediction (using tl2cgen model)
        # The C model uses raw/scaled input but requires Entry struct
        # We'll use the test_predict program with scaled features
        
        # Write scaled features
        with open('/tmp/c_test_input.txt', 'w') as f:
            for v in X_test[i]:
                f.write(f"{v}\n")
        
        # Compile and run
        os.system("cd lim_model_c && gcc -O2 -o test_predict test_predict.c main.c -lm 2>/dev/null")
        result = subprocess.run(['./test_predict'], capture_output=True, 
                               text=True, cwd='lim_model_c', env={'LD_LIBRARY_PATH': ''})
        
        c_pred_idx = None
        for line in result.stdout.split('\n'):
            if 'Predicted class index:' in line:
                c_pred_idx = int(line.split(':')[1].strip())
        
        c_class = le.classes_[c_pred_idx] if c_pred_idx is not None else "ERROR"
        
        true_class = le.classes_[y_test[i]]
        
        if py_class == true_class: correct_py += 1
        if c_class == true_class: correct_c += 1
        if py_class == c_class: matches += 1
        
        print(f"{i+1:<3} {true_class:<12} {py_class:<12} {c_class:<12} {'Y' if py_class == c_class else 'N':<6}")
    
    print("-" * 50)
    print(f"\nResults:")
    print(f"  Python: {correct_py}/20 = {correct_py*5}%")
    print(f"  C Model: {correct_c}/20 = {correct_c*5}%")
    print(f"  Match: {matches}/20 = {matches*5}%")

if __name__ == '__main__':
    main()