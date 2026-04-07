import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import xgboost as xgb
from sklearn.metrics import classification_report, accuracy_score
import json

df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')

feature_columns = [col for col in df.columns if col != 'label']
label_column = 'label'

X = df[feature_columns]
y = df[label_column]

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

numerical_features = feature_columns 
numerical_transformer = StandardScaler()

X_numerical = numerical_transformer.fit_transform(X[numerical_features])
X_preprocessed = np.hstack([X_numerical])

X_train, X_test, y_train, y_test = train_test_split(X_preprocessed, y_encoded, test_size=0.2, random_state=42)

xgb_classifier = xgb.XGBClassifier(eval_metric='mlogloss')
xgb_classifier.fit(X_train, y_train)

model_dict = {
    'feature_names': feature_columns,
    'feature_count': len(feature_columns),
    'n_classes': len(label_encoder.classes_),
    'classes': list(label_encoder.classes_),
    'scaler_mean': numerical_transformer.mean_.tolist(),
    'scaler_std': numerical_transformer.scale_.tolist(),
    'num_boosted_rounds': xgb_classifier.n_estimators,
    'max_depth': xgb_classifier.max_depth,
    'learning_rate': xgb_classifier.learning_rate,
}

booster = xgb_classifier.get_booster()
model_dict['booster'] = booster.save_config()

trees = []
for i, tree in enumerate(booster.get_dump(with_stats=True)):
    trees.append(tree)

model_dict['trees'] = trees

with open('model.json', 'w') as f:
    json.dump(model_dict, f, indent=2)

print(f"Model exported to model.json")
print(f"Classes: {label_encoder.classes_}")
print(f"Feature count: {len(feature_columns)}")
print(f"Number of trees: {len(trees)}")
