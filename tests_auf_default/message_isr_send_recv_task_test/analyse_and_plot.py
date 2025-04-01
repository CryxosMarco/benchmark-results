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
# Benchmark parsing
# -------------------------------

def parse_benchmark_file(filename, calibration):
    """
    Parse a benchmark file and subtract the calibration overhead for each PMU measurement.
    Accepts both formats with or without "Count" in the metric lines.
    Returns two lists of dictionaries: one for the Receive section and one for the Send section.
    """
    receive = []
    send = []
    current_section = None
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            # Detect section changes (allow extra words such as "Profile Point")
            if line.startswith("Receive Latency"):
                current_section = "receive"
                continue
            if line.startswith("Send Latency"):
                current_section = "send"
                continue

            # Cycle Count
            m = re.match(r'Cycle Count(?: Count)?:\s+(\d+)', line)
            if m and current_section:
                value = float(m.group(1)) - calibration['cycle']
                value = max(value, 0)
                current_dict = {'cycle': value}
                if current_section == "receive":
                    receive.append(current_dict)
                else:
                    send.append(current_dict)
                continue

            # ICache Miss
            m = re.match(r'ICache Miss(?: Count)?:\s+(\d+)', line)
            if m and current_section:
                value = float(m.group(1)) - calibration['icache']
                value = max(value, 0)
                if current_section == "receive" and receive:
                    receive[-1]['icache'] = value
                elif current_section == "send" and send:
                    send[-1]['icache'] = value
                continue

            # DCache Access
            m = re.match(r'DCache Access(?: Count)?:\s+(\d+)', line)
            if m and current_section:
                value = float(m.group(1)) - calibration['dcache_access']
                value = max(value, 0)
                if current_section == "receive" and receive:
                    receive[-1]['dcache_access'] = value
                elif current_section == "send" and send:
                    send[-1]['dcache_access'] = value
                continue

            # DCache Miss
            m = re.match(r'DCache Miss(?: Count)?:\s+(\d+)', line)
            if m and current_section:
                value = float(m.group(1)) - calibration['dcache_miss']
                value = max(value, 0)
                if current_section == "receive" and receive:
                    receive[-1]['dcache_miss'] = value
                elif current_section == "send" and send:
                    send[-1]['dcache_miss'] = value
                continue
    return receive, send

def analyze_file(filepath, calibration):
    """
    Analyze one benchmark file:
      - Compute robust average cycle counts for both Receive and Send (after subtracting overhead).
      - Determine the min and max values for each cache metric.
    Returns a dictionary with all extracted data.
    """
    receive, send = parse_benchmark_file(filepath, calibration)
    receive_cycles = [entry['cycle'] for entry in receive if 'cycle' in entry]
    send_cycles    = [entry['cycle'] for entry in send if 'cycle' in entry]
    
    avg_receive_cycle = round(robust_average(receive_cycles), 2) if receive_cycles else 0.0
    avg_send_cycle    = round(robust_average(send_cycles), 2) if send_cycles else 0.0
    avg_cycle = round((avg_receive_cycle + avg_send_cycle) / 2, 2)

    icache_values = []
    dcache_access_values = []
    dcache_miss_values = []
    for entry in (receive + send):
        if 'icache' in entry:
            icache_values.append(entry['icache'])
        if 'dcache_access' in entry:
            dcache_access_values.append(entry['dcache_access'])
        if 'dcache_miss' in entry:
            dcache_miss_values.append(entry['dcache_miss'])
    
    icache_min = round(min(icache_values), 2) if icache_values else 0.0
    icache_max = round(max(icache_values), 2) if icache_values else 0.0
    dcache_access_min = round(min(dcache_access_values), 2) if dcache_access_values else 0.0
    dcache_access_max = round(max(dcache_access_values), 2) if dcache_access_values else 0.0
    dcache_miss_min = round(min(dcache_miss_values), 2) if dcache_miss_values else 0.0
    dcache_miss_max = round(max(dcache_miss_values), 2) if dcache_miss_values else 0.0
    
    analysis = {
        'avg_receive_cycle': avg_receive_cycle,
        'avg_send_cycle': avg_send_cycle,
        'avg_cycle': avg_cycle,
        'icache_min': icache_min,
        'icache_max': icache_max,
        'dcache_access_min': dcache_access_min,
        'dcache_access_max': dcache_access_max,
        'dcache_miss_min': dcache_miss_min,
        'dcache_miss_max': dcache_miss_max,
        'receive_cycles': receive_cycles,
        'send_cycles': send_cycles,
    }
    return analysis

