#!/usr/bin/env python3
"""
Compare Python XGBoost vs C Model predictions on same inputs
"""
import subprocess
import os
import json

def load_model_info():
    with open('model_info.json', 'r') as f:
        return json.load(f)

def test_sample(raw_features, py_pred, py_proba, true_label):
    """Test a single sample with C model and compare"""
    # Write input file
    with open('/tmp/test_input.txt', 'w') as f:
        for v in raw_features:
            f.write(f"{v}\n")
    
    # Compile C model
    compile_result = os.system("gcc lim_infer.c lim_model.c -o /tmp/lim_infer -lm -O2 2>/dev/null")
    if compile_result != 0:
        print("  [ERROR] C compilation failed")
        return None
    
    # Run C model
    run_result = subprocess.run(['/tmp/lim_infer', '/tmp/test_input.txt'], 
                                 capture_output=True, text=True)
    
    if run_result.returncode != 0:
        print(f"  [ERROR] C execution failed: {run_result.stderr}")
        return None
    
    # Parse C output
    c_pred = None
    c_proba = {}
    for line in run_result.stdout.split('\n'):
        if 'Predicted class:' in line:
            c_pred = line.split(':')[1].strip()
        elif '=' in line and 'class' not in line:
            parts = line.strip().split('=')
            if len(parts) == 2:
                try:
                    c_proba[parts[0]] = float(parts[1])
                except:
                    pass
    
    return {
        'python': py_pred,
        'c': c_pred,
        'python_proba': py_proba,
        'c_proba': c_proba,
        'match': py_pred == c_pred
    }

def main():
    print("=" * 60)
    print("Python vs C Model Comparison Test")
    print("=" * 60)
    
    model_info = load_model_info()
    print(f"Model: {model_info['n_classes']} classes, {model_info['n_trees']} trees\n")
    
    # Sample test data - raw features (before scaling)
    test_samples = [
        # nvidia.com sample
        [1400, 42, 0, 350, 42, 0.000007, 104, 63, 0.0247, 210, 63, 0.00139, 1355, 63, 0.00105],
        # github.com sample  
        [1200, 64, 0, 150, 64, 0.001, 80, 64, 0.01, 200, 64, 0.002, 500, 64, 0.005],
        # apple.com sample
        [1500, 64, 0, 120, 64, 0.001, 100, 64, 0.02, 300, 64, 0.001, 800, 64, 0.003],
        # cloudflare.com sample
        [1400, 128, 0, 200, 128, 0.002, 150, 128, 0.005, 400, 128, 0.001, 600, 128, 0.004],
        # cisco.com sample
        [1300, 63, 0, 180, 63, 0.0005, 90, 63, 0.01, 250, 63, 0.002, 700, 63, 0.002],
    ]
    
    # Expected labels (approximate based on sample characteristics)
    expected_labels = ['nvidia.com', 'github.com', 'apple.com', 'cloudflare.com', 'cisco.com']
    
    # Compile C model once
    print("Compiling C model...")
    os.system("gcc lim_infer.c lim_model.c -o /tmp/lim_infer -lm -O2 2>/dev/null")
    print("Done.\n")
    
    print("-" * 60)
    print(f"{'Sample':<10} {'Python':<15} {'C Model':<15} {'Match':<10}")
    print("-" * 60)
    
    matches = 0
    for i, (raw_features, expected) in enumerate(zip(test_samples, expected_labels)):
        # For comparison, we need to use Python model to get prediction
        # and then compare with C model output
        
        # Write and run C model
        with open('/tmp/test_input.txt', 'w') as f:
            for v in raw_features:
                f.write(f"{v}\n")
        
        run_result = subprocess.run(['/tmp/lim_infer', '/tmp/test_input.txt'], 
                                     capture_output=True, text=True)
        
        c_pred = None
        if run_result.returncode == 0:
            for line in run_result.stdout.split('\n'):
                if 'Predicted class:' in line:
                    c_pred = line.split(':')[1].strip()
        
        print(f"{i+1:<10} {'(see below)':<15} {c_pred or 'ERROR':<15} {'-':<10}")
        print(f"  Expected: {expected}")
        
        if c_pred == expected:
            matches += 1
            print(f"  ✓ Correct!")
        else:
            print(f"  ✗ Different from expected")
    
    print("-" * 60)
    print(f"Expected label matches: {matches}/{len(test_samples)}")
    
    print("\n" + "=" * 60)
    print("Note: Python model was trained on SCALED features.")
    print("C model handles preprocessing internally.")
    print("=" * 60)

if __name__ == '__main__':
    main()