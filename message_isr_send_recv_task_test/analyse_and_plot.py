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
    Create a cycle count over time plot (for a given file) and removes the first measurement.
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
            colors = [cmap(j) for j in range(len(rtos_names))]
            axs[i].bar(x, means, yerr=errors, capsize=5, color=colors, edgecolor='black')
            axs[i].set_xticks(x)
            axs[i].set_xticklabels(rtos_names)
            axs[i].set_title(f"{metric} (Msg Size: {size} bytes)")
            axs[i].set_ylabel("Adjusted Value")
            axs[i].grid(True, axis='y')
        plt.tight_layout()
        plt.savefig(f"plot/cache_comparison_{size}.png")
        plt.close()

# -------------------------------
# Plotting function for average cycle count per RTOS
# -------------------------------

def plot_average_cycle_counts(summary):
    """
    Group summary data by RTOS and plot the average cycle count (averaged from receive and send)
    versus the message size.
    One plot is generated per RTOS.
    """
    rtos_groups = {}
    for item in summary:
        rtos = item['rtos']
        if rtos not in rtos_groups:
            rtos_groups[rtos] = []
        rtos_groups[rtos].append(item)
    
    for rtos, items in rtos_groups.items():
        items_sorted = sorted(items, key=lambda x: x['message_size_bytes'])
        sizes = [x['message_size_bytes'] for x in items_sorted]
        avg_cycles = [x['avg_cycle'] for x in items_sorted]
        plt.figure(figsize=(8, 6))
        plt.plot(sizes, avg_cycles, marker='o', linestyle='-', label=f'{rtos} Avg Cycle')
        plt.title(f"Average Cycle Count for {rtos}")
        plt.xlabel("Message Size (bytes)")
        plt.ylabel("Average Adjusted Cycle Count")
        plt.grid(True)
        plt.legend()
        plt.savefig(f"plot/avg_cycle_{rtos.lower()}.png")
        plt.close()

def plot_robust_average_comparison(summary):
    """
    Create a comparison plot with the robust average cycle counts for each RTOS
    across message sizes. All RTOS are plotted on one figure.
    """
    # Group data by RTOS
    rtos_groups = {}
    for item in summary:
        rtos = item['rtos']
        if rtos not in rtos_groups:
            rtos_groups[rtos] = []
        rtos_groups[rtos].append((item['message_size_bytes'], item['avg_cycle']))
    
    plt.figure(figsize=(10, 6))
    # Plot each RTOS data series
    for rtos, data in rtos_groups.items():
        # Sort by message size for a smooth line plot
        data_sorted = sorted(data, key=lambda x: x[0])
        sizes = [d[0] for d in data_sorted]
        avg_cycles = [d[1] for d in data_sorted]
        plt.plot(sizes, avg_cycles, marker='o', linestyle='-', label=rtos)
    
    plt.xlabel("Message Size (bytes)")
    plt.ylabel("Robust Average Cycle Count")
    plt.title("Comparison of Robust Average Cycle Counts Among RTOS")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("plot/robust_average_comparison.png")
    plt.close()


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
            # Plot cycle counts (first measurement removed)
            plot_cycle_counts(file, analysis, rtos.capitalize(), size)
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
    
    # Write summary file (rounded to two decimals)
    with open("plot/summary.txt", "w") as f:
        for item in summary:
            f.write(f"File: {item['file']}\n")
            f.write(f"RTOS: {item['rtos']}\n")
            f.write(f"Message Size: {item['message_size_bytes']} bytes\n")
            f.write(f"Average Receive Cycle: {item['avg_receive_cycle']:.2f}\n")
            f.write(f"Average Send Cycle: {item['avg_send_cycle']:.2f}\n")
            f.write(f"Average Cycle (Overall): {item['avg_cycle']:.2f}\n")
            f.write(f"ICache Miss Range: {item['icache_min']:.2f} - {item['icache_max']:.2f}\n")
            f.write(f"DCache Access Range: {item['dcache_access_min']:.2f} - {item['dcache_access_max']:.2f}\n")
            f.write(f"DCache Miss Range: {item['dcache_miss_min']:.2f} - {item['dcache_miss_max']:.2f}\n")
            f.write("-" * 40 + "\n")
    
    # Create grouped cache comparison plots (per message size)
    plot_cache_comparison(summary)
    # Create average cycle count plots for each RTOS
    plot_average_cycle_counts(summary)
    # Create a single comparison plot for robust average cycle counts across all RTOS
    plot_robust_average_comparison(summary)
    
    print("Analysis complete. Summary written to summary.txt and plots saved in the 'plot' directory.")

if __name__ == "__main__":
    main()
