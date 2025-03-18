import os
import re
import numpy as np
import matplotlib.pyplot as plt

# ---------- Parsing Functions ----------

def parse_sync_file(filename):
    """
    Parse a task synchronisation log file.
    Returns a list of dictionaries, one per measurement block.
    Each block is assumed to start with "**** Task Synchronistation Test ****".
    """
    with open(filename, 'r') as f:
        content = f.read()
    
    # Split into blocks based on the marker.
    blocks = re.split(r'\*{4}\s*Task Synchronistation Test\s*\*{4}', content)
    measurements = []
    for block in blocks[1:]:
        # Extract relative time
        rt_match = re.search(r"Relative Time:\s*(\d+)", block)
        relative_time = int(rt_match.group(1)) if rt_match else None
        
        # Extract time period total
        tpt_match = re.search(r"Time Period Total:\s*(\d+)", block)
        time_period_total = int(tpt_match.group(1)) if tpt_match else None
        
        # Extract task counters
        t1_match = re.search(r"Task1 Counter:\s*(\d+)", block)
        task1 = int(t1_match.group(1)) if t1_match else None
        t2_match = re.search(r"Task2 Counter:\s*(\d+)", block)
        task2 = int(t2_match.group(1)) if t2_match else None
        
        # Optionally, extract provided average time per iteration
        avg_iter_match = re.search(r"Average Time per Iteration:\s*([\d\.]+)\s*us", block)
        avg_iter = float(avg_iter_match.group(1)) if avg_iter_match else None
        
        # Extract PMU metrics (handles "Profile Point:" or "Profile Entry:" formats)
        cycle_match = re.search(r"Cycle Count:\s*(\d+)", block)
        cycle_count = int(cycle_match.group(1)) if cycle_match else None
        
        icache_match = re.search(r"ICache Miss(?: Count)?:\s*(\d+)", block)
        icache_miss = int(icache_match.group(1)) if icache_match else None
        
        dcache_access_match = re.search(r"DCache Access(?: Count)?:\s*(\d+)", block)
        dcache_access = int(dcache_access_match.group(1)) if dcache_access_match else None
        
        dcache_miss_match = re.search(r"DCache Miss(?: Count)?:\s*(\d+)", block)
        dcache_miss = int(dcache_miss_match.group(1)) if dcache_miss_match else None
        
        measurements.append({
            'relative_time': relative_time,
            'time_period_total': time_period_total,
            'task1_counter': task1,
            'task2_counter': task2,
            'avg_time_iteration': avg_iter,
            'cycle_count': cycle_count,
            'icache_miss': icache_miss,
            'dcache_access': dcache_access,
            'dcache_miss': dcache_miss,
        })
    return measurements

def parse_calibration_file(filename):
    """
    Parse a calibration log file.
    Returns a list of dictionaries – one per calibration block.
    Each block is assumed to follow a "[Main] Starting PMU calibration Test." marker.
    """
    with open(filename, 'r') as f:
        content = f.read()
    
    blocks = re.split(r"\[Main\]\s+Starting PMU calibration Test\.", content)
    calibrations = []
    for block in blocks[1:]:
        cycle_match = re.search(r"Cycle Count:\s*(\d+)", block)
        cycle_count = int(cycle_match.group(1)) if cycle_match else None
        
        icache_match = re.search(r"ICache Miss(?: Count)?:\s*(\d+)", block)
        icache_miss = int(icache_match.group(1)) if icache_match else None
        
        dcache_access_match = re.search(r"DCache Access(?: Count)?:\s*(\d+)", block)
        dcache_access = int(dcache_access_match.group(1)) if dcache_access_match else None
        
        dcache_miss_match = re.search(r"DCache Miss(?: Count)?:\s*(\d+)", block)
        dcache_miss = int(dcache_miss_match.group(1)) if dcache_miss_match else None
        
        calibrations.append({
            'cycle_count': cycle_count,
            'icache_miss': icache_miss,
            'dcache_access': dcache_access,
            'dcache_miss': dcache_miss,
        })
    return calibrations

# ---------- Statistical Functions ----------

def robust_average(values):
    """Compute the robust average (median) of a list of numbers."""
    arr = np.array(values)
    return np.median(arr)

def summary_stats(values):
    """
    Compute summary statistics for a list/array of values.
    Returns min, max, jitter (max-min), and robust average.
    """
    return {
        'min': np.min(values),
        'max': np.max(values),
        'jitter': np.max(values) - np.min(values),
        'robust_avg': np.median(values)
    }

# ---------- Main Processing & Plotting ----------

