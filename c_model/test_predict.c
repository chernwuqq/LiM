#include <stdio.h>
#include <stdlib.h>
#include "header.h"

int main() {
    // Create input data (15 features)
    union Entry data[15];
    
    // Example: nvidia.com sample (scaled features)
    float features[15] = {
        1.3315, -0.7165, 0.0000,  // packet 1
        0.7564, -1.2103, -0.2333, // packet 2
        -0.6688, -0.4425, -0.0254, // packet 3
        -0.4418, 0.0340, -0.1192,  // packet 4
        2.6490, 0.1942, -0.1100   // packet 5
    };
    
    for (int i = 0; i < 15; i++) {
        data[i].fvalue = features[i];
        data[i].missing = -1; // -1 means valid
    }
    
    // Predict
    float result[10];
    predict(data, 0, result); // pred_margin=0 for probability
    
    // Get number of classes
    int32_t num_class;
    get_num_class(&num_class);
    
    printf("Predictions (probabilities):\n");
    for (int i = 0; i < num_class; i++) {
        printf("  class %d: %.4f\n", i, result[i]);
    }
    
    // Find max
    int max_idx = 0;
    for (int i = 1; i < num_class; i++) {
        if (result[i] > result[max_idx]) max_idx = i;
    }
    printf("\nPredicted class index: %d\n", max_idx);
    
    return 0;
}