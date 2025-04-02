# Copyright (c) <2025> <Marco Milenkovic>
#
# This Code was generated with help of the ChatGPT and Github Copilot
# The Code was carfeully reviewed and adjusted to work as intended
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

# ---------- Parsing Functions ----------

def parse_sync_file(filename):
    """
    Parse a task synchronisation log file.
    Each block starts with "**** Task Synchronistation Test ****" and contains:
      - Header info (Relative Time, Time Period Total, Task Counters, etc.)
      - One or more PMU measurement sections starting with "Profile Point:" or "Profile Entry:".
    For each profile section a separate measurement dictionary is created.
    """
    with open(filename, 'r') as f:
        content = f.read()

    # Split the content into blocks by the test marker.
    blocks = re.split(r'\*{4}\s*Task Synchronistation Test\s*\*{4}', content)
    measurements = []
    for block in blocks[1:]:
        # Extract header information once per block.
        rt_match = re.search(r"Relative Time:\s*(\d+)", block)
        relative_time = int(rt_match.group(1)) if rt_match else np.nan

        tpt_match = re.search(r"Time Period Total:\s*(\d+)", block)
        time_period_total = int(tpt_match.group(1)) if tpt_match else np.nan

        t1_match = re.search(r"Task1 Counter:\s*(\d+)", block)
        task1 = int(t1_match.group(1)) if t1_match else np.nan

        t2_match = re.search(r"Task2 Counter:\s*(\d+)", block)
        task2 = int(t2_match.group(1)) if t2_match else np.nan

        avg_iter_match = re.search(r"Average Time per Iteration:\s*([\d\.]+)\s*us", block)
        avg_iter = float(avg_iter_match.group(1)) if avg_iter_match else np.nan

        # Split the block into profile sections.
        sections = re.split(r"Profile (?:Point|Entry):", block)
        for section in sections[1:]:
            cycle_match = re.search(r"Cycle Count:\s*(\d+)", section)
            cycle_val = int(cycle_match.group(1)) if cycle_match else np.nan

            icache_match = re.search(r"ICache Miss(?: Count)?:\s*(\d+)", section)
            icache_val = int(icache_match.group(1)) if icache_match else np.nan

            dcache_access_match = re.search(r"DCache Access(?: Count)?:\s*(\d+)", section)
            dcache_access_val = int(dcache_access_match.group(1)) if dcache_access_match else np.nan

            dcache_miss_match = re.search(r"DCache Miss(?: Count)?:\s*(\d+)", section)
            dcache_miss_val = int(dcache_miss_match.group(1)) if dcache_miss_match else np.nan

            measurement = {
                'relative_time': relative_time,
                'time_period_total': time_period_total,
                'task1_counter': task1,
                'task2_counter': task2,
                'avg_time_iteration': avg_iter,
                'cycle_count': cycle_val,
                'icache_miss': icache_val,
                'dcache_access': dcache_access_val,
                'dcache_miss': dcache_miss_val,
            }
            measurements.append(measurement)
    return measurements

def parse_calibration_file(filename):
    """
    Parse a calibration log file.
    Each calibration block (starting with a marker like "[Main] Starting PMU calibration Test.")
    is split into profile sections (Profile Point: or Profile Entry:) and each section produces a measurement.
    """
    with open(filename, 'r') as f:
        content = f.read()

    blocks = re.split(r"\[Main\]\s+Starting PMU calibration Test\.", content)
    calibrations = []
    for block in blocks[1:]:
        sections = re.split(r"Profile (?:Point|Entry):", block)
        for section in sections[1:]:
            cycle_match = re.search(r"Cycle Count:\s*(\d+)", section)
            cycle_val = int(cycle_match.group(1)) if cycle_match else np.nan

            icache_match = re.search(r"ICache Miss(?: Count)?:\s*(\d+)", section)
            icache_val = int(icache_match.group(1)) if icache_match else np.nan

            dcache_access_match = re.search(r"DCache Access(?: Count)?:\s*(\d+)", section)
            dcache_access_val = int(dcache_access_match.group(1)) if dcache_access_match else np.nan

            dcache_miss_match = re.search(r"DCache Miss(?: Count)?:\s*(\d+)", section)
            dcache_miss_val = int(dcache_miss_match.group(1)) if dcache_miss_match else np.nan

            calibration = {
                'cycle_count': cycle_val,
                'icache_miss': icache_val,
                'dcache_access': dcache_access_val,
                'dcache_miss': dcache_miss_val,
            }
            calibrations.append(calibration)
    return calibrations

# ---------- Statistical Functions ----------

def robust_average(values):
    """Compute the robust (median) average of a list of numbers, ignoring NaNs."""
    arr = np.array(values, dtype=float)
    return np.nanmedian(arr)

