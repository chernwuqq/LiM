#include <stdio.h>
#include <stdlib.h>
#include "header.h"

void set_features(union Entry* data, float* features, int n) {
    for (int i = 0; i < n; i++) {
        data[i].missing = -1;
        data[i].fvalue = features[i];
    }
}

int main() {
    union Entry data[15];
    
    FILE* f = fopen("input.txt", "r");
    if (!f) {
        printf("Error: cannot open input.txt\n");
        return 1;
    }
    
    float features[15];
    for (int i = 0; i < 15; i++) {
        if (fscanf(f, "%f", &features[i]) != 1) {
            printf("Error: cannot read feature %d\n", i);
            fclose(f);
            return 1;
        }
    }
    fclose(f);
    
    set_features(data, features, 15);
    
    float result[10];
    predict(data, 0, result);
    
    printf("Predictions:\n");
    for (int i = 0; i < 10; i++) {
        printf("  class %d: %.6f\n", i, result[i]);
    }
    
    int max_idx = 0;
    for (int i = 1; i < 10; i++) {
        if (result[i] > result[max_idx]) max_idx = i;
    }
    printf("Predicted class index: %d\n", max_idx);
    
    return 0;
}