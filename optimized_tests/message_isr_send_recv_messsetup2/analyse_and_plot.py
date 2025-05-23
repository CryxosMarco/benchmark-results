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

# Set working directory to script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

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

def read_calibration_stats(filename):
    """
    Reads calibration_stats.csv and returns a dict mapping lowercase RTOS names
    to their mean cycle-overheads.
    """
    stats = {}
    with open(filename, newline='') as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            rtos = row['RTOS'].lower()
            stats[rtos] = {
                'cycle': float(row['Mean_Overhead_Cycles']),
                'icache': 0.0,
                'dcache_access': 0.0,
                'dcache_miss': 0.0
            }
    return stats

# -------------------------------
# Benchmark parsing (combined send+receive)
# -------------------------------

def parse_benchmark_file(filename, calibration):
    """
    Parse a benchmark file with combined send+receive metrics.
    Subtract calibration overhead for each PMU measurement.
    Returns list of dicts with keys: cycle, icache, dcache_access, dcache_miss.
    """
    combined = []
    with open(filename, 'r') as f:
        curr = {}
        for line in f:
            line = line.strip()
            # Cycle Count
            m = re.match(r'Cycle Count(?: Count)?:\s+(\d+)', line)
            if m:
                val = max(float(m.group(1)) - calibration['cycle'], 0)
                curr['cycle'] = val
                continue
            # ICache
            m = re.match(r'ICache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                val = max(float(m.group(1)) - calibration['icache'], 0)
                curr['icache'] = val
                continue
            # DCache Access
            m = re.match(r'DCache Access(?: Count)?:\s+(\d+)', line)
            if m:
                val = max(float(m.group(1)) - calibration['dcache_access'], 0)
                curr['dcache_access'] = val
                continue
            # DCache Miss
            m = re.match(r'DCache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                val = max(float(m.group(1)) - calibration['dcache_miss'], 0)
                curr['dcache_miss'] = val
                combined.append(curr)
                curr = {}
                continue
    return combined

# -------------------------------
# Analysis
# -------------------------------

def analyze_file(filepath, calibration):
    """
    Analyze one benchmark file:
      - Compute robust average cycle count.
      - Determine min/max for each cache metric.
    """
    combined = parse_benchmark_file(filepath, calibration)
    cycles = [e['cycle'] for e in combined if 'cycle' in e]
    avg_cycle = round(robust_average(cycles), 2) if cycles else 0.0

    icache_values = [e['icache'] for e in combined if 'icache' in e]
    dcache_access_values = [e['dcache_access'] for e in combined if 'dcache_access' in e]
    dcache_miss_values = [e['dcache_miss'] for e in combined if 'dcache_miss' in e]

    stats = {
        'avg_cycle': avg_cycle,
        'icache_min': round(min(icache_values), 2) if icache_values else 0.0,
        'icache_max': round(max(icache_values), 2) if icache_values else 0.0,
        'dcache_access_min': round(min(dcache_access_values), 2) if dcache_access_values else 0.0,
        'dcache_access_max': round(max(dcache_access_values), 2) if dcache_access_values else 0.0,
        'dcache_miss_min': round(min(dcache_miss_values), 2) if dcache_miss_values else 0.0,
        'dcache_miss_max': round(max(dcache_miss_values), 2) if dcache_miss_values else 0.0,
        'combined_cycles': cycles
    }
    return stats

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
    plt.title(f"{rtos} {size*4} bytes send/received Cycle Count")
    plt.xlabel("Iteration")
    plt.ylabel("Normalized Cycle Count")
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
    plt.ylabel("Robust Average normalized Cycle Count")
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
            axs[i].set_ylabel("Normalized Value")
            axs[i].grid(True, axis='y')
        plt.tight_layout()
        plt.savefig(os.path.join("plot", f"cache_comparison_{size}.png"), dpi=300)
        plt.close()

def plot_stacked_cycle_counts_by_rtos(raw_cycles):
    """
    For each RTOS, plot calibration-corrected cycle counts over iterations
    as simple line traces—one line per message size—so hills and valleys show.
    raw_cycles: dict mapping message_size -> { RTOS: [cycles…], … }
    """

    # invert raw_cycles to group by RTOS
    cycles_by_rtos = {}
    for size, rtos_data in raw_cycles.items():
        for rtos, series in rtos_data.items():
            cycles_by_rtos.setdefault(rtos, {})[size] = series

    for rtos, size_dict in cycles_by_rtos.items():
        # find max length so all series share the same x-axis
        max_iters = max(len(series) for series in size_dict.values())
        x = np.arange(1, max_iters + 1)

        plt.figure(figsize=(10, 6))
        for size in sorted(size_dict):
            series = size_dict[size]
            padded = series + [np.nan] * (max_iters - len(series))  # np.nan for missing
            plt.plot(x, padded, marker='o', label=f"{size} bytes")

        plt.title(f"{rtos}: Cycle Counts by Message Size")
        plt.xlabel("Iteration")
        plt.ylabel("Calibration-corrected Cycle Count")
        plt.legend(title="Message Size", fontsize='small', loc='upper right')
        plt.grid(axis='both', linestyle='--', alpha=0.7)
        plt.tight_layout()
        os.makedirs('plot', exist_ok=True)
        plt.savefig(os.path.join('plot', f"lines_by_sizes_{rtos}.png"), dpi=300)
        plt.close()


# -------------------------------
# Main entry point
# -------------------------------

def main():
    # Load calibration stats
    csv_path = os.path.normpath(os.path.join(script_dir, '..', '..', 'pmu_calibration', 'calibration_stats.csv'))
    calibration_stats = read_calibration_stats(csv_path)

    summary = []
    raw_cycles = {} # { size: { RTOS: [cycle0, cycle1, ...], ... }, ... }

    for file in os.listdir('.'):
        m = re.match(r'(\d+)_([a-zA-Z]+)_isr_task_queue_test\.txt', file)
        if not m:
            continue
        size, rtos = int(m.group(1)), m.group(2).lower()
        cal = calibration_stats.get(rtos, {'cycle':0.0,'icache':0.0,'dcache_access':0.0,'dcache_miss':0.0})
        analysis = analyze_file(file, cal)
        # collect calibration-corrected cycle series
        msg_bytes = size * 4
        raw_cycles.setdefault(msg_bytes, {})[rtos.capitalize()] = analysis['combined_cycles']

        plot_cycle_counts(file, analysis, rtos.capitalize(), size)
        summary.append({
            'file': file,
            'rtos': rtos.capitalize(),
            'message_size_bytes': size*4,
            **{k:analysis[k] for k in ['avg_cycle','icache_min','icache_max','dcache_access_min','dcache_access_max','dcache_miss_min','dcache_miss_max']}
        })
    # Write CSV summary
    os.makedirs('plot', exist_ok=True)
    out_csv = os.path.join('plot','summary.csv')
    with open(out_csv,'w',newline='') as cf:
        w=csv.writer(cf)
        header=["File","RTOS","Message Size (bytes)","Average Cycle","ICache Min","ICache Max","DCache Access Min","DCache Access Max","DCache Miss Min","DCache Miss Max"]
        w.writerow(header)
        for it in summary:
            w.writerow([it['file'],it['rtos'],it['message_size_bytes'],f"{it['avg_cycle']:.2f}",f"{it['icache_min']:.2f}",f"{it['icache_max']:.2f}",f"{it['dcache_access_min']:.2f}",f"{it['dcache_access_max']:.2f}",f"{it['dcache_miss_min']:.2f}",f"{it['dcache_miss_max']:.2f}"])
    # Generate comparison plots
    plot_combined_average_cycle_counts(summary)
    plot_cache_comparison(summary)
    plot_stacked_cycle_counts_by_rtos(raw_cycles)
    print(f"Analysis complete. Summary at {out_csv} and plots in 'plot' folder.")

if __name__=='__main__':
    main()
