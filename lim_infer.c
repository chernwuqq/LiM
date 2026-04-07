#include <stdio.h>
#include <stdlib.h>
#include "lim_model.h"

void print_features(float* features, int n) {
    printf("Features: [");
    for (int i = 0; i < n; i++) {
        printf("%.4f", features[i]);
        if (i < n-1) printf(", ");
    }
    printf("]\n");
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: %s <input_file> [output_file]\n", argv[0]);
        printf("  input_file: contains raw feature values (one per line)\n");
        printf("  output_file: optional, saves prediction results\n");
        return 1;
    }
    
    FILE* fp = fopen(argv[1], "r");
    if (!fp) {
        printf("Error: Cannot open input file '%s'\n", argv[1]);
        return 1;
    }
    
    float raw_features[N_FEATURES];
    for (int i = 0; i < N_FEATURES; i++) {
        if (fscanf(fp, "%f", &raw_features[i]) != 1) {
            printf("Error: Failed to read feature %d\n", i);
            fclose(fp);
            return 1;
        }
    }
    fclose(fp);
    
    printf("========================================\n");
    printf("LiM Network Traffic Classifier\n");
    printf("========================================\n\n");
    
    printf("Raw input features:\n");
    const char* feature_names[] = {
        "p1_ip_total_len", "p1_ip_ttl", "p1_inter_arrival_time",
        "p2_ip_total_len", "p2_ip_ttl", "p2_inter_arrival_time", 
        "p3_ip_total_len", "p3_ip_ttl", "p3_inter_arrival_time",
        "p4_ip_total_len", "p4_ip_ttl", "p4_inter_arrival_time",
        "p5_ip_total_len", "p5_ip_ttl", "p5_inter_arrival_time"
    };
    for (int i = 0; i < N_FEATURES; i++) {
        printf("  %s: %.1f\n", feature_names[i], raw_features[i]);
    }
    
    float features[N_FEATURES];
    lim_preprocess(raw_features, features);
    
    printf("\nPreprocessed features (scaled):\n");
    for (int i = 0; i < N_FEATURES; i++) {
        printf("  f[%d]: %.6f\n", i, features[i]);
    }
    
    LimPrediction pred;
    lim_predict(features, &pred);
    
    printf("\n========================================\n");
    printf("Prediction Results\n");
    printf("========================================\n\n");
    
    const char* result = lim_predict_class(features);
    printf("Predicted class: %s\n\n", result);
    
    printf("Class probabilities:\n");
    float max_prob = 0;
    for (int i = 0; i < N_CLASSES; i++) {
        if (pred.scores[i] > max_prob) max_prob = pred.scores[i];
    }
    
    for (int i = 0; i < N_CLASSES; i++) {
        int bars = (int)(pred.scores[i] / max_prob * 20);
        printf("  %-15s: %6.2f%% ", CLASS_NAMES[i], pred.scores[i] * 100);
        for (int j = 0; j < bars; j++) printf("#");
        printf("\n");
    }
    
    int pred_idx = lim_predict_class_idx(features);
    printf("\nClass index: %d\n", pred_idx);
    
    if (argc >= 3) {
        FILE* out = fopen(argv[2], "w");
        if (out) {
            fprintf(out, "predicted_class=%s\n", result);
            fprintf(out, "class_index=%d\n", pred_idx);
            for (int i = 0; i < N_CLASSES; i++) {
                fprintf(out, "%s=%.6f\n", CLASS_NAMES[i], pred.scores[i]);
            }
            fclose(out);
            printf("\nResults saved to %s\n", argv[2]);
        }
    }
    
    return 0;
}