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

# -------------------------------
# Set working directory to script directory
# -------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# -------------------------------
# Utility functions
# -------------------------------

def robust_average(values, trim_fraction=0.1):
    """
    Compute the average after trimming the top and bottom trim_fraction of values.
    This helps to reduce the influence of outliers.
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

def compute_stats(values):
    """Return average, minimum, and maximum of a list of numbers."""
    if not values:
        return 0, 0, 0
    avg = np.mean(values)
    return avg, min(values), max(values)

# -------------------------------
# Calibration parsing
# -------------------------------

def read_calibration_stats(filename):
    """
    Reads calibration_stats.csv and returns a dict mapping lowercase RTOS names
    to their mean cycle‐overheads.
    """
    stats = {}
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rtos = row['RTOS'].lower()
            stats[rtos] = { 'cycle': float(row['Mean_Overhead_Cycles']),
                            'icache': 0.0,
                            'dcache_access': 0.0,
                            'dcache_miss': 0.0 }
    return stats

# -------------------------------
# Parsing overall Time Period Total from the test file
# -------------------------------

def parse_overall_performance(filename):
    """
    Parse the file to extract context switching Time Period Total data.
    It looks for lines containing "Relative Time:" and "Time Period Total:".
    Returns two lists:
      - relative_times: list of relative time markers
      - processing_times: corresponding "Time Period Total" values
    """
    relative_times = []
    processing_times = []
    current_rel = None
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if "Relative Time:" in line:
                m = re.search(r'Relative Time:\s*(\d+)', line)
                if m:
                    current_rel = int(m.group(1))
            if "Time Period Total:" in line:
                m = re.search(r'Time Period Total:\s*(\d+)', line)
                if m and current_rel is not None:
                    relative_times.append(current_rel)
                    processing_times.append(int(m.group(1)))
                    current_rel = None
    return relative_times, processing_times

# -------------------------------
# Parsing PMU metrics (per profile block)
# -------------------------------

def parse_pmu_metrics(filename, calibration):
    """
    Parse the file to extract PMU metrics from each profile block.
    Calibration overhead for cycles is subtracted based on calibration dict.
    Returns a list of dicts per profile block.
    """
    measurements = []
    current = None
    with open(filename, 'r') as f:
        for line in f:
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
    return measurements

# -------------------------------
# Plotting functions
# -------------------------------

def plot_overall_performance(rtos, rel_times, processing_times):
    """
    Plot context switching Time Period Total data (Time Period Total vs Relative Time) for one RTOS.
    Saves the plot as "plot/<rtos>_avg_period_total.png".
    """
    plt.figure(figsize=(8, 6))
    if len(rel_times) > 1:
        plt.plot(rel_times, processing_times, 'bo-', label="Time Period Total")
    else:
        plt.plot(rel_times, processing_times, 'bo', markersize=10, label="Time Period Total")
    plt.xlabel("Relative Time")
    plt.ylabel("Counter Value in Time Period")
    plt.title(f"{rtos.capitalize()} - Time Period Counter Values over Time")
    plt.legend()
    plt.grid(True)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, f"{rtos}_avg_period_total_over_time.png")
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()

def plot_pmu_metric(metric_label, values, rtos, base_filename):
    """
    Plot a PMU metric over profile points.
    Saves the plot as "plot/<base_filename>_<metric_label>.png".
    """
    indices = np.arange(1, len(values) + 1)
    plt.figure(figsize=(8, 6))
    plt.plot(indices, values, 'bo-', label=metric_label)
    plt.xlabel("Profile Index")
    plt.ylabel(f"Adjusted {metric_label}")
    plt.title(f"{rtos.capitalize()} - {metric_label} over Profile Points")
    plt.legend()
    plt.grid(True)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, f"{base_filename}_{metric_label.replace(' ', '_').lower()}.png")
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()

def plot_cache_metrics(rtos, base_filename, icache, dcache_access, dcache_miss):
    """
    Generate a single combined plot comparing cache metrics for one RTOS.
    Plots ICache Miss, DCache Access, and DCache Miss (adjusted values) versus profile point index.
    Saves the plot as "plot/<base_filename>_cache_comparison.png".
    """
    plt.figure(figsize=(8, 6))
    if icache:
        plt.plot(np.arange(1, len(icache)+1), icache, 'ro-', label="ICache Miss")
    if dcache_access:
        plt.plot(np.arange(1, len(dcache_access)+1), dcache_access, 'bo-', label="DCache Access")
    if dcache_miss:
        plt.plot(np.arange(1, len(dcache_miss)+1), dcache_miss, 'go-', label="DCache Miss")
    plt.xlabel("Profile Point Index")
    plt.ylabel("Adjusted Cache Metric")
    plt.title(f"{rtos.capitalize()} - Combined Cache Metrics")
    plt.legend()
    plt.grid(True)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, f"{base_filename}_cache_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()

def plot_overall_comparison(summary):
    """
    Generate a bar chart comparing the average context switching Time Period Total for all RTOSes.
    Saves the plot as "plot/avg_period_total_comparison.png".
    """
    rtoses = [item['rtos'] for item in summary]
    avg_processing = [item['avg_overall'] for item in summary]
    x = np.arange(len(rtoses))
    plt.figure(figsize=(8, 6))
    bars = plt.bar(x, avg_processing, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
    # Add text annotations above the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', ha='center', va='bottom')
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Average Counter Value")
    plt.title("Comparison of Context Switching Counter Averages over Time Period Total ")
    plt.grid(True, axis='y')
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, "avg_period_total_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()

def plot_overall_jitter_comparison(summary):
    """
    Generate separate bar charts for jitter total and jitter percentage across RTOSes.
    Saves the plots as "plot/jitter_total_comparison.png" and "plot/jitter_percentage_comparison.png".
    """
    rtoses = [item['rtos'] for item in summary]
    jitter_totals = [item['jitter_total'] for item in summary]
    jitter_pcts = [item['jitter_pct'] for item in summary]
    x = np.arange(len(rtoses))
    
    # Jitter Total Plot
    plt.figure(figsize=(8,6))
    plt.bar(x, jitter_totals, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Jitter Total")
    plt.title("Jitter Total Comparison")
    plt.grid(True, axis='y')
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile1 = os.path.join(plot_dir, "jitter_total_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile1, dpi=300)
    plt.close()
    
    # Jitter Percentage Plot
    plt.figure(figsize=(8,6))
    plt.bar(x, jitter_pcts, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Jitter Percentage (%)")
    plt.title("Jitter Percentage Comparison")
    plt.grid(True, axis='y')
    outfile2 = os.path.join(plot_dir, "jitter_percentage_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile2, dpi=300)
    plt.close()

def plot_avg_cycle_comparison(summary):
    """
    Plot average cycle count comparison between RTOSes using PMU data.
    Saves the plot as 'plot/avg_cycle_count_comparison.png'.
    """
    rtoses = [item['rtos'] for item in summary]
    avg_cycles = [item.get('avg_cycles', 0.0) for item in summary]

    x = np.arange(len(rtoses))
    plt.figure(figsize=(8, 6))
    bars = plt.bar(x, avg_cycles, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
    # Add text annotations above the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.1f}', ha='center', va='bottom')
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Average Cycle Count (PMU-adjusted)")
    plt.title("Average Cycle Count Comparison Between RTOSes")
    plt.grid(True, axis='y')
    
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, "avg_cycle_count_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()

def plot_cycle_counts_over_time(summary_all_cycles):
    """
    Create one plot per RTOS showing cycle counts over time using consistent color coding.
    Saves plots to 'plot/<rtos>_cycle_counts_over_time.png'
    """
    color_map = {
        'freertos': 'steelblue',
        'threadx': 'forestgreen',
        'zephyr': 'darkorange'
    }

    plot_dir = "plot"
    os.makedirs(plot_dir, exist_ok=True)

    for rtos, cycles in summary_all_cycles.items():
        if not cycles:
            continue

        indices = np.arange(1, len(cycles) + 1)
        plt.figure(figsize=(8, 6))
        plt.plot(indices, cycles, marker='o', color=color_map.get(rtos, 'gray'), label=rtos.capitalize())
        plt.xlabel("Profile Index")
        plt.ylabel("Cycle Count (adjusted)")
        plt.title(f"{rtos.capitalize()} - Cycle Count over Time")
        plt.grid(True)
        plt.legend()

        outfile = os.path.join(plot_dir, f"{rtos}_cycle_counts_over_time.png")
        plt.tight_layout()
        plt.savefig(outfile, dpi=300)
        plt.close()



# -------------------------------
# Main function
# -------------------------------

def main():
    # List of RTOS names (as in the file names)
    rtoses = ['freertos', 'threadx', 'zephyr']
    summary = []  # to collect overall performance stats for each RTOS
    summary_all_cycles = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # build the path to the CSV in pmu_calibration folder:
    csv_path = os.path.join(script_dir, '..', '..', 'pmu_calibration', 'calibration_stats.csv')
    csv_path = os.path.normpath(csv_path) 
    calibration_stats = read_calibration_stats(csv_path)
    
    for rtos in rtoses:
        test_file = f"{rtos}_context_switching_test.txt"
        calibration = calibration_stats.get(rtos, 
                  {'cycle':0.0,'icache':0.0,'dcache_access':0.0,'dcache_miss':0.0})
        
        # Parse overall Time Period Total data.
        rel_times, processing_times = parse_overall_performance(test_file)
        if not processing_times:
            continue
        
        avg_overall, min_overall, max_overall = compute_stats(processing_times)
        # Compute jitter metrics for overall performance.
        jitter_total = max_overall - min_overall
        jitter_pct = (jitter_total / avg_overall * 100) if avg_overall else 0
        
        summary.append({
            'rtos': rtos.capitalize(),
            'avg_overall': avg_overall,
            'min_overall': min_overall,
            'max_overall': max_overall,
            'jitter_total': jitter_total,
            'jitter_pct': jitter_pct,
            'num_overall': len(processing_times)
        })
        
        # Plot overall Time Period Total.
        plot_overall_performance(rtos, rel_times, processing_times)
        
        # Parse PMU metrics from profile blocks.
        pmu_measurements = parse_pmu_metrics(test_file, calibration)
        base_filename = os.path.splitext(os.path.basename(test_file))[0]
        if pmu_measurements:
            cycles = [m.get('cycle', 0) for m in pmu_measurements]
            summary_all_cycles[rtos] = cycles
            avg_cycles = round(robust_average(cycles), 2) if cycles else 0.0
            summary[-1]['avg_cycles'] = avg_cycles
            icache = [m.get('icache', 0) for m in pmu_measurements]
            dcache_access = [m.get('dcache_access', 0) for m in pmu_measurements]
            dcache_miss = [m.get('dcache_miss', 0) for m in pmu_measurements]
            
            if cycles:
                plot_pmu_metric("Cycle Count", cycles, rtos, base_filename)
                
            if icache or dcache_access or dcache_miss:
                plot_cache_metrics(rtos, base_filename, icache, dcache_access, dcache_miss)
    
    # Generate overall Time Period Total comparison bar chart.
    if summary:
        plot_overall_comparison(summary)
        plot_overall_jitter_comparison(summary)
        plot_avg_cycle_comparison(summary)
        plot_cycle_counts_over_time(summary_all_cycles)

    
    # Define the output CSV file path
    summary_file = os.path.join("plot", "summary_context_switching.csv")

    with open(summary_file, mode='w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # Write the header row with PMU values and calibration
        header = [
            "RTOS", "Avg Total", "Min Total", "Max Total", "Jitter Total", "Jitter (%)", "Data Points",
            "Avg Cycle Count"
        ]
        csvwriter.writerow(header)
        
        for item in summary:
            calib = item.get('calibration', {'cycle': 0, 'icache': 0, 'dcache_access': 0, 'dcache_miss': 0})
            row = [
                item['rtos'],
                f"{item['avg_overall']:.2f}",
                item['min_overall'],
                item['max_overall'],
                item['jitter_total'],
                f"{item['jitter_pct']:.2f}",
                item['num_overall'],
                f"{item.get('avg_cycles', 0):.2f}"
            ]
            csvwriter.writerow(row)


if __name__ == "__main__":
    main()
