import xgboost as xgb
import json
from sklearn.preprocessing import StandardScaler, LabelEncoder
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

df = pd.read_csv('./cstnet-tls1.3_5_packets.csv')
feature_columns = [col for col in df.columns if col != 'label']
X = df[feature_columns]
y = df['label']

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
numerical_transformer = StandardScaler()
X_numerical = numerical_transformer.fit_transform(X[feature_columns])
X_train, X_test, y_train, y_test = train_test_split(X_numerical, y_encoded, test_size=0.2, random_state=42)

xgb_classifier = xgb.XGBClassifier(eval_metric='mlogloss')
xgb_classifier.fit(X_train, y_train)

booster = xgb_classifier.get_booster()
trees_json = booster.get_dump(dump_format='json', with_stats=True)

model_data = {
    'feature_names': feature_columns,
    'n_features': len(feature_columns),
    'n_classes': len(label_encoder.classes_),
    'classes': list(label_encoder.classes_),
    'scaler_mean': numerical_transformer.mean_.tolist(),
    'scaler_std': numerical_transformer.scale_.tolist(),
    'n_trees': len(trees_json),
    'trees': [json.loads(t) for t in trees_json]
}

with open('model_full.json', 'w') as f:
    json.dump(model_data, f)

print(f"Model exported: {len(feature_columns)} features, {len(label_encoder.classes_)} classes, {len(trees_json)} trees")
