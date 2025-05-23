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
import csv

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

def read_calibration_stats(filename):
    """
    Reads calibration_stats.csv and returns a dict mapping lowercase RTOS names
    to their mean overheads for cycle, icache, dcache_access, and dcache_miss.
    """
    stats = {}
    with open(filename, newline='') as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            rtos = row['RTOS'].lower()
            stats[rtos] = {
                'cycle': float(row['Mean_Overhead_Cycles']),
                'icache': float(row.get('Mean_Overhead_ICache', 0.0)),
                'dcache_access': float(row.get('Mean_Overhead_DCache_Access', 0.0)),
                'dcache_miss': float(row.get('Mean_Overhead_DCache_Miss', 0.0))
            }
    return stats
# ---------- Statistical Functions ----------

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

def bar_plot(metric, ylabel, title, filename, summary_dict):
    """
    Draws a bar chart of the robust averages for a given metric,
    with RTOS-specific colors: Freertos=steelblue, ThreadX=forestgreen, Zephyr=darkorange.
    """
    rtoses = list(summary_dict.keys())
    # map each RTOS to its specified color
    color_map = {
        'freertos': 'steelblue',
        'threadx': 'forestgreen',
        'zephyr':   'darkorange'
    }
    # collect values and corresponding colors
    values = [summary_dict[r][metric]['robust_avg'] for r in rtoses]
    colors = [color_map.get(r.lower(), 'gray') for r in rtoses]

    plt.figure(figsize=(6, 4))
    bars = plt.bar(rtoses, values, color=colors)
    # annotate each bar with its height
    for bar in bars:
        h = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2, 
            h, 
            f"{h:.1f}", 
            ha='center', 
            va='bottom', 
            fontsize=8
        )

    plt.xlabel("RTOS")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()

    os.makedirs("plots", exist_ok=True)
    plt.savefig(os.path.join("plots", filename), dpi=300)
    plt.close()


# ---------- Main Workflow ----------

def main():
    rtoses = ['freertos', 'threadx', 'zephyr']
    metric_keys = ['time_period_total','cycle_count','icache_miss','dcache_access','dcache_miss']

    # 1. Read calibration overheads from CSV
    calib_csv = os.path.join('..','..','pmu_calibration','calibration_stats.csv')
    calibration_stats = read_calibration_stats(calib_csv)

    # 2. Parse and correct raw measurements
    raw_measurements = {}
    for r in rtoses:
        fname = f"{r}_task_sync.txt"
        if not os.path.exists(fname):
            raw_measurements[r] = []
            continue
        meas = parse_sync_file(fname)
        # subtract calibration overheads
        ov = calibration_stats.get(r, {})
        for m in meas:
            if 'cycle_count' in m and not np.isnan(m['cycle_count']):
                m['cycle_count'] = max(m['cycle_count'] - ov.get('cycle',0.0), 0)
            for key in ('icache_miss','dcache_access','dcache_miss'):
                if key in m and not np.isnan(m[key]):
                    m[key] = max(m[key] - ov.get(key.replace('_miss','').replace('_access',''),0.0), 0)
        raw_measurements[r] = meas

    # 3. Summaries
    raw_summary = {}
    for r in rtoses:
        raw_summary[r] = compute_summary(raw_measurements[r], metric_keys)

    corrected_summary = {}
    for r in rtoses:
        calib = {
            'cycle_count': calibration_stats.get(r,{}).get('cycle',0.0),
            'icache_miss': calibration_stats.get(r,{}).get('icache',0.0),
            'dcache_access': calibration_stats.get(r,{}).get('dcache_access',0.0),
            'dcache_miss': calibration_stats.get(r,{}).get('dcache_miss',0.0),
            'time_period_total': 0.0
        }
        corrected_summary[r] = compute_corrected_summary(raw_summary[r], calib)

    # 4. Write summary.csv
    with open("summary.csv","w", newline="") as cf:
        w = csv.writer(cf)
        w.writerow(["RTOS","Type","Metric","Min","Max","Jitter","Robust Avg"])
        for r in rtoses:
            for k in metric_keys:
                s = raw_summary[r][k]
                w.writerow([r,"RAW",k,s['min'],s['max'],s['jitter'],s['robust_avg']])
            for k in metric_keys:
                s = corrected_summary[r][k]
                w.writerow([r,"CORRECTED",k,s['min'],s['max'],s['jitter'],s['robust_avg']])

    # 5. Generate bar plots
    bar_plot('cycle_count', "Cycle Count", "Corrected Robust Avg Cycle Count", "cycle_count_comparison.png", corrected_summary)
    bar_plot('icache_miss', "ICache Miss", "Corrected Robust Avg ICache Miss", "icache_miss_comparison.png", corrected_summary)
    bar_plot('dcache_access', "DCache Access", "Corrected Robust Avg DCache Access", "dcache_access_comparison.png", corrected_summary)
    bar_plot('dcache_miss', "DCache Miss", "Corrected Robust Avg DCache Miss", "dcache_miss_comparison.png", corrected_summary)
    bar_plot('time_period_total',"Time Period Total","Corrected Robust Avg Time Period Total","time_period_total_comparison.png",corrected_summary)

if __name__ == "__main__":
    main()