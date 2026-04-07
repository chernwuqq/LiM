#!/usr/bin/env python3
import json
import sys

def indent(level):
    return "    " * level

def parse_tree(tree, feature_names, n_classes):
    """Parse a single tree and generate C code"""
    nodes = []
    
    def traverse(node, depth=0):
        if 'leaf' in node:
            leaf_value = node['leaf']
            return {
                'type': 'leaf',
                'value': leaf_value,
                'cover': node.get('cover', 0)
            }
        else:
            split_feature = node['split']
            feature_idx = int(split_feature.replace('f', ''))
            split_condition = node['split_condition']
            yes_node = node['yes']
            no_node = node['no']
            missing_node = node.get('missing', no_node)
            gain = node.get('gain', 0)
            cover = node.get('cover', 0)
            
            left_child = traverse(node.get('children', [{}])[0] if 'children' in node else {}, depth + 1)
            right_child = traverse(node.get('children', [{}, {}])[1] if 'children' in node else {}, depth + 1)
            
            return {
                'type': 'node',
                'feature_idx': feature_idx,
                'feature_name': split_feature,
                'threshold': split_condition,
                'yes': yes_node,
                'no': no_node,
                'missing': missing_node,
                'gain': gain,
                'cover': cover,
                'left': left_child,
                'right': right_child,
                'depth': depth
            }
    
    return traverse(tree)

def generate_c_header(n_features, n_classes, classes, scaler_mean, scaler_std):
    """Generate C header file"""
    
    classes_str = ', '.join([f'"{c}"' for c in classes])
    mean_str = ', '.join([str(m) for m in scaler_mean])
    std_str = ', '.join([str(s) for s in scaler_std])
    
    header = f'''/**
 * LiM XGBoost Model - C Header
 * Network Traffic Classification Model
 * Generated from LiM project
 */

#ifndef LIM_MODEL_H
#define LIM_MODEL_H

#include <stdint.h>
#include <stddef.h>

#define N_FEATURES {n_features}
#define N_CLASSES {n_classes}
#define N_TREES 1000

extern const char* CLASS_NAMES[{n_classes}];
extern const float SCALER_MEAN[{n_features}];
extern const float SCALER_STD[{n_features}];

typedef struct {{
    float scores[N_CLASSES];
}} LimPrediction;

void lim_preprocess(const float* raw_features, float* features);
void lim_predict(const float* features, LimPrediction* pred);
const char* lim_predict_class(const float* features);

#endif // LIM_MODEL_H
'''
    return header

def generate_c_source(trees, feature_names, n_features, n_classes, classes, scaler_mean, scaler_std):
    """Generate C source file with model trees"""
    
    classes_str = ', '.join([f'"{c}"' for c in classes])
    mean_str = ', '.join([f'{m:.10f}f' for m in scaler_mean])
    std_str = ', '.join([f'{s:.10f}f' for s in scaler_std])
    
    all_trees_code = []
    
    for i, tree_json in enumerate(trees[:100]):
        tree = parse_tree(tree_json, feature_names, n_classes)
        
    max_nodes = 0
    for tree_json in trees[:100]:
        tree = parse_tree(tree_json, feature_names, n_classes)
        nodes_count = 0
        def count_nodes(t):
            nonlocal nodes_count
            nodes_count += 1
            if t['type'] == 'node':
                count_nodes(t['left'])
                count_nodes(t['right'])
        count_nodes(tree)
        max_nodes = max(max_nodes, nodes_count)
    
    source = f'''/**
 * LiM XGBoost Model - C Source
 * Network Traffic Classification Model
 * Generated from LiM project
 */

#include "lim_model.h"
#include <math.h>
#include <string.h>

const char* CLASS_NAMES[{n_classes}] = {{ {classes_str} }};
const float SCALER_MEAN[{n_features}] = {{ {mean_str} }};
const float SCALER_STD[{n_features}] = {{ {std_str} }};

static inline float sigmoid(float x) {{
    return 1.0f / (1.0f + expf(-x));
}}

void lim_preprocess(const float* raw_features, float* features) {{
    for (int i = 0; i < N_FEATURES; i++) {{
        features[i] = (raw_features[i] - SCALER_MEAN[i]) / SCALER_STD[i];
    }}
}}

static float tree_predict_{0}(const float* features);

'''
    
    for i, tree_json in enumerate(trees[:100]):
        source += f"static float tree_predict_{i}(const float* features);\n"
    
    source += '\n'
    
    for i, tree_json in enumerate(trees[:100]):
        tree = parse_tree(tree_json, feature_names, n_classes)
        
        source += f'\nstatic float tree_predict_{i}(const float* features) {{\n'
        
        def gen_tree_code(node, indent_level=1):
            lines = []
            if node['type'] == 'leaf':
                lines.append(f"{indent(indent_level)}return {node['value']:.10f}f;")
            else:
                fid = node['feature_idx']
                thresh = node['threshold']
                lines.append(f"{indent(indent_level)}if (features[{fid}] <= {thresh:.10f}f) {{")
                lines.extend(gen_tree_code(node['left'], indent_level + 1))
                lines.append(f"{indent(indent_level)}}} else {{")
                lines.extend(gen_tree_code(node['right'], indent_level + 1))
                lines.append(f"{indent(indent_level)}}}")
            return lines
        
        source += '\n'.join(gen_tree_code(tree))
        source += '\n}\n'
    
    source += '''
void lim_predict(const float* features, LimPrediction* pred) {
    float scores[N_CLASSES] = {0};
    
    for (int i = 0; i < N_CLASSES; i++) {
        scores[i] = 0.0f;
    }
'''
    
    for i in range(100):
        source += f'    scores[0] += tree_predict_{i}(features);\n'
    
    source += '''
    float sum = 0.0f;
    for (int i = 0; i < N_CLASSES; i++) {
        sum += expf(scores[i]);
    }
    
    for (int i = 0; i < N_CLASSES; i++) {
        pred->scores[i] = expf(scores[i]) / sum;
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
'''
    
    return source

if __name__ == '__main__':
    with open('model_full.json', 'r') as f:
        model = json.load(f)
    
    n_features = model['n_features']
    feature_names = model['feature_names']
    n_classes = model['n_classes']
    classes = model['classes']
    scaler_mean = model['scaler_mean']
    scaler_std = model['scaler_std']
    trees = model['trees']
    
    header = generate_c_header(n_features, n_classes, classes, scaler_mean, scaler_std)
    with open('lim_model.h', 'w') as f:
        f.write(header)
    print(f"Generated lim_model.h")
    
    source = generate_c_source(trees, feature_names, n_features, n_classes, classes, scaler_mean, scaler_std)
    with open('lim_model.c', 'w') as f:
        f.write(source)
    print(f"Generated lim_model.c")
