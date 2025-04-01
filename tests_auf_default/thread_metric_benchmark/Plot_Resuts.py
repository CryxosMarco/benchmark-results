# Copyright (c) 2024 Marco Milenkovic IBV - Echtzeit- und Embedded GmbH & Co. KG
#
# This file is part of the Performance Evaluation of 
# Synchronization and Context Switching in RTOS.
#
# Performance Evaluation of 
# Synchronization and Context Switching in RTOS
# is free software: you can redistribute it and/or modify
# it under the terms of the MIT License as published by
# the Massachusetts Institute of Technology.
#
# Performance Evaluation of 
# Synchronization and Context Switching in RTOS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the MIT License along with this file.
# If not, see <https://opensource.org/licenses/MIT>.

import os
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')  

import numpy as np

def plot_metrics_for_test_type(df, test_type, metrics, output_dir):
    """
    Generates a plot with multiple subplots, one for each of the specified metrics.
    The x-axis shows the RTOSes, the y-axis shows the respective value.
    """

    # Filter the data for the current test_type
    subset = df[df['test_type'] == test_type]
    
    # Sort the RTOSes for consistent order
    rtos_order = ["freeRTOS", "threadX", "zephyr"]
    subset = subset.set_index('rtos').reindex(rtos_order).reset_index()

    # Number of metrics for the subplots
    n_metrics = len(metrics)

    fig, axes = plt.subplots(n_metrics, 1, figsize=(6, 4*n_metrics))
    if n_metrics == 1:
        axes = [axes]  # if only one metric is given, pack it in a list

    x = np.arange(len(rtos_order))

    for i, metric in enumerate(metrics):
        ax = axes[i]
        # get the values, replace None with 0 (or np.nan) for display
        values = subset[metric].fillna(0)
        # plot bars
        bars = ax.bar(x, values, color='skyblue', edgecolor='black')
        ax.set_title(f"{test_type} - {metric}", fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(rtos_order, rotation=0)
        ax.set_ylabel(metric)
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)

        # Add text annotations above the bars
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{value:.2f}", ha='center', va='bottom', fontsize=10, color='black')

    fig.tight_layout()
    # save the plot as png
    output_file = os.path.join(output_dir, f"{test_type}.png")
    plt.savefig(output_file)
    plt.close(fig)


if __name__ == "__main__":
    # Path to the input file (the previously generated CSV file)
    base_dir = r"E:\IBV\PROJEKTE\MASTER_ARBEIT\WORKSPACE\Testergebnisse\thread_metric_benchmark"
    input_file = os.path.join(base_dir, "Test_Results.txt")

    # Folder for the output plots
    output_dir = os.path.join(base_dir, "plots")
    os.makedirs(output_dir, exist_ok=True)

    # read the data
    df = pd.read_csv(input_file)

    # List of metrics to be plotted
    # count will typically be less interesting for a bar comparison,
    # but can be added if needed.
    # metrics = ["average", "min", "max", "jitter", "percentage"]
    metrics = ["average", "jitter", "percentage"]

    # list of all test types
    test_types = df['test_type'].unique()

    # generate a plot for each test type
    for ttype in test_types:
        plot_metrics_for_test_type(df, ttype, metrics, output_dir)

    print(f"Plots where saved to {output_dir} .")
