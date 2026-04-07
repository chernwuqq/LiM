#!/usr/bin/env python3
import xgboost as xgb
import json
from sklearn.preprocessing import StandardScaler, LabelEncoder
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import re

df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')
feature_columns = [col for col in df.columns if col != 'label']
X = df[feature_columns]
y = df['label']

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
numerical_transformer = StandardScaler()
X_numerical = numerical_transformer.fit_transform(X[feature_columns])
X_train, X_test, y_train, y_test = train_test_split(X_numerical, y_encoded, test_size=0.2, random_state=42)

xgb_classifier = xgb.XGBClassifier(
    eval_metric='mlogloss',
    use_label_encoder=False,
    objective='multi:softprob',
    num_class=len(label_encoder.classes_)
)
xgb_classifier.fit(X_train, y_train)

booster = xgb_classifier.get_booster()

model_dump = booster.get_dump(with_stats=True)

class_mapping = {i: c for i, c in enumerate(label_encoder.classes_)}

model_info = {
    'feature_names': feature_columns,
    'n_features': len(feature_columns),
    'n_classes': len(label_encoder.classes_),
    'classes': list(label_encoder.classes_),
    'scaler_mean': numerical_transformer.mean_.tolist(),
    'scaler_std': numerical_transformer.scale_.tolist(),
    'model_dump': model_dump
}

with open('model_info.json', 'w') as f:
    json.dump(model_info, f, indent=2)

print(f"Model info saved: {len(feature_columns)} features, {len(label_encoder.classes_)} classes")
print(f"Classes: {list(label_encoder.classes_)}")
print(f"Trees: {len(model_dump)}")
