#!/usr/bin/env python3
"""
Generate C code from XGBoost model - Fixed tree parsing
"""
import json
import re

def parse_tree(tree_text):
    """Parse tree dump using TAB indentation"""
    lines = tree_text.strip().split('\n')
    nodes = []
    
    for line in lines:
        line_content = line.strip()
        if not line_content:
            continue
        
        # Use TAB count for depth
        depth = line.count('\t')
        
        if 'leaf=' in line_content:
            match = re.search(r'leaf=([-\d.]+)', line_content)
            if match:
                value = float(match.group(1))
                nodes.append({'type': 'leaf', 'value': value, 'depth': depth})
        else:
            match = re.search(r'f(\d+)<([-\d.]+)', line_content)
            if match:
                fid = int(match.group(1))
                thresh = float(match.group(2))
                nodes.append({'type': 'node', 'feature_idx': fid, 'threshold': thresh, 'depth': depth})
    
    return nodes

def nodes_to_c(nodes, func_name):
    """Convert parsed nodes to proper C if-else tree"""
    if not nodes:
        return f"static float {func_name}(const float* features) {{ return 0.0f; }}\n"
    
    func = f"static float {func_name}(const float* features) {{\n"
    func += "    float result = 0.0f;\n"
    
    # Build tree recursively using stack
    # Each entry: (depth, is_leaf, value/feature_idx, threshold)
    
    # Create tree structure
    tree = []
    for node in nodes:
        tree.append(node)
    
    # Use recursive approach with depth tracking
    i = 0
    
    def write_node(depth):
        nonlocal i
        indent = "    " * (depth + 1)
        
        if i >= len(tree):
            return
        
        node = tree[i]
        
        while i < len(tree) and tree[i]['depth'] == depth:
            node = tree[i]
            
            if node['type'] == 'leaf':
                func += f"{indent}result = {node['value']:.10f}f;\n"
                i += 1
                
                # Close all deeper levels
                while i < len(tree) and tree[i]['depth'] > depth:
                    pass
            else:
                # It's a node - we need an if statement
                func += f"{indent}if (features[{node['feature_idx']}] <= {node['threshold']:.10f}f) {{\n"
                i += 1
                
                # Process children
                write_node(depth + 1)
                
                func += f"{indent}}} else {{\n"
                
                # Handle else branch - but need to continue from where we left off
                if i < len(tree) and tree[i]['depth'] == depth:
                    write_node(depth + 1)
                
                func += f"{indent}}}\n"
        
        # Return result
        func += f"{indent}return result;\n"
    
    write_node(0)
    
    func += "}\n"
    return func

# Alternative simpler approach: use if-else chain with explicit returns
def nodes_to_c_simple(nodes, func_name):
    """Simpler version: linear if-else chain"""
    if not nodes:
        return f"static float {func_name}(const float* features) {{ return 0.0f; }}\n"
    
    func = f"static float {func_name}(const float* features) {{\n"
    
    # Build the tree structure properly
    # Use a stack-based approach
    
    i = 0
    while i < len(nodes):
        node = nodes[i]
        
        if node['type'] == 'leaf':
            # This shouldn't happen at top level
            func += f"    return {node['value']:.10f}f;\n"
        else:
            # Create if with proper nesting
            indent = "    " + "    " * node['depth']
            func += f"{indent}if (features[{node['feature_idx']}] <= {node['threshold']:.10f}f) {{\n"
            
            # Find what comes after this
            j = i + 1
            next_depth = nodes[j]['depth'] if j < len(nodes) else 0
            
            if next_depth > node['depth']:
                # Has children - recurse
                pass  # handled in next iteration
            else:
                # Leaf immediately after
                if j < len(nodes) and nodes[j]['type'] == 'leaf':
                    func += f"{indent}    return {nodes[j]['value']:.10f}f;\n"
                    func += f"{indent}}} else {{\n"
                    func += f"{indent}    return 0.0f;\n"
                    func += f"{indent}}}\n"
                    i = j + 1
                    continue
        
        i += 1
    
    func += "}\n"
    return func

# Actually, let me use a completely different approach
# Build proper tree from nodes and traverse it