def main():
    # RTOS names and file names (as in your tree)
    rtoses = ['freertos', 'zephyr', 'threadx']
    sync_data = {}
    calib_data = {}
    
    for rtos in rtoses:
        sync_file = f"{rtos}_task_sync.txt"
        calib_file = f"{rtos}_pmu_calibaration.txt"
        if os.path.exists(sync_file):
            sync_data[rtos] = parse_sync_file(sync_file)
        else:
            sync_data[rtos] = []
        if os.path.exists(calib_file):
            calib_data[rtos] = parse_calibration_file(calib_file)
        else:
            calib_data[rtos] = []
    
    # Compute robust calibration averages for each RTOS
    calib_averages = {}
    for rtos in rtoses:
        calibs = calib_data[rtos]
        if calibs:
            cycle_vals = [c['cycle_count'] for c in calibs if c['cycle_count'] is not None]
            icache_vals = [c['icache_miss'] for c in calibs if c['icache_miss'] is not None]
            dcache_access_vals = [c['dcache_access'] for c in calibs if c['dcache_access'] is not None]
            dcache_miss_vals = [c['dcache_miss'] for c in calibs if c['dcache_miss'] is not None]
            calib_averages[rtos] = {
                'cycle_count': robust_average(cycle_vals) if cycle_vals else None,
                'icache_miss': robust_average(icache_vals) if icache_vals else None,
                'dcache_access': robust_average(dcache_access_vals) if dcache_access_vals else None,
                'dcache_miss': robust_average(dcache_miss_vals) if dcache_miss_vals else None,
            }
        else:
            calib_averages[rtos] = {
                'cycle_count': None,
                'icache_miss': None,
                'dcache_access': None,
                'dcache_miss': None
            }
    
    # Process sync test measurements and subtract calibration averages
    processed_data = {}
    summary = {}
    time_iteration_calc = {}
    
    for rtos in rtoses:
        data = sync_data[rtos]
        if not data:
            continue
        
        # Collect lists for each metric
        rel_times = []
        tpt_list = []
        cycle_list = []
        icache_list = []
        dcache_access_list = []
        dcache_miss_list = []
        avg_iter_list = []  # if provided in the log
        
        for d in data:
            rel_times.append(d['relative_time'])
            if d['time_period_total'] is not None:
                tpt_list.append(d['time_period_total'])
            if d['cycle_count'] is not None:
                cycle_list.append(d['cycle_count'])
            if d['icache_miss'] is not None:
                icache_list.append(d['icache_miss'])
            if d['dcache_access'] is not None:
                dcache_access_list.append(d['dcache_access'])
            if d['dcache_miss'] is not None:
                dcache_miss_list.append(d['dcache_miss'])
            if d['avg_time_iteration'] is not None:
                avg_iter_list.append(d['avg_time_iteration'])
        
        # Subtract calibration robust averages to get corrected PMU values.
        cal = calib_averages[rtos]
        corrected_cycle = [x - cal['cycle_count'] if cal['cycle_count'] is not None else x for x in cycle_list]
        corrected_icache = [x - cal['icache_miss'] if cal['icache_miss'] is not None else x for x in icache_list]
        corrected_dcache_access = [x - cal['dcache_access'] if cal['dcache_access'] is not None else x for x in dcache_access_list]
        corrected_dcache_miss = [x - cal['dcache_miss'] if cal['dcache_miss'] is not None else x for x in dcache_miss_list]
        
        processed_data[rtos] = {
            'relative_time': rel_times,
            'time_period_total': tpt_list,
            'cycle_count': cycle_list,
            'icache_miss': icache_list,
            'dcache_access': dcache_access_list,
            'dcache_miss': dcache_miss_list,
            'corrected_cycle_count': corrected_cycle,
            'corrected_icache_miss': corrected_icache,
            'corrected_dcache_access': corrected_dcache_access,
            'corrected_dcache_miss': corrected_dcache_miss,
            'avg_iteration_provided': avg_iter_list,
        }
        
        # Compute summary statistics for raw and corrected metrics
        summary[rtos] = {
            'time_period_total': summary_stats(np.array(tpt_list)),
            'cycle_count': summary_stats(np.array(cycle_list)),
            'icache_miss': summary_stats(np.array(icache_list)),
            'dcache_access': summary_stats(np.array(dcache_access_list)),
            'dcache_miss': summary_stats(np.array(dcache_miss_list)),
            'corrected_cycle_count': summary_stats(np.array(corrected_cycle)),
            'corrected_icache_miss': summary_stats(np.array(corrected_icache)),
            'corrected_dcache_access': summary_stats(np.array(corrected_dcache_access)),
            'corrected_dcache_miss': summary_stats(np.array(corrected_dcache_miss)),
        }
        
        # Calculate robust average of time_period_total and derive time per iteration.
        # (Assuming the test runs for 30 seconds which equals 30,000,000 microseconds)
        robust_tpt = robust_average(tpt_list)
        time_per_iter_us = 30000000.0 / robust_tpt if robust_tpt else None
        time_iteration_calc[rtos] = time_per_iter_us
    
    # ---------- Plotting ----------
    
    # Create one plot per raw PMU metric (Cycle Count, ICache Miss, DCache Access, DCache Miss)
    metrics = ['cycle_count', 'icache_miss', 'dcache_access', 'dcache_miss']
    for metric in metrics:
        plt.figure()
        for rtos in rtoses:
            if rtos in processed_data:
                x = processed_data[rtos]['relative_time']
                y = processed_data[rtos][metric]
                plt.plot(x, y, marker='o', label=rtos)
        plt.xlabel('Relative Time (s)')
        plt.ylabel(metric.replace('_', ' ').title())
        plt.title(f"{metric.replace('_', ' ').title()} over Time")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join("plots", f"{metric}_over_time.png"))
        plt.close()
    
    # Plot corrected PMU metrics
    for metric in metrics:
        plt.figure()
        # Define mapping: for "cycle_count", use "corrected_cycle_count"; for others, "corrected_" + metric.
        if metric == 'cycle_count':
            key = 'corrected_cycle_count'
        elif metric == 'icache_miss':
            key = 'corrected_icache_miss'
        elif metric == 'dcache_access':
            key = 'corrected_dcache_access'
        elif metric == 'dcache_miss':
            key = 'corrected_dcache_miss'
        for rtos in rtoses:
            if rtos in processed_data:
                x = processed_data[rtos]['relative_time']
                y = processed_data[rtos][key]
                plt.plot(x, y, marker='o', label=rtos)
        plt.xlabel('Relative Time (s)')
        plt.ylabel(f"Corrected {metric.replace('_', ' ').title()}")
        plt.title(f"Corrected {metric.replace('_', ' ').title()} over Time")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join("plots", f"corrected_{metric}_over_time.png"))
        plt.close()
    
    # ---------- Output Summary ----------
    
    # Write summary into a text file formatted as tables
    with open("summary.txt", "w") as f:
        for rtos in rtoses:
            if rtos not in summary:
                continue
            f.write(f"Summary for {rtos}:\n")
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            f.write("| Metric                    | Min           | Max           | Jitter        | Robust Avg     |\n")
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            for metric, stats in summary[rtos].items():
                # Format each value as a number (stripping numpy type info)
                min_val = float(stats['min']) if isinstance(stats['min'], (np.int64, np.float64)) else stats['min']
                max_val = float(stats['max']) if isinstance(stats['max'], (np.int64, np.float64)) else stats['max']
                jitter = float(stats['jitter']) if isinstance(stats['jitter'], (np.int64, np.float64)) else stats['jitter']
                robust_avg = float(stats['robust_avg']) if isinstance(stats['robust_avg'], (np.int64, np.float64)) else stats['robust_avg']
                f.write("| {:25} | {:13} | {:13} | {:13} | {:14} |\n".format(
                    metric, min_val, max_val, jitter, robust_avg))
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            f.write(f"Calculated robust time per iteration (us): {time_iteration_calc[rtos]}\n")
            f.write("\n\n")
    
    # ---------- Bar Plots for Robust Averages ----------
    
    # Bar plot for robust average cycle count and time period total
    rtos_list = []
    robust_cycle = []
    robust_time_total = []
    for rtos in rtoses:
        if rtos in summary:
            rtos_list.append(rtos)
            robust_cycle.append(summary[rtos]['cycle_count']['robust_avg'])
            robust_time_total.append(summary[rtos]['time_period_total']['robust_avg'])
    
    # Get the default color cycle for the bars
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color'][:len(rtos_list)]
    
    # Bar plot for robust average cycle count
    plt.figure()
    plt.bar(rtos_list, robust_cycle, color=colors)
    plt.xlabel("RTOS")
    plt.ylabel("Robust Average Cycle Count")
    plt.title("Robust Average Cycle Count Comparison")
    plt.savefig(os.path.join("plots", "robust_avg_cycle_count.png"))
    plt.close()
    
    # Bar plot for robust average time period total
    plt.figure()
    plt.bar(rtos_list, robust_time_total, color=colors)
    plt.xlabel("RTOS")
    plt.ylabel("Robust Average Time Period Total")
    plt.title("Robust Average Time Period Total Comparison")
    plt.savefig(os.path.join("plots", "robust_avg_time_period_total.png"))
    plt.close()
    
if __name__ == "__main__":
    main()