# -------------------------------
# Plotting functions for file-level cycle counts
# -------------------------------

def plot_cycle_counts(filename, analysis, rtos, size):
    """
    Create a cycle count over time plot (for a given file) and remove the first measurement.
    Saves the plot in the "plot" directory.
    """
    receive_cycles = analysis['receive_cycles']
    send_cycles = analysis['send_cycles']

    # Remove the first measurement if available.
    if len(receive_cycles) > 1:
        receive_cycles = receive_cycles[1:]
        iterations_r = list(range(2, len(analysis['receive_cycles']) + 1))
    else:
        iterations_r = list(range(1, len(receive_cycles) + 1))
    if len(send_cycles) > 1:
        send_cycles = send_cycles[1:]
        iterations_s = list(range(2, len(analysis['send_cycles']) + 1))
    else:
        iterations_s = list(range(1, len(send_cycles) + 1))
    
    plt.figure(figsize=(10, 6))
    plt.plot(iterations_r, receive_cycles, marker='o', label='Receive Cycle')
    plt.plot(iterations_s, send_cycles, marker='x', label='Send Cycle')
    plt.title(f"{rtos} {size*4} bytes Cycle Count")
    plt.xlabel("Iteration")
    plt.ylabel("Adjusted Cycle Count")
    plt.legend()
    plt.grid(True)
    
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    base = os.path.basename(filename)
    plot_filename = os.path.join(plot_dir, base.replace("_isr_task_queue_test.txt", "_cycle.png"))
    plt.savefig(plot_filename)
    plt.close()

# -------------------------------
# Plotting functions for grouped cache comparison
# -------------------------------

def plot_cache_comparison(summary):
    """
    For each message size bucket, create a grouped plot comparing the cache metrics
    (ICache Miss, DCache Access, DCache Miss) among the available RTOS.
    One figure is created per message size, with 3 subplots (one per metric).
    """
    # Group summary items by message size
    size_groups = {}
    for item in summary:
        size = item['message_size_bytes']
        if size not in size_groups:
            size_groups[size] = []
        size_groups[size].append(item)
    
    for size, items in size_groups.items():
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))
        metrics = ['ICache', 'DCache Access', 'DCache Miss']
        for i, metric in enumerate(metrics):
            rtos_names = []
            means = []
            errors = []
            for item in items:
                rtos = item['rtos']
                rtos_names.append(rtos)
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
            # Use a colormap to assign distinct colors for each RTOS bar.
            import matplotlib.cm as cm
            cmap = cm.get_cmap('viridis', len(rtos_names))
            # colors = [cmap(j) for j in range(len(rtos_names))]
            axs[i].bar(x, means, yerr=errors, capsize=5, color=['steelblue', 'darkorange', 'forestgreen'], edgecolor='black')
            axs[i].set_xticks(x)
            axs[i].set_xticklabels(rtos_names)
            axs[i].set_title(f"{metric} (Msg Size: {size} bytes)")
            axs[i].set_ylabel("Adjusted Value")
            axs[i].grid(True, axis='y')
        plt.tight_layout()
        plt.savefig(os.path.join("plot", f"cache_comparison_{size}.png"))
        plt.close()

# -------------------------------
# Plotting function for combined average cycle counts
# -------------------------------

