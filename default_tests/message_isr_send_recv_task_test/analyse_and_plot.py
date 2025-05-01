# Copyright (c) <2025> <Marco Milenkovic>
#
# This Code was generated with help of the ChatGPT and Github Copilot
# The Code was carefully reviewed and adjusted to work as intended
# The Code is used to analyse and plot the critical section test results
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of 
# this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation the 
# rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the Software 
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
# A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN 
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import re
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------
# Utility functions
# -------------------------------

def robust_average(values, trim_fraction=0.1):
    """
    Compute the average after trimming the top and bottom trim_fraction of values.
    This helps to remove spikes/outliers.
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

# -------------------------------
# Calibration parsing
# -------------------------------

def parse_calibration_file(filename):
    """
    Parse a calibration file and compute a reference (overhead) value for each metric.
    Accepts both "Metric:" and "Metric Count:" formats.
    """
    metrics = {'cycle': [], 'icache': [], 'dcache_access': [], 'dcache_miss': []}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            m = re.match(r'Cycle Count(?: Count)?:\s+(\d+)', line)
            if m:
                metrics['cycle'].append(float(m.group(1)))
                continue
            m = re.match(r'ICache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                metrics['icache'].append(float(m.group(1)))
                continue
            m = re.match(r'DCache Access(?: Count)?:\s+(\d+)', line)
            if m:
                metrics['dcache_access'].append(float(m.group(1)))
                continue
            m = re.match(r'DCache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                metrics['dcache_miss'].append(float(m.group(1)))
                continue

    cal = {}
    for key in metrics:
        if metrics[key]:
            cal[key] = round(robust_average(metrics[key]), 2)
        else:
            cal[key] = 0.0
    return cal

# -------------------------------
# Benchmark parsing (combined send+receive)
# -------------------------------

def parse_benchmark_file(filename, calibration):
    """
    Parse a benchmark file with combined send+receive metrics.
    Subtract calibration overhead for each PMU measurement.
    """
    combined = []
    with open(filename, 'r') as f:
        current_dict = {}
        for line in f:
            line = line.strip()

            m = re.match(r'Cycle Count(?: Count)?:\s+(\d+)', line)
            if m:
                value = float(m.group(1)) - calibration['cycle']
                value = max(value, 0)
                current_dict['cycle'] = value
                continue

            m = re.match(r'ICache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                value = float(m.group(1)) - calibration['icache']
                value = max(value, 0)
                current_dict['icache'] = value
                continue

            m = re.match(r'DCache Access(?: Count)?:\s+(\d+)', line)
            if m:
                value = float(m.group(1)) - calibration['dcache_access']
                value = max(value, 0)
                current_dict['dcache_access'] = value
                continue

            m = re.match(r'DCache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                value = float(m.group(1)) - calibration['dcache_miss']
                value = max(value, 0)
                current_dict['dcache_miss'] = value
                combined.append(current_dict)
                current_dict = {}
                continue

    return combined

# -------------------------------
# Analysis
# -------------------------------

def analyze_file(filepath, calibration):
    """
    Analyze one benchmark file:
      - Compute robust average cycle count (combined).
      - Determine the min and max values for each cache metric.
    """
    combined = parse_benchmark_file(filepath, calibration)
    cycles = [entry['cycle'] for entry in combined if 'cycle' in entry]
    avg_cycle = round(robust_average(cycles), 2) if cycles else 0.0

    icache_values = [entry['icache'] for entry in combined if 'icache' in entry]
    dcache_access_values = [entry['dcache_access'] for entry in combined if 'dcache_access' in entry]
    dcache_miss_values = [entry['dcache_miss'] for entry in combined if 'dcache_miss' in entry]

    icache_min = round(min(icache_values), 2) if icache_values else 0.0
    icache_max = round(max(icache_values), 2) if icache_values else 0.0
    dcache_access_min = round(min(dcache_access_values), 2) if dcache_access_values else 0.0
    dcache_access_max = round(max(dcache_access_values), 2) if dcache_access_values else 0.0
    dcache_miss_min = round(min(dcache_miss_values), 2) if dcache_miss_values else 0.0
    dcache_miss_max = round(max(dcache_miss_values), 2) if dcache_miss_values else 0.0

    return {
        'avg_cycle': avg_cycle,
        'icache_min': icache_min,
        'icache_max': icache_max,
        'dcache_access_min': dcache_access_min,
        'dcache_access_max': dcache_access_max,
        'dcache_miss_min': dcache_miss_min,
        'dcache_miss_max': dcache_miss_max,
        'combined_cycles': cycles
    }

# -------------------------------
# Plotting functions
# -------------------------------

def plot_cycle_counts(filename, analysis, rtos, size):
    """
    Create a cycle count plot for a benchmark file.
    Handles a single combined cycle count metric.
    """
    combined_cycles = analysis['combined_cycles']
    if len(combined_cycles) > 1:
        combined_cycles = combined_cycles[1:]
        iterations = list(range(2, len(analysis['combined_cycles']) + 1))
    else:
        iterations = list(range(1, len(combined_cycles) + 1))

    plt.figure(figsize=(10, 6))
    plt.plot(iterations, combined_cycles, marker='o', label='Combined Cycle')
    plt.title(f"{rtos} {size*4} bytes Combined Cycle Count")
    plt.xlabel("Iteration")
    plt.ylabel("Adjusted Cycle Count")
    plt.legend()
    plt.grid(True)

    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    base = os.path.basename(filename)
    plot_filename = os.path.join(plot_dir, base.replace("_isr_task_queue_test.txt", "_cycle.png"))
    plt.savefig(plot_filename, dpi=300)
    plt.close()

def plot_combined_average_cycle_counts(summary):
    """
    Create a single plot showing the average cycle counts for each RTOS
    across message sizes for better comparability.
    """
    rtos_groups = {}
    for item in summary:
        rtos = item['rtos']
        rtos_groups.setdefault(rtos, []).append((item['message_size_bytes'], item['avg_cycle']))

    plt.figure(figsize=(10, 6))
    for rtos, data in rtos_groups.items():
        data.sort()
        sizes = [d[0] for d in data]
        avg_cycles = [d[1] for d in data]
        plt.plot(sizes, avg_cycles, marker='o', label=rtos)

    plt.xlabel("Message Size (bytes)")
    plt.ylabel("Robust Average Adjusted Cycle Count")
    plt.title("Comparison of Robust Average Cycle Counts Among RTOS over Message Sizes")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plt.savefig(os.path.join(plot_dir, "combined_average_cycle_counts.png"), dpi=300)
    plt.close()

def plot_cache_comparison(summary):
    """
    For each message size bucket, create a grouped plot comparing the cache metrics
    (ICache Miss, DCache Access, DCache Miss) among the available RTOS.
    """
    size_groups = {}
    for item in summary:
        size = item['message_size_bytes']
        size_groups.setdefault(size, []).append(item)

    for size, items in size_groups.items():
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))
        metrics = ['ICache', 'DCache Access', 'DCache Miss']
        for i, metric in enumerate(metrics):
            rtos_names = []
            means = []
            errors = []
            for item in items:
                rtos_names.append(item['rtos'])
                if metric == 'ICache':
                    mean_val = (item['icache_min'] + item['icache_max']) / 2
                    err = (item['icache_max'] - item['icache_min']) / 2
                elif metric == 'DCache Access':
                    mean_val = (item['dcache_access_min'] + item['dcache_access_max']) / 2
                    err = (item['dcache_access_max'] - item['dcache_access_min']) / 2
                elif metric == 'DCache Miss':
                    mean_val = (item['dcache_miss_min'] + item['dcache_miss_max']) / 2
                    err = (item['dcache_miss_max'] - item['dcache_miss_min']) / 2
                means.append(mean_val)
                errors.append(err)
            x = np.arange(len(rtos_names))
            axs[i].bar(x, means, yerr=errors, capsize=5, edgecolor='black')
            axs[i].set_xticks(x)
            axs[i].set_xticklabels(rtos_names)
            axs[i].set_title(f"{metric} (Msg Size: {size} bytes)")
            axs[i].set_ylabel("Adjusted Value")
            axs[i].grid(True, axis='y')
        plt.tight_layout()
        plt.savefig(os.path.join("plot", f"cache_comparison_{size}.png"), dpi=300)
        plt.close()

# -------------------------------
# Main entry point
# -------------------------------

def main():
    """
    Main function to process calibration and benchmark files,
    perform analysis, generate plots, and write CSV summary.
    """
    rtos_list = ['freertos', 'threadx', 'zephyr']
    calibration_data = {}

    for rtos in rtos_list:
        cal_file = f"{rtos}_pmu_calibaration.txt"
        if os.path.exists(cal_file):
            calibration_data[rtos] = parse_calibration_file(cal_file)
            print(f"Calibration for {rtos}: {calibration_data[rtos]}")
        else:
            calibration_data[rtos] = {'cycle': 0.0, 'icache': 0.0, 'dcache_access': 0.0, 'dcache_miss': 0.0}

    summary = []

    for file in os.listdir('.'):
        m = re.match(r'(\d+)_([a-zA-Z]+)_isr_task_queue_test\.txt', file)
        if m:
            size = int(m.group(1))
            rtos = m.group(2).lower()
            if rtos not in calibration_data:
                continue
            cal = calibration_data[rtos]
            analysis = analyze_file(file, cal)
            plot_cycle_counts(file, analysis, rtos.capitalize(), size)
            summary.append({
                'file': file,
                'rtos': rtos.capitalize(),
                'message_size_bytes': size * 4,
                'avg_cycle': analysis['avg_cycle'],
                'icache_min': analysis['icache_min'],
                'icache_max': analysis['icache_max'],
                'dcache_access_min': analysis['dcache_access_min'],
                'dcache_access_max': analysis['dcache_access_max'],
                'dcache_miss_min': analysis['dcache_miss_min'],
                'dcache_miss_max': analysis['dcache_miss_max']
            })

    import csv
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    csv_filename = os.path.join(plot_dir, "summary.csv")
    with open(csv_filename, mode="w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        header = [
            "File", "RTOS", "Message Size (bytes)", "Average Cycle",
            "ICache Miss Min", "ICache Miss Max",
            "DCache Access Min", "DCache Access Max",
            "DCache Miss Min", "DCache Miss Max"
        ]
        csvwriter.writerow(header)
        for item in summary:
            row = [
                item["file"], item["rtos"], item["message_size_bytes"], f"{item['avg_cycle']:.2f}",
                f"{item['icache_min']:.2f}", f"{item['icache_max']:.2f}",
                f"{item['dcache_access_min']:.2f}", f"{item['dcache_access_max']:.2f}",
                f"{item['dcache_miss_min']:.2f}", f"{item['dcache_miss_max']:.2f}"
            ]
            csvwriter.writerow(row)

    # Generate comparison plots
    plot_combined_average_cycle_counts(summary)
    plot_cache_comparison(summary)

    print("Analysis complete. Summary written to summary.csv and plots saved in the 'plot' directory.")

if __name__ == "__main__":
    main()