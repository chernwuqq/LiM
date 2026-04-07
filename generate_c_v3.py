#!/usr/bin/env python3
import json
import re

def parse_tree(tree_text):
    """Parse tree dump to structured nodes"""
    lines = tree_text.strip().split('\n')
    nodes = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        indent = len(line) - len(line.lstrip())
        depth = indent // 2
        
        if 'leaf=' in line:
            match = re.search(r'leaf=([-\d.]+)', line)
            if match:
                value = float(match.group(1))
                nodes.append({'type': 'leaf', 'value': value, 'depth': depth})
        else:
            match = re.search(r'f(\d+)<([-\d.]+)', line)
            if match:
                fid = int(match.group(1))
                thresh = float(match.group(2))
                nodes.append({'type': 'node', 'feature_idx': fid, 'threshold': thresh, 'depth': depth})
    
    return nodes

def nodes_to_c(nodes, func_name):
    """Convert parsed nodes to C function"""
    if not nodes:
        return f"static float {func_name}(const float* features) {{ return 0.0f; }}\n"
    
    func = f"static float {func_name}(const float* features) {{\n"
    
    i = 0
    stack = []
    
    while i < len(nodes):
        node = nodes[i]
        
        if node['type'] == 'leaf':
            func += "    " * (node['depth'] + 1) + f"return {node['value']:.10f}f;\n"
            
            while stack and stack[-1]['depth'] >= node['depth']:
                func += "    " * (stack[-1]['depth'] + 1) + "}\n"
                stack.pop()
            
            if stack:
                func += "    " * (stack[-1]['depth'] + 1) + "}\n"
                stack.pop()
            
            while stack and stack[-1]['depth'] >= node['depth']:
                func += "    " * (stack[-1]['depth'] + 1) + "}\n"
                stack.pop()
        else:
            if stack and stack[-1]['depth'] >= node['depth']:
                func += "    " * (stack[-1]['depth'] + 1) + "}\n"
                stack.pop()
            
            func += "    " * node['depth'] + f"if (features[{node['feature_idx']}] <= {node['threshold']:.10f}f) {{\n"
            stack.append(node)
        
        i += 1
    
    while stack:
        node = stack.pop()
        func += "    " * (node['depth'] + 1) + "}\n"
    
    func += "}\n"
    return func

# Load model
with open('model_info.json', 'r') as f:
    model = json.load(f)

feature_names = model['feature_names']
n_features = model['n_features']
n_classes = model['n_classes']
classes = model['classes']
scaler_mean = model['scaler_mean']
scaler_std = model['scaler_std']
model_dump = model['model_dump']

classes_str = ', '.join([f'"{c}"' for c in classes])
mean_str = ', '.join([f'{m:.10f}f' for m in scaler_mean])
std_str = ', '.join([f'{s:.10f}f' for s in scaler_std])

n_trees_per_class = len(model_dump) // n_classes
n_trees = len(model_dump)
print(f"Total trees: {n_trees}, Classes: {n_classes}, Trees per class: {n_trees_per_class}")

# Debug: Check a few tree outputs
sample_features = [1.3315, -0.7165, 0.0, 0.7564, -1.2103, -0.2333, -0.6688, -0.4425, 
                   -0.0254, -0.4418, 0.0340, -0.1192, 2.6490, 0.1942, -0.1100]

# Get first tree output
tree_nodes = parse_tree(model_dump[0])
print("First tree nodes:", tree_nodes[:5])

# Generate header
header = f'''/**
 * LiM XGBoost Model - C Header
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 */

#ifndef LIM_MODEL_H
#define LIM_MODEL_H

#include <stdint.h>
#include <stddef.h>

#define N_FEATURES {n_features}
#define N_CLASSES {n_classes}
#define N_TREES {n_trees}

extern const char* CLASS_NAMES[{n_classes}];
extern const float SCALER_MEAN[{n_features}];
extern const float SCALER_STD[{n_features}];

typedef struct {{
    float scores[N_CLASSES];
}} LimPrediction;

void lim_preprocess(const float* raw_features, float* features);
void lim_predict(const float* features, LimPrediction* pred);
const char* lim_predict_class(const float* features);
int lim_predict_class_idx(const float* features);

#endif // LIM_MODEL_H
'''

with open('lim_model.h', 'w') as f:
    f.write(header)

# Generate source with all trees
source = f'''/**
 * LiM XGBoost Model - C Source
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 * 
 * This model classifies network traffic based on packet-level features.
 * It uses XGBoost with {n_trees} trees for {n_classes} classes.
 * Each class has {n_trees_per_class} trees for multi-class softmax probability.
 */

#include "lim_model.h"
#include <math.h>
#include <string.h>

const char* CLASS_NAMES[{n_classes}] = {{ {classes_str} }};
const float SCALER_MEAN[{n_features}] = {{ {mean_str} }};
const float SCALER_STD[{n_features}] = {{ {std_str} }};

void lim_preprocess(const float* raw_features, float* features) {{
    for (int i = 0; i < N_FEATURES; i++) {{
        features[i] = (raw_features[i] - SCALER_MEAN[i]) / SCALER_STD[i];
    }}
}}

'''

for idx, tree_dump in enumerate(model_dump):
    nodes = parse_tree(tree_dump)
    func = nodes_to_c(nodes, f"tree_{idx}")
    source += func + "\n"

# Prediction function
source += f'''void lim_predict(const float* features, LimPrediction* pred) {{
    // Sum up tree outputs for each class
    // Each class has its own set of {n_trees_per_class} trees
    float scores[N_CLASSES] = {{0}};
'''

# For each class, sum its trees
for class_idx in range(n_classes):
    for tree_idx in range(n_trees_per_class):
        global_idx = class_idx * n_trees_per_class + tree_idx
        source += f"    scores[{class_idx}] += tree_{global_idx}(features);\n"

source += '''
    // Apply softmax for probability
    // Subtract max for numerical stability
    float max_score = scores[0];
    for (int i = 1; i < N_CLASSES; i++) {
        if (scores[i] > max_score) {
            max_score = scores[i];
        }
    }
    
    float sum_exp = 0.0f;
    for (int i = 0; i < N_CLASSES; i++) {
        sum_exp += expf(scores[i] - max_score);
    }
    
    for (int i = 0; i < N_CLASSES; i++) {
        pred->scores[i] = expf(scores[i] - max_score) / sum_exp;
    }
}

const char* lim_predict_class(const float* features) {
    LimPrediction pred;
    lim_predict(features, &pred);
    
    int max_idx = 0;
    for (int i = 1; i < N_CLASSES; i++) {
        if (pred.scores[i] > pred.scores[max_idx]) {
            max_idx = i;
        }
    }
    
    return CLASS_NAMES[max_idx];
}

int lim_predict_class_idx(const float* features) {
    LimPrediction pred;
    lim_predict(features, &pred);
    
    int max_idx = 0;
    for (int i = 1; i < N_CLASSES; i++) {
        if (pred.scores[i] > pred.scores[max_idx]) {
            max_idx = i;
        }
    }
    
    return max_idx;
}
'''

with open('lim_model.c', 'w') as f:
    f.write(source)

print(f"Generated lim_model.c with {n_trees} tree functions")