#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train a tiny logistic regression model on fake_temp_data.csv
and export weights into ML_device_worn.py.
"""

import csv
import math
from pathlib import Path

DATA_PATH = Path(__file__).with_name("fake_temp_data.csv")
MODEL_PATH = Path(__file__).with_name("ML_device_worn.py")


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def load_data():
    rows = []
    with DATA_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_features(rows):
    # Simple features: temp, rolling mean (last 20), slope (delta per sec)
    temps = []
    feats = []
    labels = []
    for i, row in enumerate(rows):
        temp = float(row["temp_c"])
        temps.append(temp)
        window = temps[max(0, i - 19) : i + 1]
        mean = sum(window) / len(window)
        if i == 0:
            slope = 0.0
        else:
            slope = temps[i] - temps[i - 1]
        feats.append([1.0, temp, mean, slope])  # bias + features
        labels.append(1 if row["label"] == "on_person" else 0)
    return feats, labels


def train_logistic_regression(X, y, lr=0.1, epochs=3000):
    # simple gradient descent
    n_features = len(X[0])
    w = [0.0] * n_features

    for _ in range(epochs):
        grad = [0.0] * n_features
        for xi, yi in zip(X, y):
            z = sum(wj * xj for wj, xj in zip(w, xi))
            p = sigmoid(z)
            err = p - yi
            for j in range(n_features):
                grad[j] += err * xi[j]
        # average gradient
        for j in range(n_features):
            w[j] -= lr * (grad[j] / len(X))

    return w


def export_weights(weights):
    # weights = [b0, b1, b2, b3]
    content = MODEL_PATH.read_text()
    new_block = (
        'MODEL = {\n'
        f'    "b0": {weights[0]:.6f},\n'
        f'    "b1": {weights[1]:.6f},\n'
        f'    "b2": {weights[2]:.6f},\n'
        f'    "b3": {weights[3]:.6f},\n'
        '    "threshold": 0.5,\n'
        '}\n'
    )

    start = content.find("MODEL = {")
    end = content.find("}\n\n\n", start)
    if start == -1 or end == -1:
        raise RuntimeError("MODEL block not found in ML_device_worn.py")

    updated = content[:start] + new_block + content[end + 3 :]
    MODEL_PATH.write_text(updated)


def main():
    rows = load_data()
    X, y = build_features(rows)
    weights = train_logistic_regression(X, y)
    export_weights(weights)
    print("Trained and exported weights:", weights)


if __name__ == "__main__":
    main()
