import os
import re
import numpy as np
import matplotlib.pyplot as plt

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

def parse_calibration_file(filename):
    """
    Parse a calibration file and compute a robust average for each PMU metric.
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

# --------------------------------
# Inheritance Test File Parsing
# --------------------------------

def parse_inheritance_file(filename, calibration):
    """
    Parse an inheritance test file:
      - Extract the "Total inversion cycles completed" if present.
      - For each measurement block (marked by "Profile Point:" or "Profile Entry:"),
        extract the PMU metrics and subtract the corresponding calibration.
    Returns:
      (total_inversions, measurements)
      where measurements is a list of dicts with keys: 'cycle', 'icache', 'dcache_access', 'dcache_miss'.
    """
    measurements = []
    total_inversions = None
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Extract overall inversion cycles if available
    for line in lines:
        line = line.strip()
        m = re.match(r'Total inversion cycles completed:\s+(\d+)', line)
        if m:
            total_inversions = int(m.group(1))
            break

    current_measurement = None
    for line in lines:
        line = line.strip()
        # Accept both "Profile Point:" and "Profile Entry:" markers.
        if line.startswith("Profile Point:") or line.startswith("Profile Entry:"):
            if current_measurement is not None:
                measurements.append(current_measurement)
            current_measurement = {}
            continue
        if current_measurement is not None:
            m = re.match(r'Cycle Count(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['cycle']
                current_measurement['cycle'] = max(val, 0)
                continue
            m = re.match(r'ICache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['icache']
                current_measurement['icache'] = max(val, 0)
                continue
            m = re.match(r'DCache Access(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['dcache_access']
                current_measurement['dcache_access'] = max(val, 0)
                continue
            m = re.match(r'DCache Miss(?: Count)?:\s+(\d+)', line)
            if m:
                val = float(m.group(1)) - calibration['dcache_miss']
                current_measurement['dcache_miss'] = max(val, 0)
                continue
    if current_measurement is not None and current_measurement:
        measurements.append(current_measurement)
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
    plt.savefig(plot_filename)
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
    axs[0, 0].bar(x - bar_width, cycle_mins, width=bar_width, label='Min')
    axs[0, 0].bar(x, cycle_robusts, width=bar_width, label='Robust Avg')
    axs[0, 0].bar(x + bar_width, cycle_maxs, width=bar_width, label='Max')
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
    
    plt.tight_layout()
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plot_filename = os.path.join(plot_dir, "comparison_all_rtoses.png")
    plt.savefig(plot_filename)
    plt.close()

# --------------------------------
# Main Function
# --------------------------------

def main():
    # Test files: freertos_inheritance_test.txt, threadx_inheritance_test.txt, zephyr_inheritance_test.txt
    rtos_list = ['freertos', 'threadx', 'zephyr']
    summary = []

    for rtos in rtos_list:
        test_file = f"{rtos}_inheritance_test.txt"
        cal_file = f"{rtos}_pmu_calibaration.txt"
        if not os.path.exists(test_file):
            continue

        if os.path.exists(cal_file):
            calibration = parse_calibration_file(cal_file)
            print(f"Calibration for {rtos}: {calibration}")
        else:
            calibration = {'cycle': 0.0, 'icache': 0.0, 'dcache_access': 0.0, 'dcache_miss': 0.0}

        total_inversions, measurements = parse_inheritance_file(test_file, calibration)
        print(f"{rtos.capitalize()}: Parsed {len(measurements)} measurements. Total inversion cycles: {total_inversions}")
        averages = plot_inheritance_metrics(test_file, measurements, rtos.capitalize())
        summary.append({
            'rtos': rtos.capitalize(),
            'file': test_file,
            'total_inversions': total_inversions,
            'num_measurements': len(measurements),
            'cycle_robust': averages['cycle_robust'],
            'cycle_median': averages['cycle_median'],
            'cycle_min': averages['cycle_min'],
            'cycle_max': averages['cycle_max'],
            'icache_robust': averages['icache_robust'],
            'icache_median': averages['icache_median'],
            'icache_min': averages['icache_min'],
            'icache_max': averages['icache_max'],
            'dcache_access_robust': averages['dcache_access_robust'],
            'dcache_access_median': averages['dcache_access_median'],
            'dcache_access_min': averages['dcache_access_min'],
            'dcache_access_max': averages['dcache_access_max'],
            'dcache_miss_robust': averages['dcache_miss_robust'],
            'dcache_miss_median': averages['dcache_miss_median'],
            'dcache_miss_min': averages['dcache_miss_min'],
            'dcache_miss_max': averages['dcache_miss_max'],
        })

    # Write summary file.
    with open("summary_inheritance.txt", "w") as f:
        for item in summary:
            f.write(f"RTOS: {item['rtos']}\n")
            f.write(f"File: {item['file']}\n")
            f.write(f"Total Inversion Cycles: {item['total_inversions']}\n")
            f.write(f"Number of Measurements: {item['num_measurements']}\n")
            f.write(f"Cycle Count - Min: {item['cycle_min']:.2f}, Robust Avg: {item['cycle_robust']:.2f}, Median: {item['cycle_median']:.2f}, Max: {item['cycle_max']:.2f}\n")
            f.write(f"ICache Miss - Min: {item['icache_min']:.2f}, Robust Avg: {item['icache_robust']:.2f}, Median: {item['icache_median']:.2f}, Max: {item['icache_max']:.2f}\n")
            f.write(f"DCache Access - Min: {item['dcache_access_min']:.2f}, Robust Avg: {item['dcache_access_robust']:.2f}, Median: {item['dcache_access_median']:.2f}, Max: {item['dcache_access_max']:.2f}\n")
            f.write(f"DCache Miss - Min: {item['dcache_miss_min']:.2f}, Robust Avg: {item['dcache_miss_robust']:.2f}, Median: {item['dcache_miss_median']:.2f}, Max: {item['dcache_miss_max']:.2f}\n")
            f.write("-" * 40 + "\n")
    print("Inheritance analysis complete. Summary written to summary_inheritance.txt and all plots saved in the 'plot' directory.")

    # Generate the comparison plot for all RTOSes.
    plot_comparison_all_rtoses(summary)

if __name__ == "__main__":
    main()