def plot_combined_average_cycle_counts(summary):
    """
    Create a single plot showing the average cycle counts for each RTOS
    across message sizes for better comparability.
    """
    # Group data by RTOS
    rtos_groups = {}
    for item in summary:
        rtos = item['rtos']
        if rtos not in rtos_groups:
            rtos_groups[rtos] = []
        rtos_groups[rtos].append((item['message_size_bytes'], item['avg_cycle']))
    
    plt.figure(figsize=(10, 6))
    for rtos, data in rtos_groups.items():
        data_sorted = sorted(data, key=lambda x: x[0])
        sizes = [d[0] for d in data_sorted]
        avg_cycles = [d[1] for d in data_sorted]
        plt.plot(sizes, avg_cycles, marker='o', linestyle='-', label=rtos)
    
    plt.xlabel("Message Size (bytes)")
    plt.ylabel("Robust Average Adjusted Cycle Count")
    plt.title("Comparison of Rubust Average Cycle Counts Among RTOS over Message Sizes")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plot_filename = os.path.join(plot_dir, "combined_average_cycle_counts.png")
    plt.savefig(plot_filename)
    plt.close()
    print(f"Combined average cycle counts plot saved to {plot_filename}")

# -------------------------------
# New Plotting function: Stacked send cycles per RTOS
# -------------------------------

def plot_stacked_send_cycles_by_rtos(time_series_list):
    """
    For each RTOS, create one figure with stacked subplots showing send cycle counts 
    over time for message sizes 2, 4, 8, 16, and 32 (as parsed from filenames).
    Each subplot (for a given message size) plots all send cycle time series for that size.
    """
    sizes_to_plot = [2, 4, 8, 16, 32]
    
    # Group entries by RTOS, filtering only for the selected message sizes.
    rtos_groups = {}
    for entry in time_series_list:
        if entry['original_size'] in sizes_to_plot:
            rtos = entry['rtos']
            rtos_groups.setdefault(rtos, []).append(entry)
    
    # For each RTOS, further group by original_size and create a stacked figure.
    for rtos, entries in rtos_groups.items():
        # Group by message size.
        size_groups = {}
        for entry in entries:
            orig_size = entry['original_size']
            size_groups.setdefault(orig_size, []).append(entry)
        
        sorted_sizes = sorted(size_groups.keys())
        num_plots = len(sorted_sizes)
        
        fig, axs = plt.subplots(num_plots, 1, figsize=(10, 4*num_plots), sharex=True)
        if num_plots == 1:
            axs = [axs]
        
        for ax, size in zip(axs, sorted_sizes):
            group_entries = size_groups[size]
            for entry in group_entries:
                send_cycles = entry['send_cycles']
                # Remove the first measurement if available.
                if len(send_cycles) > 1:
                    s_cycles = send_cycles[1:]
                    iterations = list(range(2, len(send_cycles) + 1))
                else:
                    s_cycles = send_cycles
                    iterations = list(range(1, len(send_cycles) + 1))
                ax.plot(iterations, s_cycles, marker='o', label=entry['file'])
            ax.set_title(f"{rtos} - {size*4} bytes Send Cycle Count")
            ax.set_ylabel("Adjusted Cycle Count")
            ax.grid(True)
            ax.legend(fontsize='small', loc='best')
        
        plt.xlabel("Iteration")
        plt.tight_layout()
        plot_dir = "plot"
        if not os.path.exists(plot_dir):
            os.makedirs(plot_dir)
        filename = os.path.join(plot_dir, f"stacked_send_cycles_{rtos.lower()}.png")
        plt.savefig(filename)
        plt.close()
        print(f"Stacked send cycles plot saved for {rtos} to {filename}")

# -------------------------------
# Main function
# -------------------------------

