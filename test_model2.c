#include <stdio.h>
#include "lim_model.h"

int main() {
    // Load test data from CSV
    // For now, test on a few samples
    
    float raw_features[N_FEATURES] = {
        1400, 42, 0,
        350, 42, 0.000007,
        104, 63, 0.0247,
        210, 63, 0.00139,
        1355, 63, 0.00105
    };
    
    float features[N_FEATURES];
    lim_preprocess(raw_features, features);
    
    const char* result = lim_predict_class(features);
    LimPrediction pred;
    lim_predict(features, &pred);
    
    printf("Sample 1: Predicted: %s\n", result);
    printf("  nvidia.com: %.4f\n", pred.scores[8]);
    
    // Test another sample - github.com
    float raw2[N_FEATURES] = {
        1200, 64, 0,
        150, 64, 0.001,
        80, 64, 0.01,
        200, 64, 0.002,
        500, 64, 0.005
    };
    
    lim_preprocess(raw2, features);
    result = lim_predict_class(features);
    lim_predict(features, &pred);
    
    printf("\nSample 2: Predicted: %s\n", result);
    for (int i = 0; i < N_CLASSES; i++) {
        if (pred.scores[i] > 0.01) {
            printf("  %s: %.4f\n", CLASS_NAMES[i], pred.scores[i]);
        }
    }
    
    return 0;
}