def summary_stats(values):
    """
    Compute summary statistics for a list/array of values.
    Returns a dictionary with keys: 'min', 'max', 'jitter', and 'robust_avg'.
    Uses nan-aware functions.
    """
    arr = np.array(values, dtype=float)
    if arr.size == 0 or np.isnan(arr).all():
        return {'min': np.nan, 'max': np.nan, 'jitter': np.nan, 'robust_avg': np.nan}
    return {
        'min': np.nanmin(arr),
        'max': np.nanmax(arr),
        'jitter': np.nanmax(arr) - np.nanmin(arr),
        'robust_avg': np.nanmedian(arr)
    }

def compute_summary(measurements, metric_keys):
    """
    Given a list of measurement dictionaries and the metric keys,
    returns a dictionary of summary statistics (for each metric) over all measurements.
    """
    summary = {}
    for key in metric_keys:
        values = [m[key] for m in measurements if not np.isnan(m[key])]
        summary[key] = summary_stats(values)
    return summary

def compute_corrected_summary(raw_summary, calib_avgs):
    """
    Compute corrected summary statistics by subtracting the calibration average
    from the raw summary statistics.
    For min and max: corrected = raw - calib; jitter remains unchanged.
    """
    corrected = {}
    for key in raw_summary:
        raw_stat = raw_summary[key]
        calib_val = calib_avgs.get(key, np.nan)
        if not np.isnan(calib_val):
            corrected[key] = {
                'min': raw_stat['min'] - calib_val if not np.isnan(raw_stat['min']) else np.nan,
                'max': raw_stat['max'] - calib_val if not np.isnan(raw_stat['max']) else np.nan,
                'jitter': raw_stat['jitter'],
                'robust_avg': raw_stat['robust_avg'] - calib_val if not np.isnan(raw_stat['robust_avg']) else np.nan
            }
        else:
            corrected[key] = raw_stat
    return corrected

# ---------- Main Workflow ----------

