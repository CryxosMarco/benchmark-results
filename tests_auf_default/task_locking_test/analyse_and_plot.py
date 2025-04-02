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


import os, re, glob, statistics, argparse
import numpy as np
import matplotlib.pyplot as plt

def parse_calibration_file(filepath):
    """
    Parse a PMU calibration file and return a dictionary with the median overheads.
    Expected keys: cycle, icache_miss, dcache_access, dcache_miss.
    """
    overheads = {"cycle": [], "icache_miss": [], "dcache_access": [], "dcache_miss": []}
    with open(filepath, 'r') as f:
        for line in f:
            m = re.search(r'Cycle Count:\s*(\d+)', line)
            if m:
                overheads["cycle"].append(int(m.group(1)))
            m = re.search(r'ICache Miss(?: Count)?:\s*(\d+)', line)
            if m:
                overheads["icache_miss"].append(int(m.group(1)))
            m = re.search(r'DCache Access(?: Count)?:\s*(\d+)', line)
            if m:
                overheads["dcache_access"].append(int(m.group(1)))
            m = re.search(r'DCache Miss(?: Count)?:\s*(\d+)', line)
            if m:
                overheads["dcache_miss"].append(int(m.group(1)))
    cal = {}
    for key in overheads:
        cal[key] = statistics.median(overheads[key]) if overheads[key] else 0
    return cal

def parse_test_file(filepath):
    """
    Parse a thread locking test file.
    Returns a dict with:
      - relative_times: list of the relative time markers,
      - locking_ops: list of the "Locking Operations in Period" values,
      - profiles: list of profile entry dictionaries (each with cycle count and cache stats).
    """
    data = {"relative_times": [], "locking_ops": [], "profiles": []}
    with open(filepath, 'r') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for relative time marker
        m = re.search(r'\*\*\*\* Thread Locking Benchmark \*\*\*\* Relative Time:\s*(\d+)', line)
        if m:
            rt = int(m.group(1))
            data["relative_times"].append(rt)
            # Next line expected to be "Locking Operations in Period: <value>"
            if i+1 < len(lines):
                m_ops = re.search(r'Locking Operations in Period:\s*(\d+)', lines[i+1])
                if m_ops:
                    data["locking_ops"].append(int(m_ops.group(1)))
                    i += 2
                    continue
        # Look for a profile entry; it may be labeled "Profile Entry:" or "Profile Point:"
        m = re.search(r'Profile (?:Entry|Point):\s*([\w\d]+)', line)
        if m:
            profile_label = m.group(1)
            profile = {"label": profile_label}
            j = i + 1
            # Read subsequent lines with measurements until an empty line or new section
            while j < len(lines) and lines[j].strip():
                line2 = lines[j]
                m_val = re.search(r'Cycle Count:\s*(\d+)', line2)
                if m_val:
                    profile["cycle"] = int(m_val.group(1))
                m_val = re.search(r'ICache Miss(?: Count)?:\s*(\d+)', line2)
                if m_val:
                    profile["icache_miss"] = int(m_val.group(1))
                m_val = re.search(r'DCache Access(?: Count)?:\s*(\d+)', line2)
                if m_val:
                    profile["dcache_access"] = int(m_val.group(1))
                m_val = re.search(r'DCache Miss(?: Count)?:\s*(\d+)', line2)
                if m_val:
                    profile["dcache_miss"] = int(m_val.group(1))
                j += 1
            data["profiles"].append(profile)
            i = j
            continue
        i += 1
    return data

def adjust_profiles(profiles, calibration):
    """
    Adjust the cycle count in each profile by subtracting the calibration overhead.
    """
    adjusted = []
    for profile in profiles:
        adj = profile.copy()
        if "cycle" in profile:
            adj["cycle"] = profile["cycle"] - calibration.get("cycle", 0)
        adjusted.append(adj)
    return adjusted

def robust_average(values):
    """Compute a robust average (median) for a list of numeric values."""
    return statistics.median(values) if values else 0

