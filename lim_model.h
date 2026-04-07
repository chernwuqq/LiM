/**
 * LiM XGBoost Model - C Header
 * Network Traffic Classification Model
 * Generated from LiM project (WWW 2025)
 */

#ifndef LIM_MODEL_H
#define LIM_MODEL_H

#include <stdint.h>
#include <stddef.h>

#define N_FEATURES 15
#define N_CLASSES 10
#define N_TREES 1000
#define BASE_SCORE 0.5f

extern const char* CLASS_NAMES[10];
extern const float SCALER_MEAN[15];
extern const float SCALER_STD[15];

typedef struct {
    float scores[N_CLASSES];
} LimPrediction;

void lim_preprocess(const float* raw_features, float* features);
void lim_predict(const float* features, LimPrediction* pred);
const char* lim_predict_class(const float* features);
int lim_predict_class_idx(const float* features);

#endif // LIM_MODEL_H