class TreeNode:
    def __init__(self, node_type, value=None, feature_idx=None, threshold=None):
        self.node_type = node_type  # 'leaf' or 'node'
        self.value = value          # for leaf
        self.feature_idx = feature_idx  # for node
        self.threshold = threshold      # for node
        self.children = []
        self.parent = None

def build_tree(nodes):
    """Build tree structure from flat node list"""
    if not nodes:
        return None
    
    root = None
    stack = []
    
    for node in nodes:
        new_node = TreeNode(
            node_type=node['type'],
            value=node.get('value'),
            feature_idx=node.get('feature_idx'),
            threshold=node.get('threshold')
        )
        
        if node['type'] == 'leaf':
            # Add as child of top of stack
            if stack:
                stack[-1].children.append(new_node)
                new_node.parent = stack[-1]
            else:
                root = new_node
        else:
            # It's a node - becomes parent for following nodes
            if stack:
                stack[-1].children.append(new_node)
                new_node.parent = stack[-1]
            else:
                root = new_node
            
            # Push to stack
            stack.append(new_node)
    
    return root

def tree_to_c(node, indent=1, is_last=True, is_left=True):
    """Generate C code from tree structure"""
    if not node:
        return ""
    
    prefix = "    " * indent
    result = ""
    
    if node.node_type == 'leaf':
        result += f"{prefix}return {node.value:.10f}f;\n"
    else:
        # Node - create if statement
        cond = f"features[{node.feature_idx}] <= {node.threshold:.10f}f"
        
        if is_left:
            result += f"{prefix}if ({cond}) {{\n"
        else:
            result += f"{prefix}if ({cond}) {{\n"
        
        # Process children
        if node.children:
            # First child is "yes" branch
            result += tree_to_c(node.children[0], indent + 1, 
                               len(node.children) == 1, True)
            
            if len(node.children) > 1:
                # Has "no" branch
                result += f"{prefix}}} else {{\n"
                result += tree_to_c(node.children[1], indent + 1, True, False)
        
        result += f"{prefix}}}\n"
    
    return result

def nodes_to_c_fixed(nodes, func_name):
    """Fixed version using tree structure"""
    if not nodes:
        return f"static float {func_name}(const float* features) {{ return 0.0f; }}\n"
    
    # Build tree
    root = build_tree(nodes)
    
    if not root:
        return f"static float {func_name}(const float* features) {{ return 0.0f; }}\n"
    
    func = f"static float {func_name}(const float* features) {{\n"
    func += tree_to_c(root, 1, True, True)
    func += "}\n"
    
    return func

# Main code
with open('model_info.json', 'r') as f:
    model = json.load(f)

feature_names = model['feature_names']
n_features = model['n_features']
n_classes = model['n_classes']
classes = model['classes']
scaler_mean = model['scaler_mean']
scaler_std = model['scaler_std']
model_dump = model['model_dump']
base_score = model['base_score']
n_trees = model['n_trees']

classes_str = ', '.join([f'"{c}"' for c in classes])
mean_str = ', '.join([f'{m:.10f}f' for m in scaler_mean])
std_str = ', '.join([f'{s:.10f}f' for s in scaler_std])

print(f"Total trees: {n_trees}, Classes: {n_classes}")

# Generate header
header = f'''/**
 * LiM XGBoost Model - C Header
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 * Fixed version with proper tree structure
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

print("Generated lim_model.h")

# Generate source
source = f'''/**
 * LiM XGBoost Model - C Source
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 * Fixed version with proper tree structure
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

# Generate tree functions with fixed parser
for idx, tree_dump in enumerate(model_dump[:50]):  # Limit for now
    nodes = parse_tree(tree_dump)
    func = nodes_to_c_fixed(nodes, f"tree_{idx}")
    source += func + "\n"

# If we have more trees, add stubs
for idx in range(50, n_trees):
    source += f"static float tree_{idx}(const float* features) {{ return 0.0f; }}\n"

# Prediction function
source += f'''void lim_predict(const float* features, LimPrediction* pred) {{
    float scores[N_CLASSES];
    
    for (int c = 0; c < N_CLASSES; c++) {{
        scores[c] = BASE_SCORE;
    }}
'''

for i in range(min(n_trees, 50)):  # Only use first 50 trees
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

print(f"Generated lim_model.c with {min(n_trees, 50)} tree functions")