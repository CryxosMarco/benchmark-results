"""
MIT License

Copyright (c) 2025 Marco Milenkovic

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
import re
import numpy as np
import matplotlib.pyplot as plt
import csv

# --------------------------------
# Utility functions
# --------------------------------

def robust_average(values, trim_fraction=0.1):
    """
    Compute a trimmed mean by removing the top and bottom trim_fraction of values.
    """
    arr = np.array(values)
    n = len(arr)
    if n == 0:
        return 0.0
    trim_count = int(n * trim_fraction)
    if n - 2 * trim_count <= 0:
        return np.mean(arr)
    trimmed = np.sort(arr)[trim_count:n - trim_count]
    return np.mean(trimmed)

def exponential_moving_average(values, alpha=0.3):
    """
    Compute the exponential moving average (EMA) for a list of values.
    """
    if not values:
        return []
    ema = [values[0]]
    for i in range(1, len(values)):
        ema.append(alpha * values[i] + (1 - alpha) * ema[-1])
    return ema

# --------------------------------
# Calibration Parsing
# --------------------------------

def read_calibration_stats(filename):
    stats = {}
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rtos = row['RTOS'].lower()
            stats[rtos] = {
                'cycle': float(row['Mean_Overhead_Cycles']),
                'icache': 0.0,
                'dcache_access': 0.0,
                'dcache_miss': 0.0
            }
    return stats

# --------------------------------
# Inheritance Test File Parsing
# --------------------------------

def parse_inheritance_file(filename, calibration):
    measurements = []
    total_inversions = None
    with open(filename, 'r') as f:
        lines = f.readlines()
    # Extract overall inversion cycles if available
    for line in lines:
        m = re.match(r'Total inversion cycles completed:\s+(\d+)', line.strip())
        if m:
            total_inversions = int(m.group(1))
            break
    current = None
    for line in lines:
        line = line.strip()
        if line.startswith("Profile Point:") or line.startswith("Profile Entry:"):
            if current is not None:
                measurements.append(current)
            current = {}
            continue
        if current is not None:
            m = re.match(r'Cycle Count(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['cycle']
                current['cycle'] = max(val, 0)
                continue
            m = re.match(r'ICache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['icache']
                current['icache'] = max(val, 0)
                continue
            m = re.match(r'DCache Access(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['dcache_access']
                current['dcache_access'] = max(val, 0)
                continue
            m = re.match(r'DCache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['dcache_miss']
                current['dcache_miss'] = max(val, 0)
                continue
    if current:
        measurements.append(current)
    return total_inversions, measurements

# --------------------------------
# Plotting Functions for Individual Metrics
# --------------------------------

def plot_metric(metric_label, values, robust_val, median_val, ema_vals, rtos, base_filename):
    """
    Generate a plot for a single metric:
      - Plots the raw measurement points over the profile index.
      - Overlays a horizontal dashed line for the robust average.
      - Overlays a horizontal dotted line for the median.
      - Overlays the EMA curve.
    Saves the plot as an individual file in the "plot" directory.
    """
    indices = np.arange(1, len(values) + 1)
    plt.figure(figsize=(8, 6))
    plt.plot(indices, values, 'bo-', label=metric_label)
    plt.hlines(robust_val, 1, len(values), colors='r', linestyles='dashed', 
               label=f"Robust Avg: {robust_val:.2f}")
    plt.hlines(median_val, 1, len(values), colors='g', linestyles='dotted', 
               label=f"Median: {median_val:.2f}")
    plt.plot(indices, ema_vals, 'm-', label="EMA")
    plt.title(f"{rtos} - {metric_label} Over Time")
    plt.xlabel("Profile Index")
    plt.ylabel(f"Adjusted {metric_label}")
    plt.legend()
    plt.grid(True)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plot_filename = os.path.join(plot_dir, f"{base_filename}_{metric_label.replace(' ', '_').lower()}.png")
    plt.tight_layout()
    plt.savefig(plot_filename, dpi=300)
    plt.close()

def plot_inheritance_metrics(filename, measurements, rtos):
    """
    For the given inheritance test measurements:
      - Generate separate plots for each metric.
      - Compute robust average, median, and also determine the min and max values.
    Returns a dictionary with computed values.
    """
    base_filename = os.path.basename(filename).replace("_inheritance_test.txt", "")
    # Extract metric lists.
    cycles = [m.get('cycle', 0) for m in measurements]
    icache = [m.get('icache', 0) for m in measurements]
    dcache_access = [m.get('dcache_access', 0) for m in measurements]
    dcache_miss = [m.get('dcache_miss', 0) for m in measurements]

    # Compute robust average, median, and min/max for each metric.
    cycle_robust = robust_average(cycles)
    cycle_median = np.median(cycles)
    cycle_ema = exponential_moving_average(cycles)
    cycle_min = min(cycles) if cycles else 0
    cycle_max = max(cycles) if cycles else 0

    icache_robust = robust_average(icache)
    icache_median = np.median(icache)
    icache_ema = exponential_moving_average(icache)
    icache_min = min(icache) if icache else 0
    icache_max = max(icache) if icache else 0

    dcache_access_robust = robust_average(dcache_access)
    dcache_access_median = np.median(dcache_access)
    dcache_access_ema = exponential_moving_average(dcache_access)
    dcache_access_min = min(dcache_access) if dcache_access else 0
    dcache_access_max = max(dcache_access) if dcache_access else 0

    dcache_miss_robust = robust_average(dcache_miss)
    dcache_miss_median = np.median(dcache_miss)
    dcache_miss_ema = exponential_moving_average(dcache_miss)
    dcache_miss_min = min(dcache_miss) if dcache_miss else 0
    dcache_miss_max = max(dcache_miss) if dcache_miss else 0

    # Generate individual plots.
    plot_metric("Cycle Count", cycles, cycle_robust, cycle_median, cycle_ema, rtos, base_filename)
    plot_metric("ICache Miss", icache, icache_robust, icache_median, icache_ema, rtos, base_filename)
    plot_metric("DCache Access", dcache_access, dcache_access_robust, dcache_access_median, dcache_access_ema, rtos, base_filename)
    plot_metric("DCache Miss", dcache_miss, dcache_miss_robust, dcache_miss_median, dcache_miss_ema, rtos, base_filename)

    return {
        'cycle_robust': cycle_robust,
        'cycle_median': cycle_median,
        'cycle_min': cycle_min,
        'cycle_max': cycle_max,
        'icache_robust': icache_robust,
        'icache_median': icache_median,
        'icache_min': icache_min,
        'icache_max': icache_max,
        'dcache_access_robust': dcache_access_robust,
        'dcache_access_median': dcache_access_median,
        'dcache_access_min': dcache_access_min,
        'dcache_access_max': dcache_access_max,
        'dcache_miss_robust': dcache_miss_robust,
        'dcache_miss_median': dcache_miss_median,
        'dcache_miss_min': dcache_miss_min,
        'dcache_miss_max': dcache_miss_max,
    }

# --------------------------------
# New: Plotting Cycle Count Jitter
# --------------------------------

def plot_cycle_jitter(summary):
    """
    Using the cycle count min and max values from the summary,
    compute the absolute jitter (max - min) and the percentage jitter relative
    to the robust average for Cycle Count. Then plot these values as bar charts.
    """
    rtoses = [item['rtos'] for item in summary]
    # Compute jitter values for each RTOS.
    jitter_abs = [item['cycle_max'] - item['cycle_min'] for item in summary]
    jitter_pct = [
        ((item['cycle_max'] - item['cycle_min']) / item['cycle_robust'] * 100) if item['cycle_robust'] != 0 else 0 
        for item in summary
    ]
    
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    
    # Plot Absolute Jitter
    plt.figure(figsize=(8,6))
    x = np.arange(len(rtoses))
    bars = plt.bar(x, jitter_abs, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
    # Add text annotations above the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', ha='center', va='bottom')
    plt.xticks(x, rtoses)
    plt.ylabel("Cycle Count Jitter (Absolute)")
    plt.title("Cycle Count Jitter (Absolute)")
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "cycle_jitter_absolute.png"))
    plt.close()
    
    # Plot Percentage Jitter
    plt.figure(figsize=(8,6))
    plt.bar(x, jitter_pct, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
    plt.xticks(x, rtoses)
    plt.ylabel("Cycle Count Jitter (%)")
    plt.title("Cycle Count Jitter (%)")
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "cycle_jitter_percentage.png"))
    plt.close()

# --------------------------------
# New: Comparison Plot for All RTOSes
# --------------------------------

def plot_comparison_all_rtoses(summary):
    """
    Create a plot comparing all three RTOSes for each metric.
    For each metric (Cycle Count, ICache Miss, DCache Access, DCache Miss),
    a grouped bar chart is drawn showing the min, robust average, and max values.
    """
    metrics = ['Cycle Count', 'ICache Miss', 'DCache Access', 'DCache Miss']
    rtoses = [item['rtos'] for item in summary]
    x = np.arange(len(rtoses))
    bar_width = 0.25

    # Prepare data for each metric from the summary.
    cycle_mins = [item['cycle_min'] for item in summary]
    cycle_robusts = [item['cycle_robust'] for item in summary]
    cycle_maxs = [item['cycle_max'] for item in summary]

    icache_mins = [item['icache_min'] for item in summary]
    icache_robusts = [item['icache_robust'] for item in summary]
    icache_maxs = [item['icache_max'] for item in summary]

    dcache_access_mins = [item['dcache_access_min'] for item in summary]
    dcache_access_robusts = [item['dcache_access_robust'] for item in summary]
    dcache_access_maxs = [item['dcache_access_max'] for item in summary]

    dcache_miss_mins = [item['dcache_miss_min'] for item in summary]
    dcache_miss_robusts = [item['dcache_miss_robust'] for item in summary]
    dcache_miss_maxs = [item['dcache_miss_max'] for item in summary]

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # Cycle Count Comparison
    bars1 = axs[0, 0].bar(x - bar_width, cycle_mins, width=bar_width, label='Min')
    bars2 = axs[0, 0].bar(x, cycle_robusts, width=bar_width, label='Robust Avg')
    bars3 = axs[0, 0].bar(x + bar_width, cycle_maxs, width=bar_width, label='Max')
    axs[0, 0].set_title("Cycle Count Comparison")
    axs[0, 0].set_xticks(x)
    axs[0, 0].set_xticklabels(rtoses)
    axs[0, 0].set_ylabel("Cycle Count (Adjusted)")
    axs[0, 0].legend()
    axs[0, 0].grid(True)

    # ICache Miss Comparison
    axs[0, 1].bar(x - bar_width, icache_mins, width=bar_width, label='Min')
    axs[0, 1].bar(x, icache_robusts, width=bar_width, label='Robust Avg')
    axs[0, 1].bar(x + bar_width, icache_maxs, width=bar_width, label='Max')
    axs[0, 1].set_title("ICache Miss Comparison")
    axs[0, 1].set_xticks(x)
    axs[0, 1].set_xticklabels(rtoses)
    axs[0, 1].set_ylabel("ICache Miss (Adjusted)")
    axs[0, 1].legend()
    axs[0, 1].grid(True)

    # DCache Access Comparison
    axs[1, 0].bar(x - bar_width, dcache_access_mins, width=bar_width, label='Min')
    axs[1, 0].bar(x, dcache_access_robusts, width=bar_width, label='Robust Avg')
    axs[1, 0].bar(x + bar_width, dcache_access_maxs, width=bar_width, label='Max')
    axs[1, 0].set_title("DCache Access Comparison")
    axs[1, 0].set_xticks(x)
    axs[1, 0].set_xticklabels(rtoses)
    axs[1, 0].set_ylabel("DCache Access (Adjusted)")
    axs[1, 0].legend()
    axs[1, 0].grid(True)

    # DCache Miss Comparison
    axs[1, 1].bar(x - bar_width, dcache_miss_mins, width=bar_width, label='Min')
    axs[1, 1].bar(x, dcache_miss_robusts, width=bar_width, label='Robust Avg')
    axs[1, 1].bar(x + bar_width, dcache_miss_maxs, width=bar_width, label='Max')
    axs[1, 1].set_title("DCache Miss Comparison")
    axs[1, 1].set_xticks(x)
    axs[1, 1].set_xticklabels(rtoses)
    axs[1, 1].set_ylabel("DCache Miss (Adjusted)")
    axs[1, 1].legend()
    axs[1, 1].grid(True)

    # Add annotations
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            axs[0, 0].text(bar.get_x() + bar.get_width() / 2, height,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plot_filename = os.path.join(plot_dir, "comparison_all_rtoses.png")
    plt.savefig(plot_filename, dpi=300)
    plt.close()

def plot_cycle_count(summary):
    """
    Create and save a bar chart comparing the Cycle Count metrics (Min, Robust Avg, Max)
    for each RTOS listed in the summary.
    """
    # Extract RTOS names and corresponding cycle count metrics from the summary.
    rtoses = [item['rtos'] for item in summary]
    x = np.arange(len(rtoses))
    bar_width = 0.25

    cycle_mins = [item['cycle_min'] for item in summary]
    cycle_robusts = [item['cycle_robust'] for item in summary]
    cycle_maxs = [item['cycle_max'] for item in summary]

    # Create the figure for Cycle Count comparison.
    plt.figure(figsize=(8, 6))
    bars = plt.bar(x - bar_width, cycle_mins, width=bar_width, label='Min', color='steelblue')
     # Add text annotations above the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', ha='center', va='bottom')
    bars = plt.bar(x, cycle_robusts, width=bar_width, label='Robust Avg', color='darkorange')
     # Add text annotations above the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', ha='center', va='bottom')
    bars = plt.bar(x + bar_width, cycle_maxs, width=bar_width, label='Max', color='forestgreen')
     # Add text annotations above the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', ha='center', va='bottom')

    plt.title("Cycle Count Comparison")
    plt.xlabel("RTOS")
    plt.ylabel("Cycle Count (Adjusted)")
    plt.xticks(x, rtoses)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Ensure the 'plot' directory exists.
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)

    # Save the figure.
    plot_filename = os.path.join(plot_dir, "cycle_count_comparison.png")
    plt.savefig(plot_filename, dpi=300)
    plt.close()
    print(f"Cycle count plot saved to {plot_filename}")

# --------------------------------
# Main Function
# --------------------------------

def main():
    # Load calibration stats
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.normpath(os.path.join(script_dir, '..', '..', 'pmu_calibration', 'calibration_stats.csv'))
    calibration_stats = read_calibration_stats(csv_path)

    rtos_list = ['freertos', 'threadx', 'zephyr']
    summary = []

    for rtos in rtos_list:
        test_file = f"{rtos}_inheritance_test.txt"
        if not os.path.exists(test_file):
            continue
        calibration = calibration_stats.get(rtos, {'cycle':0.0,'icache':0.0,'dcache_access':0.0,'dcache_miss':0.0})

        total, measurements = parse_inheritance_file(test_file, calibration)
        averages = plot_inheritance_metrics(test_file, measurements, rtos.capitalize())
        summary.append({'rtos': rtos.capitalize(), 'file': test_file,
                        'total_inversions': total, **averages})
    # Write summary CSV
    keys = ["rtos","file","total_inversions","num_measurements",
            "cycle_min","cycle_robust","cycle_median","cycle_max",
            "icache_min","icache_robust","icache_median","icache_max",
            "dcache_access_min","dcache_access_robust","dcache_access_median","dcache_access_max",
            "dcache_miss_min","dcache_miss_robust","dcache_miss_median","dcache_miss_max"]
    with open('summary_inheritance.csv','w',newline='') as cf:
        w = csv.writer(cf)
        w.writerow(keys)
        for item in summary:
            w.writerow([item.get(k, '') for k in keys])
    # Generate plots
    plot_comparison_all_rtoses(summary)
    plot_cycle_jitter(summary)
    plot_cycle_count(summary)

if __name__ == '__main__':
    main()

