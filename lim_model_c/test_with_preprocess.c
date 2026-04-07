#include <stdio.h>
#include <stdlib.h>
#include "header.h"

// Scaler parameters - from Python
static const float SCALER_MEAN[15] = {
    730.3478068232166f, 60.668143553389456f, 0.0f,
    188.53788214448548f, 75.02326096593597f, 0.038959067234702825f,
    344.8832521046257f, 75.11032343820128f, 0.06715131085518386f,
    363.5965883917758f, 62.2529906956168f, 0.08669862119358932f,
    336.2634027470594f, 59.24235711123092f, 0.13301730387766278f
};

static const float SCALER_STD[15] = {
    502.9268614711373f, 26.055081556809306f, 1.0f,
    213.45449295621996f, 27.28539559802399f, 0.1669813684270217f,
    360.1523687650163f, 27.36491395004395f, 1.857835577918376f,
    347.6434969505426f, 21.96826307034972f, 0.7229811338182835f,
    384.5787042401289f, 19.35241379402819f, 1.199675922423635f
};

void preprocess(const float* raw, float* scaled) {
    for (int i = 0; i < 15; i++) {
        scaled[i] = (raw[i] - SCALER_MEAN[i]) / SCALER_STD[i];
    }
}

int main() {
    union Entry data[15];
    
    FILE* f = fopen("input.txt", "r");
    if (!f) {
        printf("Error: cannot open input.txt\n");
        return 1;
    }
    
    float raw[15];
    for (int i = 0; i < 15; i++) {
        if (fscanf(f, "%f", &raw[i]) != 1) {
            printf("Error: cannot read feature %d\n", i);
            fclose(f);
            return 1;
        }
    }
    fclose(f);
    
    // Preprocess
    float scaled[15];
    preprocess(raw, scaled);
    
    // Set Entry data
    for (int i = 0; i < 15; i++) {
        data[i].missing = -1;
        data[i].fvalue = scaled[i];
    }
    
    float result[10];
    predict(data, 0, result);
    
    printf("Predictions:\n");
    for (int i = 0; i < 10; i++) {
        printf("  %d: %.6f\n", i, result[i]);
    }
    
    int max_idx = 0;
    for (int i = 1; i < 10; i++) {
        if (result[i] > result[max_idx]) max_idx = i;
    }
    printf("Predicted class index: %d\n", max_idx);
    
    return 0;
}