def main():
    # Define RTOS names as they appear in filenames.
    rtos_list = ['freertos', 'threadx', 'zephyr']
    calibration_data = {}
    
    # Process calibration files (e.g. freertos_pmu_calibaration.txt)
    for rtos in rtos_list:
        cal_file = f"{rtos}_pmu_calibaration.txt"
        if os.path.exists(cal_file):
            calibration_data[rtos] = parse_calibration_file(cal_file)
            print(f"Calibration for {rtos}: {calibration_data[rtos]}")
        else:
            calibration_data[rtos] = {'cycle': 0.0, 'icache': 0.0, 'dcache_access': 0.0, 'dcache_miss': 0.0}
    
    summary = []
    time_series_list = []
    # Process benchmark files matching <size>_<rtos>_isr_task_queue_test.txt
    for file in os.listdir('.'):
        m = re.match(r'(\d+)_([a-zA-Z]+)_isr_task_queue_test\.txt', file)
        if m:
            size = int(m.group(1))
            rtos = m.group(2).lower()
            if rtos not in calibration_data:
                continue
            cal = calibration_data[rtos]
            analysis = analyze_file(file, cal)
            # Optionally, plot individual file cycle counts
            plot_cycle_counts(file, analysis, rtos.capitalize(), size)
            # Append time series data for the stacked send cycles plots
            time_series_list.append({
                'file': file,
                'rtos': rtos.capitalize(),
                'original_size': size,
                'message_size_bytes': size * 4,
                'receive_cycles': analysis['receive_cycles'],
                'send_cycles': analysis['send_cycles']
            })
            # Add summary data with numeric cache values and computed average cycle count
            summary.append({
                'file': file,
                'rtos': rtos.capitalize(),
                'message_size_bytes': size * 4,
                'avg_receive_cycle': analysis['avg_receive_cycle'],
                'avg_send_cycle': analysis['avg_send_cycle'],
                'avg_cycle': analysis['avg_cycle'],
                'icache_min': analysis['icache_min'],
                'icache_max': analysis['icache_max'],
                'dcache_access_min': analysis['dcache_access_min'],
                'dcache_access_max': analysis['dcache_access_max'],
                'dcache_miss_min': analysis['dcache_miss_min'],
                'dcache_miss_max': analysis['dcache_miss_max']
            })
    import csv
    # Write summary file (rounded to two decimals)
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    csv_filename = os.path.join(plot_dir, "summary.csv")
    with open(csv_filename, mode="w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # Write header row
        header = [
            "File",
            "RTOS",
            "Message Size (bytes)",
            "Average Receive Cycle",
            "Average Send Cycle",
            "Average Cycle (Overall)",
            "ICache Miss Min",
            "ICache Miss Max",
            "DCache Access Min",
            "DCache Access Max",
            "DCache Miss Min",
            "DCache Miss Max"
        ]
        csvwriter.writerow(header)
        
        # Write data rows
        for item in summary:
            row = [
                item["file"],
                item["rtos"],
                item["message_size_bytes"],
                f"{item['avg_receive_cycle']:.2f}",
                f"{item['avg_send_cycle']:.2f}",
                f"{item['avg_cycle']:.2f}",
                f"{item['icache_min']:.2f}",
                f"{item['icache_max']:.2f}",
                f"{item['dcache_access_min']:.2f}",
                f"{item['dcache_access_max']:.2f}",
                f"{item['dcache_miss_min']:.2f}",
                f"{item['dcache_miss_max']:.2f}"
            ]
            csvwriter.writerow(row)
    
    # Create grouped cache comparison plots (per message size)
    plot_cache_comparison(summary)
    # Create one combined average cycle count plot for better comparability
    plot_combined_average_cycle_counts(summary)
    # Create a stacked send cycles plot per RTOS for message sizes 2,4,8,16,32
    plot_stacked_send_cycles_by_rtos(time_series_list)
    
    print("Analysis complete. Summary written to summary.csv and plots saved in the 'plot' directory.")

if __name__ == "__main__":
    main()