def main():
    rtoses = ['freertos', 'zephyr', 'threadx']
    metric_keys = ['time_period_total', 'cycle_count', 'icache_miss', 'dcache_access', 'dcache_miss']

    # 1. Parse all Calibration Data.
    calib_data = {}
    for rtos in rtoses:
        calib_file = f"{rtos}_pmu_calibaration.txt"
        calib_data[rtos] = parse_calibration_file(calib_file) if os.path.exists(calib_file) else []
    
    # 2. Parse all Raw Test Data.
    raw_data = {}
    for rtos in rtoses:
        raw_file = f"{rtos}_task_sync.txt"
        raw_data[rtos] = parse_sync_file(raw_file) if os.path.exists(raw_file) else []

    # 3. Compute Robust Calibration Averages for Each RTOS.
    calib_averages = {}
    for rtos in rtoses:
        calibs = calib_data[rtos]
        if calibs:
            calib_averages[rtos] = {}
            for key in ['cycle_count', 'icache_miss', 'dcache_access', 'dcache_miss']:
                values = [m[key] for m in calibs if not np.isnan(m[key])]
                calib_averages[rtos][key] = robust_average(values) if values else np.nan
        else:
            calib_averages[rtos] = {key: np.nan for key in ['cycle_count', 'icache_miss', 'dcache_access', 'dcache_miss']}

    # 4. Compute Raw Summary Statistics for Each RTOS.
    raw_summary = {}
    time_iteration_calc = {}
    for rtos in rtoses:
        if raw_data[rtos]:
            raw_summary[rtos] = compute_summary(raw_data[rtos], metric_keys)
        else:
            raw_summary[rtos] = {key: {'min': np.nan, 'max': np.nan, 'jitter': np.nan, 'robust_avg': np.nan} for key in metric_keys}
        # Calculate robust average of time_period_total and derive time per iteration.
        # (Assuming the test runs for 30 seconds which equals 30,000,000 microseconds)
        
        time_per_iter_us = 30000000.0 / raw_summary[rtos]['time_period_total']['robust_avg'] if not np.isnan(raw_summary[rtos]['time_period_total']['robust_avg']) else np.nan
        time_iteration_calc[rtos] = time_per_iter_us

    # 5. Compute Corrected Summary Statistics.
    # For each metric, subtract the calibration robust average from the raw robust average (and min/max).
    corrected_summary = {}
    for rtos in rtoses:
        # Create a dictionary of calibration averages for the relevant metrics.
        calib_avgs = {}
        for key in ['cycle_count', 'icache_miss', 'dcache_access', 'dcache_miss']:
            calib_avgs[key] = calib_averages[rtos].get(key, np.nan)
        # For time_period_total we do not subtract anything (or could be left raw).
        calib_avgs['time_period_total'] = 0  
        corrected_summary[rtos] = compute_corrected_summary(raw_summary[rtos], calib_avgs)

    # 6. Output Summary and Create Plots.
    # Write summary.txt including both raw and corrected statistics.
    with open("summary.txt", "w") as f:
        for rtos in rtoses:
            f.write(f"Summary for {rtos} (RAW Data):\n")
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            f.write("| Metric                    | Min           | Max           | Jitter        | Robust Avg     |\n")
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            for key in metric_keys:
                stat = raw_summary[rtos][key]
                f.write("| {:25} | {:13} | {:13} | {:13} | {:14} |\n".format(key, stat['min'], stat['max'], stat['jitter'], stat['robust_avg']))
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n\n")
            
            f.write(f"Summary for {rtos} (CORRECTED Data):\n")
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            f.write("| Metric                    | Min           | Max           | Jitter        | Corrected Avg  |\n")
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n")
            for key in metric_keys:
                stat = corrected_summary[rtos][key]
                f.write("| {:25} | {:13} | {:13} | {:13} | {:14} |\n".format(key, stat['min'], stat['max'], stat['jitter'], stat['robust_avg']))
            f.write("+---------------------------+---------------+---------------+---------------+----------------+\n\n")
            f.write(f"Calculated robust time per iteration (us): {time_iteration_calc[rtos]}\n")
            f.write("\n\n")
    
    import csv

    # Define the CSV output file name.
    output_csv = "summary.csv"
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    with open(output_csv, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # Write header for the summary statistics section.
        header = ["RTOS", "Data Type", "Metric", "Min", "Max", "Jitter", "Robust/Corrected Avg"]
        csvwriter.writerow(header)
        
        # Loop over each RTOS and output both RAW and CORRECTED statistics.
        for rtos in rtoses:
            # RAW Data section.
            for key in metric_keys:
                stat = raw_summary[rtos][key]
                row = [
                    rtos,
                    "RAW",
                    key,
                    stat['min'],
                    stat['max'],
                    stat['jitter'],
                    stat['robust_avg']
                ]
                csvwriter.writerow(row)
            # CORRECTED Data section.
            for key in metric_keys:
                stat = corrected_summary[rtos][key]
                row = [
                    rtos,
                    "CORRECTED",
                    key,
                    stat['min'],
                    stat['max'],
                    stat['jitter'],
                    stat['robust_avg']
                ]
                csvwriter.writerow(row)
        
        # Add a blank row as a separator.
        csvwriter.writerow([])
        
        # Write header for the calculated robust time per iteration.
        csvwriter.writerow(["RTOS", "Calculated robust time per iteration (us)"])
        for rtos in rtoses:
            csvwriter.writerow([rtos, time_iteration_calc[rtos]])

    print(f"Summary CSV written to {output_csv}")
    # Produce bar plots (one per metric) for both raw and corrected robust averages.
    plots_dir = "plots"
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
    
    def bar_plot(metric, ylabel, title, filename, summary_dict, corrected=False):
        # Build list of robust averages for each RTOS.
        values = [summary_dict[rtos][metric]['robust_avg'] for rtos in rtoses]
        plt.figure()
        # plot bars in different colors
        plt.bar(rtoses, values, color=['steelblue', 'forestgreen', 'darkorange'])
        plt.xlabel("RTOS")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.savefig(os.path.join(plots_dir, filename))
        plt.close()
    
    # Raw data plots.
    bar_plot('cycle_count', "Robust Average Cycle Count", 
             "Raw Robust Average Cycle Count Comparison", "raw_robust_avg_cycle_count.png", raw_summary)
    bar_plot('time_period_total', "Robust Average Time Period Total", 
             "Raw Robust Average Time Period Total Comparison", "raw_robust_avg_time_period_total.png", raw_summary)
    bar_plot('icache_miss', "Robust Average ICache Miss", 
             "Raw Robust Average ICache Miss Comparison", "raw_robust_avg_icache_miss.png", raw_summary)
    bar_plot('dcache_access', "Robust Average DCache Access", 
             "Raw Robust Average DCache Access Comparison", "raw_robust_avg_dcache_access.png", raw_summary)
    bar_plot('dcache_miss', "Robust Average DCache Miss", 
             "Raw Robust Average DCache Miss Comparison", "raw_robust_avg_dcache_miss.png", raw_summary)
    
    # Corrected data plots.
    bar_plot('cycle_count', "Corrected Cycle Count", 
             "Corrected Robust Average Cycle Count Comparison", "corrected_robust_avg_cycle_count.png", corrected_summary)
    bar_plot('time_period_total', "Corrected Time Period Total", 
             "Corrected Robust Average Time Period Total Comparison", "corrected_robust_avg_time_period_total.png", corrected_summary)
    bar_plot('icache_miss', "Corrected ICache Miss", 
             "Corrected Robust Average ICache Miss Comparison", "corrected_robust_avg_icache_miss.png", corrected_summary)
    bar_plot('dcache_access', "Corrected DCache Access", 
             "Corrected Robust Average DCache Access Comparison", "corrected_robust_avg_dcache_access.png", corrected_summary)
    bar_plot('dcache_miss', "Corrected DCache Miss", 
             "Corrected Robust Average DCache Miss Comparison", "corrected_robust_avg_dcache_miss.png", corrected_summary)

if __name__ == "__main__":
    main()
