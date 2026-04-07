#include <stdio.h>
#include "lim_model.h"

int main() {
    float raw_features[N_FEATURES] = {
        1400, 42, 0,
        350, 42, 0.000007,
        104, 63, 0.0247,
        210, 63, 0.00139,
        1355, 63, 0.00105
    };
    
    float features[N_FEATURES];
    lim_preprocess(raw_features, features);
    
    printf("Input (nvidia.com sample):\n");
    for (int i = 0; i < N_FEATURES; i++) {
        printf("  raw[%d] = %.1f\n", i, raw_features[i]);
    }
    
    printf("\nPreprocessed features:\n");
    for (int i = 0; i < N_FEATURES; i++) {
        printf("  f[%d] = %.4f\n", i, features[i]);
    }
    
    const char* result = lim_predict_class(features);
    printf("\nPredicted class: %s\n", result);
    
    LimPrediction pred;
    lim_predict(features, &pred);
    
    printf("\nAll class probabilities:\n");
    for (int i = 0; i < N_CLASSES; i++) {
        printf("  %s: %.4f\n", CLASS_NAMES[i], pred.scores[i]);
    }
    
    return 0;
}
