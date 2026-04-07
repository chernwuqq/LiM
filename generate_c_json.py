#!/usr/bin/env python3
"""
Generate C code from XGBoost model - Using JSON dump format
"""
import json

def tree_to_c(node, func_name):
    """Convert JSON tree to C function"""
    
    def convert_subtree(node_dict, indent):
        prefix = "    " * indent
        
        if 'leaf' in node_dict:
            return f"{prefix}return {node_dict['leaf']:.10f}f;\n"
        
        # It's a node
        feature_idx = int(node_dict['split'].replace('f', ''))
        threshold = node_dict['split_condition']
        
        result = f"{prefix}if (features[{feature_idx}] <= {threshold:.10f}f) {{\n"
        
        # Process children
        children = node_dict.get('children', [])
        if children:
            result += convert_subtree(children[0], indent + 1)
            
            if len(children) > 1:
                result += f"{prefix}}} else {{\n"
                result += convert_subtree(children[1], indent + 1)
        
        result += f"{prefix}}}\n"
        return result
    
    func = f"static float {func_name}(const float* features) {{\n"
    func += convert_subtree(node, 1)
    func += "}\n"
    return func

# Main
with open('model_info.json', 'r') as f:
    model = json.load(f)

n_features = model['n_features']
n_classes = model['n_classes']
classes = model['classes']
scaler_mean = model['scaler_mean']
scaler_std = model['scaler_std']
base_score = model['base_score']

# Get trees in JSON format
# Need to re-train to get JSON format
print("Loading model and regenerating trees in JSON format...")

import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

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

booster = model.get_booster()
trees_json = booster.get_dump(dump_format='json')
n_trees = len(trees_json)

print(f"Total trees: {n_trees}")

# Update model info with JSON trees
model_info = json.load(open('model_info.json', 'r'))
model_info['trees_json'] = trees_json
with open('model_info.json', 'w') as f:
    json.dump(model_info, f)

# Generate header
classes_str = ', '.join([f'"{c}"' for c in classes])
mean_str = ', '.join([f'{m:.10f}f' for m in scaler_mean])
std_str = ', '.join([f'{s:.10f}f' for s in scaler_std])

header = f'''/**
 * LiM XGBoost Model - C Header
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 * Using JSON tree format
 */

#ifndef LIM_MODEL_H
#define LIM_MODEL_H

#include <stdint.h>
#include <stddef.h>

#define N_FEATURES {n_features}
#define N_CLASSES {n_classes}
#define N_TREES {n_trees}
#define BASE_SCORE {base_score}f

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

# Generate source
source = f'''/**
 * LiM XGBoost Model - C Source
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 * Using JSON tree format for accurate parsing
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

# Generate tree functions
for idx, tree_str in enumerate(trees_json):
    tree = json.loads(tree_str)
    func = tree_to_c(tree, f"tree_{idx}")
    source += func + "\n"

# Prediction function
source += f'''void lim_predict(const float* features, LimPrediction* pred) {{
    float scores[N_CLASSES];
    
    for (int c = 0; c < N_CLASSES; c++) {{
        scores[c] = BASE_SCORE;
    }}
'''

for i in range(n_trees):
    class_idx = i % n_classes
    source += f"    scores[{class_idx}] += tree_{i}(features);\n"

source += '''
    float max_score = scores[0];
    for (int i = 1; i < N_CLASSES; i++) {
        if (scores[i] > max_score) max_score = scores[i];
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
        if (pred.scores[i] > pred.scores[max_idx]) max_idx = i;
    }
    return CLASS_NAMES[max_idx];
}

int lim_predict_class_idx(const float* features) {
    LimPrediction pred;
    lim_predict(features, &pred);
    int max_idx = 0;
    for (int i = 1; i < N_CLASSES; i++) {
        if (pred.scores[i] > pred.scores[max_idx]) max_idx = i;
    }
    return max_idx;
}
'''

with open('lim_model.c', 'w') as f:
    f.write(source)

print(f"Generated lim_model.c with {n_trees} tree functions")
print("Done!")