def main():
    # Use the script's directory as the default folder
    default_folder = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Benchmark Data Analysis and Plotting")
    parser.add_argument("--folder", type=str, default=default_folder,
                        help="Folder containing benchmark files (default: script directory)")
    args = parser.parse_args()
    
    print("Searching for files in folder:", args.folder)
    
    # Find calibration and test files (calibration files contain the typo 'calibaration')
    calib_files = glob.glob(os.path.join(args.folder, "*_pmu_calibaration.txt"))
    test_files = glob.glob(os.path.join(args.folder, "*_thread_locking_test.txt"))
    
    if not calib_files and not test_files:
        print("No calibration or test files found in folder:", args.folder)
        return

    # Parse calibration data per system (system name assumed to be first part of filename)
    calibrations = {}
    for f in calib_files:
        system = os.path.basename(f).split("_")[0]
        calibrations[system] = parse_calibration_file(f)
        print(f"Calibration for {system}: {calibrations[system]}")
    
    # Parse test files
    tests = {}
    for f in test_files:
        system = os.path.basename(f).split("_")[0]
        tests[system] = parse_test_file(f)
        print(f"Test data for {system}: Relative Times: {tests[system]['relative_times']}, "
              f"Locking Ops: {tests[system]['locking_ops']}, Profiles: {len(tests[system]['profiles'])} entries")
    
    # Adjust profiles using calibration (if available)
    for system in tests:
        if system in calibrations:
            tests[system]["profiles_adjusted"] = adjust_profiles(tests[system]["profiles"], calibrations[system])
        else:
            tests[system]["profiles_adjusted"] = tests[system]["profiles"]
    
    # Compute jitter metrics per system
    jitter_metrics = {}
    for system in tests:
        ops = tests[system]["locking_ops"]
        if ops:
            avg_ops = sum(ops) / len(ops)
            jitter_total = max(ops) - min(ops)
            jitter_pct = (jitter_total / avg_ops) * 100 if avg_ops else 0
            jitter_metrics[system] = {"avg": avg_ops, "jitter_total": jitter_total, "jitter_pct": jitter_pct}
        else:
            jitter_metrics[system] = {"avg": 0, "jitter_total": 0, "jitter_pct": 0}
        print(f"{system}: Jitter total: {jitter_metrics[system]['jitter_total']}, Jitter %: {jitter_metrics[system]['jitter_pct']:.2f}%")
    
    # Compute robust averages for locking operations and adjusted cycle counts
    robust_locking = {}
    robust_cycle = {}
    for system in tests:
        ops = tests[system]["locking_ops"]
        robust_locking[system] = robust_average(ops)
        cycles = [p.get("cycle", 0) for p in tests[system]["profiles_adjusted"] if "cycle" in p]
        robust_cycle[system] = robust_average(cycles)
        print(f"{system}: Robust Locking Ops: {robust_locking[system]}, Robust Cycle Count: {robust_cycle[system]}")
    
    # Compute average cache statistics per system
    cache_stats = {}
    for system in tests:
        profiles = tests[system]["profiles_adjusted"]
        if profiles:
            avg_icache = statistics.mean([p.get("icache_miss", 0) for p in profiles])
            avg_dcache_access = statistics.mean([p.get("dcache_access", 0) for p in profiles])
            avg_dcache_miss = statistics.mean([p.get("dcache_miss", 0) for p in profiles])
        else:
            avg_icache = avg_dcache_access = avg_dcache_miss = 0
        cache_stats[system] = {"ICache Miss": avg_icache, 
                               "DCache Access": avg_dcache_access, 
                               "DCache Miss": avg_dcache_miss}
    
    # Create the output folder "plot" inside the given folder
    output_dir = os.path.join(args.folder, "plot")
    os.makedirs(output_dir, exist_ok=True)
    
    # --- Plot: Locking Operations vs Relative Time ---
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    for system in tests:
        rt = tests[system]["relative_times"]
        ops = tests[system]["locking_ops"]
        if rt and ops:
            ax1.plot(rt, ops, marker='o', label=system)
    ax1.set_title("Locking Operations over Time Period")
    ax1.set_xlabel("Relative Time")
    ax1.set_ylabel("Locking Operations")
    handles, labels = ax1.get_legend_handles_labels()
    if handles:
        ax1.legend()
    plt.tight_layout()
    file1 = os.path.join(output_dir, "locking_operations_over_time.png")
    fig1.savefig(file1)
    plt.close(fig1)
    
    # --- Plot: Jitter Comparison (Separate Plot) ---
    fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(12, 6))
    systems_list = list(jitter_metrics.keys())
    # Jitter Total
    jitter_totals = [jitter_metrics[s]["jitter_total"] for s in systems_list]
    ax2a.bar(systems_list, jitter_totals, color=['steelblue', 'forestgreen', 'darkorange'])
    ax2a.set_title("Jitter Total in Absolute")
    ax2a.set_xlabel("RTOS")
    ax2a.set_ylabel("Jitter Absolute")
    # Jitter Percentage
    jitter_pct = [jitter_metrics[s]["jitter_pct"] for s in systems_list]
    ax2b.bar(systems_list, jitter_pct, color=['steelblue', 'forestgreen', 'darkorange'])
    ax2b.set_title("Jitter Percentage")
    ax2b.set_xlabel("RTOS")
    ax2b.set_ylabel("Jitter (%)")
    plt.suptitle("Jitter Comparison")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    file2 = os.path.join(output_dir, "jitter_comparison.png")
    fig2.savefig(file2)
    plt.close(fig2)
    
    # --- Plot: Robust Locking Operations ---
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    systems_list = list(robust_locking.keys())
    locking_vals = [robust_locking[s] for s in systems_list]
    ax3.bar(systems_list, locking_vals, color=['steelblue', 'forestgreen', 'darkorange'])
    ax3.set_title("Robust Locking Operations Over Time Period")
    ax3.set_xlabel("RTOS")
    ax3.set_ylabel("Average Locking Operations")
    plt.tight_layout()
    file3 = os.path.join(output_dir, "average_locking_ops.png")
    fig3.savefig(file3)
    plt.close(fig3)
    
    # --- Plot: Robust Cycle Count ---
    fig4, ax4 = plt.subplots(figsize=(8, 6))
    systems_list = list(robust_cycle.keys())
    cycle_vals = [robust_cycle[s] for s in systems_list]
    ax4.bar(systems_list, cycle_vals, color=['steelblue', 'forestgreen', 'darkorange'])
    ax4.set_title("Average Cycle Count for Locking a Thread")
    ax4.set_xlabel("RTOS")
    ax4.set_ylabel("Average Cycle Count")
    plt.tight_layout()
    file4 = os.path.join(output_dir, "average_cycle_count_comparison.png")
    fig4.savefig(file4)
    plt.close(fig4)
    
    # --- Plot: Cache Statistics Overview (Averages) ---
    fig5, ax5 = plt.subplots(figsize=(8, 6))
    categories = ["ICache Miss", "DCache Access", "DCache Miss"]
    x = np.arange(len(categories))
    width = 0.2
    systems_cache = list(cache_stats.keys())
    for idx, system in enumerate(systems_cache):
        values = [cache_stats[system][cat] for cat in categories]
        ax5.bar(x + idx * width, values, width, label=system)
    ax5.set_title("Cache Statistics Overview (Averages)")
    ax5.set_xticks(x + width)
    ax5.set_xticklabels(categories)
    handles, labels = ax5.get_legend_handles_labels()
    if handles:
        ax5.legend()
    plt.tight_layout()
    file5 = os.path.join(output_dir, "cache_statistics_overview.png")
    fig5.savefig(file5)
    plt.close(fig5)
    
    import csv

    output_dir = "plot"  # Assuming output_dir is defined like this
    os.makedirs(output_dir, exist_ok=True)
    summary_file = os.path.join(output_dir, "benchmark_summary.csv")

    with open(summary_file, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        header = [
            "System",
            "Avg Locking Ops",
            "Jitter Total",
            "Jitter %",
            "Robust Locking Ops",
            "Robust Cycle Count",
            "ICache Miss",
            "DCache Access",
            "DCache Miss"
        ]
        csvwriter.writerow(header)
        
        systems = sorted(set(list(tests.keys()) + list(calibrations.keys())))
        for system in systems:
            avg_ops = jitter_metrics[system]["avg"] if system in jitter_metrics else 0
            jitter_tot = jitter_metrics[system]["jitter_total"] if system in jitter_metrics else 0
            jitter_percent = jitter_metrics[system]["jitter_pct"] if system in jitter_metrics else 0
            r_lock = robust_locking[system] if system in robust_locking else 0
            r_cycle = robust_cycle[system] if system in robust_cycle else 0
            cache = cache_stats[system] if system in cache_stats else {"ICache Miss": 0, "DCache Access": 0, "DCache Miss": 0}
            
            row = [
                system,
                f"{avg_ops:.2f}",
                jitter_tot,
                f"{jitter_percent:.2f}",
                r_lock,
                r_cycle,
                f"{cache['ICache Miss']:.2f}",
                f"{cache['DCache Access']:.2f}",
                f"{cache['DCache Miss']:.2f}"
            ]
            csvwriter.writerow(row)

    
if __name__ == "__main__":
    main()
