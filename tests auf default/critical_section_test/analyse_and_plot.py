import os
import re
import numpy as np
import matplotlib.pyplot as plt

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

def parse_calibration_file(filename):
    """
    Parse a calibration file and compute a reference overhead for each metric.
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
# Parsing overall Time Period Total from the test file
# -------------------------------

def parse_overall_performance(filename):
    """
    Parse the file to extract critical section Time Period Total data.
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
    Looks for lines starting with either "Profile Point:" or "Profile Entry:" then,
    in subsequent lines, matches "Cycle Count", "ICache Miss", "DCache Access", and "DCache Miss"
    (with or without "Count"). Calibration overhead is subtracted.
    Returns a list of dictionaries (one per profile block).
    """
    measurements = []
    current_measurement = None
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
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
    return measurements

# -------------------------------
# Plotting functions
# -------------------------------

def plot_overall_performance(rtos, rel_times, processing_times):
    """
    Plot critical section Time Period Total data (Time Period Total vs Relative Time) for one RTOS.
    Saves the plot as "plot/<rtos>_avg_period_total.png".
    """
    plt.figure(figsize=(8, 6))
    if len(rel_times) > 1:
        plt.plot(rel_times, processing_times, 'bo-', label="Time Period Total")
    else:
        plt.plot(rel_times, processing_times, 'bo', markersize=10, label="Time Period Total")
    plt.xlabel("Relative Time")
    plt.ylabel("Critical Section Time Period Total")
    plt.title(f"{rtos.capitalize()} - Critical Section Time Period Total")
    plt.legend()
    plt.grid(True)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, f"{rtos}_avg_period_total.png")
    plt.tight_layout()
    plt.savefig(outfile)
    plt.close()

def plot_pmu_metric(metric_label, values, rtos, base_filename):
    """
    Plot a PMU metric over profile points.
    Saves the plot as "plot/<base_filename>_<metric_label>.png".
    """
    indices = np.arange(1, len(values) + 1)
    plt.figure(figsize=(8, 6))
    plt.plot(indices, values, 'bo-', label=metric_label)
    plt.xlabel("Profile Point Index")
    plt.ylabel(f"Adjusted {metric_label}")
    plt.title(f"{rtos.capitalize()} - {metric_label} over Profile Points")
    plt.legend()
    plt.grid(True)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, f"{base_filename}_{metric_label.replace(' ', '_').lower()}.png")
    plt.tight_layout()
    plt.savefig(outfile)
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
    plt.savefig(outfile)
    plt.close()

def plot_overall_comparison(summary):
    """
    Generate a bar chart comparing the average critical section Time Period Total for all RTOSes.
    Saves the plot as "plot/avg_period_total_comparison.png".
    """
    rtoses = [item['rtos'] for item in summary]
    avg_processing = [item['avg_overall'] for item in summary]
    x = np.arange(len(rtoses))
    plt.figure(figsize=(8, 6))
    plt.bar(x, avg_processing, color='skyblue', edgecolor='black')
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Average Critical Section Time Period Total")
    plt.title("Critical Section Time Period Total Comparison")
    plt.grid(True, axis='y')
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    outfile = os.path.join(plot_dir, "avg_period_total_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile)
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
    plt.bar(x, jitter_totals, color='orange', edgecolor='black')
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
    plt.savefig(outfile1)
    plt.close()
    
    # Jitter Percentage Plot
    plt.figure(figsize=(8,6))
    plt.bar(x, jitter_pcts, color='purple', edgecolor='black')
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Jitter Percentage (%)")
    plt.title("Jitter Percentage Comparison")
    plt.grid(True, axis='y')
    outfile2 = os.path.join(plot_dir, "jitter_percentage_comparison.png")
    plt.tight_layout()
    plt.savefig(outfile2)
    plt.close()

# -------------------------------
# Main function
# -------------------------------

def main():
    # List of RTOS names (as in the file names)
    rtoses = ['freertos', 'threadx', 'zephyr']
    summary = []  # to collect overall performance stats for each RTOS
    
    for rtos in rtoses:
        test_file = f"{rtos}_critical_section_test.txt"
        cal_file = f"{rtos}_pmu_calibaration.txt"
        
        if not os.path.exists(test_file):
            continue
        
        if not os.path.exists(cal_file):
            calibration = {'cycle': 0.0, 'icache': 0.0, 'dcache_access': 0.0, 'dcache_miss': 0.0}
        else:
            calibration = parse_calibration_file(cal_file)
        
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
    
    # Write summary file in table form.
    summary_file = os.path.join("plot", "summary_critical_section.txt")
    with open(summary_file, "w") as f:
        header = ("RTOS\tAvg Total\tMin Total\tMax Total\tJitter Total\tJitter (%)\tData Points\n")
        f.write(header)
        for item in summary:
            line = (f"{item['rtos']}\t{item['avg_overall']:.2f}\t{item['min_overall']}\t{item['max_overall']}\t"
                    f"{item['jitter_total']}\t{item['jitter_pct']:.2f}\t{item['num_overall']}\n")
            f.write(line)

if __name__ == "__main__":
    main()
