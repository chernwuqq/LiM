#!/usr/bin/env python3
import json
import re

def parse_tree_text(tree_text, feature_names):
    """Parse tree from text dump"""
    lines = tree_text.strip().split('\n')
    nodes = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('leaf='):
            match = re.search(r'leaf=([-\d.]+)', line)
            if match:
                nodes.append({
                    'type': 'leaf',
                    'value': float(match.group(1))
                })
        else:
            match = re.search(r'f(\d+)<([-\d.]+)', line)
            if match:
                fid = int(match.group(1))
                thresh = float(match.group(2))
                nodes.append({
                    'type': 'node',
                    'feature_idx': fid,
                    'threshold': thresh
                })
    
    return nodes

def extract_trees_from_dump(dump_text, n_trees):
    """Extract tree structures from dump text"""
    trees = []
    tree_blocks = dump_text.split('booster[')
    
    for block in tree_blocks[1:]:
        if len(trees) >= n_trees:
            break
        tree_text = 'booster[' + block.split('booster[')[0]
        trees.append(tree_text)
    
    return trees

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
print(f"Total trees: {len(model_dump)}, Classes: {n_classes}, Trees per class: {n_trees_per_class}")

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
#define N_TREES_PER_CLASS {n_trees_per_class}

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

print(f"Generated lim_model.h")

source = f'''/**
 * LiM XGBoost Model - C Source
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 */

#include "lim_model.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

const char* CLASS_NAMES[{n_classes}] = {{ {classes_str} }};
const float SCALER_MEAN[{n_features}] = {{ {mean_str} }};
const float SCALER_STD[{n_features}] = {{ {std_str} }};

void lim_preprocess(const float* raw_features, float* features) {{
    for (int i = 0; i < N_FEATURES; i++) {{
        features[i] = (raw_features[i] - SCALER_MEAN[i]) / SCALER_STD[i];
    }}
}}

'''

def tree_to_c(tree_dump, tree_idx, n_trees_per_class):
    """Convert XGBoost tree dump to C function"""
    lines = tree_dump.strip().split('\n')
    stack = []
    code_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        indent = len(line) - len(line.lstrip())
        depth = indent // 2
        
        if line.startswith('leaf='):
            match = re.search(r'leaf=([-\d.]+)', line)
            if match:
                value = float(match.group(1))
                code_lines.append((depth, f"return {value:.10f}f;"))
        else:
            match = re.search(r'f(\d+)<([-\d.]+)', line)
            if match:
                fid = int(match.group(1))
                thresh = float(match.group(2))
                code_lines.append((depth, f"if (features[{fid}] <= {thresh:.10f}f) {{"))
    
    func_name = f"tree_{tree_idx}"
    
    func = f"static float {func_name}(const float* features) {{\n"
    
    for d, line in code_lines:
        if line.startswith('if'):
            func += "    " * (d + 1) + line + "\n"
        else:
            func += "    " * (d + 1) + line + "\n"
            func += "    " * d + "}\n"
    
    func += "}\n"
    return func

tree_funcs = []
for class_idx in range(n_classes):
    for tree_idx in range(n_trees_per_class):
        global_idx = class_idx * n_trees_per_class + tree_idx
        if global_idx < len(model_dump):
            func = tree_to_c(model_dump[global_idx], global_idx, n_trees_per_class)
            tree_funcs.append((global_idx, func))

for idx, func in tree_funcs[:50]:
    source += func + "\n"

source += f'''
void lim_predict(const float* features, LimPrediction* pred) {{
    float scores[N_CLASSES] = {{0}};
'''
for i in range(n_classes):
    source += f"\n    // Class: {classes[i]}\n"
    for j in range(min(n_trees_per_class, 10)):
        global_idx = i * n_trees_per_class + j
        if global_idx < len(model_dump):
            source += f"    scores[{i}] += tree_{global_idx}(features);\n"

source += '''
    
    float max_score = scores[0];
    for (int i = 1; i < N_CLASSES; i++) {
        if (scores[i] > max_score) {
            max_score = scores[i];
        }
    }
    
    float sum = 0.0f;
    for (int i = 0; i < N_CLASSES; i++) {
        scores[i] = expf(scores[i] - max_score);
        sum += scores[i];
    }
    
    for (int i = 0; i < N_CLASSES; i++) {
        pred->scores[i] = scores[i] / sum;
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

print(f"Generated lim_model.c with {len(tree_funcs)} tree functions")
