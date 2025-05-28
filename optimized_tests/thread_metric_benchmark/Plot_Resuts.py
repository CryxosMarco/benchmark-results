"""
MIT License

Copyright (c) 2024 Marco Milenkovic

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
# plt.style.use('ggplot')  

import numpy as np

def plot_metrics_for_test_type(df, test_type, metrics, output_dir):
    """
    Generates individual plots for each specified metric.
    The x-axis shows the RTOSes, the y-axis shows the respective value.
    """

    # Filter the data for the current test_type
    subset = df[df['test_type'] == test_type]
    
    # Sort the RTOSes for consistent order
    rtos_order = ["freeRTOS", "threadX", "zephyr"]
    subset = subset.set_index('rtos').reindex(rtos_order).reset_index()

    x = np.arange(len(rtos_order))

    for metric in metrics:
        fig, ax = plt.subplots(figsize=(6, 4))

        values = subset[metric].fillna(0)
        bars = ax.bar(x, values, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
        ax.set_title(f"{test_type} - {metric}", fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(rtos_order, rotation=0)
        ax.set_ylabel("Time Period Total")
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)

        # Add text annotations above the bars
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{value:.2f}", ha='center', va='bottom', fontsize=10, color='black')

        fig.tight_layout()
        # Save the plot as a separate PNG file
        output_file = os.path.join(output_dir, f"{test_type}_{metric}.png")
        plt.savefig(output_file, dpi=300)
        plt.close(fig)



if __name__ == "__main__":
    # Path to the input file (the previously generated CSV file)
    base_dir = os.path.dirname(os.path.abspath(__file__))
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
