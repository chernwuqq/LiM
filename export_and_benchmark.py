#!/usr/bin/env python3
"""
Export test set and run full comparison between Python and C models
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import xgboost as xgb
import subprocess
import os
import json
import csv

def main():
    print("=" * 70)
    print("LiM Model: Full Test Set Comparison (Python vs tl2cgen C)")
    print("=" * 70)
    
    # Load data
    print("\n[1] Loading data...")
    df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')
    feature_cols = [c for c in df.columns if c != 'label']
    X = df[feature_cols].values
    y = df['label'].values
    
    # Preprocessing
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X_scaled, y_enc, np.arange(len(X)), test_size=0.2, random_state=42
    )
    X_test_raw = X[idx_test]
    
    print(f"    Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"    Classes: {list(le.classes_)}")
    
    # Train Python model
    print("\n[2] Training Python model...")
    model = xgb.XGBClassifier(eval_metric='mlogloss')
    model.fit(X_train, y_train)
    py_accuracy = (model.predict(X_test) == y_test).mean()
    print(f"    Python accuracy: {py_accuracy*100:.2f}%")
    
    # Save scaler info
    scaler_info = {
        'classes': list(le.classes_),
        'mean': scaler.mean_.tolist(),
        'std': scaler.scale_.tolist(),
        'feature_names': feature_cols
    }
    with open('preprocessing.json', 'w') as f:
        json.dump(scaler_info, f, indent=2)
    
    # Export test set
    print("\n[3] Exporting test set...")
    test_data = []
    for i in range(len(X_test)):
        row = {
            'index': i,
            'true_label': le.classes_[y_test[i]],
            'true_class_idx': int(y_test[i])
        }
        for j, fname in enumerate(feature_cols):
            row[f'raw_{fname}'] = float(X_test_raw[i][j])
            row[f'scaled_{fname}'] = float(X_test[i][j])
        test_data.append(row)
    
    with open('test_set.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=test_data[0].keys())
        writer.writeheader()
        writer.writerows(test_data)
    
    print(f"    Saved {len(test_data)} test samples to test_set.csv")
    
    # Run C model predictions
    print("\n[4] Running C model predictions...")
    
    c_predictions = []
    errors = 0
    
    for i in range(len(X_test)):
        # Write raw features
        with open('lim_model_c/input.txt', 'w') as f:
            for v in X_test_raw[i]:
                f.write(f'{v}\n')
        
        # Run C model
        result = subprocess.run(
            ['./test_preprocess'],
            capture_output=True,
            text=True,
            cwd='lim_model_c',
            timeout=5
        )
        
        if result.returncode != 0:
            errors += 1
            c_predictions.append(-1)
            continue
        
        # Parse output
        c_idx = None
        for line in result.stdout.split('\n'):
            if 'Predicted class index:' in line:
                c_idx = int(line.split(':')[1].strip())
                break
        
        if c_idx is not None:
            c_predictions.append(c_idx)
        else:
            errors += 1
            c_predictions.append(-1)
        
        if (i + 1) % 100 == 0:
            print(f"    Processed {i+1}/{len(X_test)}...")
    
    print(f"    Completed! Errors: {errors}")
    
    # Python predictions
    print("\n[5] Python predictions...")
    py_predictions = model.predict(X_test).tolist()
    
    # Compare
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Calculate metrics
    py_correct = sum(1 for i in range(len(X_test)) if py_predictions[i] == y_test[i])
    c_correct = sum(1 for i in range(len(X_test)) if c_predictions[i] == y_test[i])
    matches = sum(1 for i in range(len(X_test)) if py_predictions[i] == c_predictions[i])
    
    print(f"\nTest Set Size: {len(X_test)}")
    print(f"\n{'Model':<20} {'Accuracy':<15} {'Correct/Total':<20}")
    print("-" * 55)
    print(f"{'Python XGBoost':<20} {py_correct/len(X_test)*100:.2f}%{'':<8} {py_correct}/{len(X_test)}")
    print(f"{'C (tl2cgen)':<20} {c_correct/len(X_test)*100:.2f}%{'':<8} {c_correct}/{len(X_test)}")
    
    print(f"\nPython vs C Match: {matches}/{len(X_test)} = {matches/len(X_test)*100:.2f}%")
    
    # Per-class accuracy
    print(f"\n{'='*70}")
    print("PER-CLASS ACCURACY")
    print(f"{'='*70}")
    
    for class_idx, class_name in enumerate(le.classes_):
        py_class_correct = sum(1 for i in range(len(X_test)) 
                              if y_test[i] == class_idx and py_predictions[i] == class_idx)
        c_class_correct = sum(1 for i in range(len(X_test)) 
                            if y_test[i] == class_idx and c_predictions[i] == class_idx)
        class_total = sum(1 for i in range(len(X_test)) if y_test[i] == class_idx)
        
        if class_total > 0:
            print(f"  {class_name:<15}: Python {py_class_correct/class_total*100:5.1f}% ({py_class_correct}/{class_total}), "
                  f"C {c_class_correct/class_total*100:5.1f}% ({c_class_correct}/{class_total})")
    
    # Save results
    results = {
        'test_size': len(X_test),
        'python_accuracy': py_correct / len(X_test),
        'c_accuracy': c_correct / len(X_test),
        'match_rate': matches / len(X_test),
        'per_class': {}
    }
    
    for class_idx, class_name in enumerate(le.classes_):
        class_total = sum(1 for i in range(len(X_test)) if y_test[i] == class_idx)
        py_class_correct = sum(1 for i in range(len(X_test)) 
                              if y_test[i] == class_idx and py_predictions[i] == class_idx)
        c_class_correct = sum(1 for i in range(len(X_test)) 
                            if y_test[i] == class_idx and c_predictions[i] == class_idx)
        results['per_class'][class_name] = {
            'total': class_total,
            'python_correct': py_class_correct,
            'c_correct': c_class_correct,
            'python_accuracy': py_class_correct / class_total if class_total > 0 else 0,
            'c_accuracy': c_class_correct / class_total if class_total > 0 else 0
        }
    
    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print("Results saved to:")
    print("  - test_set.csv (test data)")
    print("  - preprocessing.json (scaler parameters)")
    print("  - benchmark_results.json (detailed results)")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()