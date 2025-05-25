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
import glob
import argparse
import statistics
import numpy as np
import matplotlib.pyplot as plt
import csv

# Set working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# -------------------------------
# Read calibration statistics
# -------------------------------
def read_calibration_stats(csv_path):
    stats = {}
    with open(csv_path, newline='') as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            stats[row['RTOS'].lower()] = float(row['Mean_Overhead_Cycles'])
    return stats

# -------------------------------
# Parse test file
# -------------------------------
def parse_test_file(filepath):
    data = {"relative_times": [], "locking_ops": [], "profiles": []}
    with open(filepath, 'r') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r'Relative Time:\s*(\d+)', line)
        if m:
            rt = int(m.group(1))
            data["relative_times"].append(rt)
            if i+1 < len(lines):
                m_ops = re.search(r'Locking Operations in Period:\s*(\d+)', lines[i+1])
                if m_ops:
                    data["locking_ops"].append(int(m_ops.group(1)))
                    i += 2
                    continue
        m = re.search(r'Profile (?:Entry|Point):', line)
        if m:
            profile = {}
            j = i + 1
            while j < len(lines) and lines[j].strip():
                line2 = lines[j]
                m_c = re.search(r'Cycle Count:\s*(\d+)', line2)
                if m_c: profile["cycle"] = int(m_c.group(1))
                m_i = re.search(r'ICache Miss(?: Count)?:\s*(\d+)', line2)
                if m_i: profile["icache_miss"] = int(m_i.group(1))
                m_da = re.search(r'DCache Access(?: Count)?:\s*(\d+)', line2)
                if m_da: profile["dcache_access"] = int(m_da.group(1))
                m_dm = re.search(r'DCache Miss(?: Count)?:\s*(\d+)', line2)
                if m_dm: profile["dcache_miss"] = int(m_dm.group(1))
                j += 1
            data["profiles"].append(profile)
            i = j
            continue
        i += 1
    return data

# -------------------------------
# Adjust profiles
# -------------------------------
def adjust_profiles(profiles, cycle_overhead):
    adjusted = []
    for p in profiles:
        adj = p.copy()
        if "cycle" in p:
            adj["cycle"] = max(p["cycle"] - cycle_overhead, 0)
        adjusted.append(adj)
    return adjusted

# -------------------------------
# Trimmed mean
# -------------------------------
def robust_average(values, trim_fraction=0.1):
    arr = np.array(values)
    n = len(arr)
    if n == 0: return 0.0
    tc = int(n * trim_fraction)
    if n - 2*tc <= 0: return np.mean(arr)
    trimmed = np.sort(arr)[tc:n-tc]
    return float(trimmed.mean())

# -------------------------------
# Main
# -------------------------------
def main():
    parser = argparse.ArgumentParser(description="Thread Locking Benchmark Analysis")
    parser.add_argument('--folder', default=script_dir)
    args = parser.parse_args()

    # Load overheads
    cal_csv = os.path.normpath(os.path.join(args.folder, '..', '..', 'pmu_calibration', 'calibration_stats.csv'))
    cycle_overheads = read_calibration_stats(cal_csv)

    # Collect tests
    test_files = glob.glob(os.path.join(args.folder, '*_thread_locking_test.txt'))
    tests = {}
    summary = []
    for f in test_files:
        system = os.path.basename(f).split('_')[0].lower()
        data = parse_test_file(f)
        overhead = cycle_overheads.get(system, 0.0)
        data['profiles_adjusted'] = adjust_profiles(data['profiles'], overhead)
        tests[system] = data

        # Jitter ops
        ops = data['locking_ops']
        avg_ops = float(np.mean(ops)) if ops else 0.0
        jitter_tot = max(ops)-min(ops) if ops else 0.0
        jitter_pct = (jitter_tot/avg_ops*100) if avg_ops else 0.0

        # Robust metrics
        rob_lock = robust_average(ops)
        cycles = [p['cycle'] for p in data['profiles_adjusted'] if 'cycle' in p]
        rob_cycle = robust_average(cycles)

        # Cache means
        icache = [p.get('icache_miss',0) for p in data['profiles_adjusted']]
        daccess= [p.get('dcache_access',0) for p in data['profiles_adjusted']]
        dmiss  = [p.get('dcache_miss',0) for p in data['profiles_adjusted']]
        ic_mean = float(np.mean(icache)) if icache else 0.0
        da_mean = float(np.mean(daccess)) if daccess else 0.0
        dm_mean = float(np.mean(dmiss)) if dmiss else 0.0

        summary.append({
            'system': system.capitalize(),
            'avg_ops': avg_ops,
            'jitter_tot': jitter_tot,
            'jitter_pct': jitter_pct,
            'rob_lock': rob_lock,
            'rob_cycle': rob_cycle,
            'icache_avg': ic_mean,
            'daccess_avg': da_mean,
            'dmiss_avg': dm_mean
        })

    # Output directory
    out_dir = os.path.join(args.folder, 'plot')
    os.makedirs(out_dir, exist_ok=True)

    # Plot 1: Cycle Count over Profile Points
    # Define consistent color mapping
    color_map = {'Freertos': 'steelblue', 'Threadx': 'darkorange', 'Zephyr': 'forestgreen'}
    plt.figure(figsize=(8,6))
    for sys,data in tests.items():
        name = sys.capitalize()
        cycles = [p['cycle'] for p in data['profiles_adjusted'] if 'cycle' in p]
        if cycles:
            plt.plot(
                range(1, len(cycles)+1), cycles,
                marker='o', label=name,
                color=color_map.get(name, 'steelblue')
            )
    plt.title('Cycle Count over Profile Points')
    plt.xlabel('Profile Index')
    plt.ylabel('Adjusted Cycle Count')
    plt.legend(); plt.grid(True)
    plt.tight_layout(); plt.savefig(os.path.join(out_dir,'cycle_count_over_time.png'), dpi=300)
    plt.close()

    # Plot 2: Jitter comparison
    names = [it['system'] for it in summary]
    tot = [it['jitter_tot'] for it in summary]
    pct = [it['jitter_pct'] for it in summary]
    fig,axes = plt.subplots(1,2,figsize=(12,6))
    axes[0].bar(names, tot, color=['steelblue','forestgreen','darkorange']); axes[0].set_title('Jitter Total')
    axes[1].bar(names, pct, color=['steelblue','forestgreen','darkorange']); axes[1].set_title('Jitter %')
    for ax in axes: ax.grid(axis='y')
    plt.suptitle('Jitter Comparison'); plt.tight_layout(rect=[0,0.03,1,0.95])
    plt.savefig(os.path.join(out_dir,'jitter_comparison.png'), dpi=300); plt.close()

    # Plot 3: Robust Averages Comparison
    fig, ax = plt.subplots(figsize=(8,6))

    # Define consistent color mapping
    color_map = {'Freertos': 'steelblue', 'Threadx': 'darkorange', 'Zephyr': 'forestgreen'}

    names = [it['system'] for it in summary]
    rob_cycles = [it['rob_cycle'] for it in summary]
    # Assign colors per RTOS
    colors = [color_map.get(name, 'steelblue') for name in names]

    bars = ax.bar(names, rob_cycles, color=colors)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h, f'{h:.1f}', ha='center', va='bottom', fontsize=8)
    ax.set_title('Average adjusted Cycle Count Comparison')
    ax.set_xlabel('RTOS')
    ax.set_ylabel('Average Adjusted Cycle Count')
    ax.grid(axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir,'average_adjusted_cycle_comparison.png'), dpi=300)
    plt.close()

    # Plot 4: Average Locking Operations Comparison
    fig, ax = plt.subplots(figsize=(8,6))

    # Use same color mapping for consistency
    avg_ops = [it['avg_ops'] for it in summary]
    colors_ops = [color_map.get(it['system'], 'steelblue') for it in summary]

    bars = ax.bar(names, avg_ops, color=colors_ops)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h, f'{h:.1f}', ha='center', va='bottom', fontsize=8)
    ax.set_title('Average Locking Operations per Time Period Comparison')
    ax.set_xlabel('RTOS')
    ax.set_ylabel('Average Locking Operations')
    ax.grid(axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir,'average_locking_ops_comparison.png'), dpi=300)
    plt.close()

    # Plot 4: Cache stats
    cats = ['ICache','DCache Access','DCache Miss']
    x = np.arange(len(cats)); width=0.2
    plt.figure(figsize=(8,6))
    for i,it in enumerate(summary):
        vals=[it['icache_avg'],it['daccess_avg'],it['dmiss_avg']]
        plt.bar(x+i*width, vals, width, label=it['system'])
    plt.xticks(x+width, cats); plt.title('Cache Averages'); plt.legend(); plt.grid(axis='y')
    plt.tight_layout(); plt.savefig(os.path.join(out_dir,'cache_averages.png'), dpi=300); plt.close()

    # CSV
    csvf = os.path.join(out_dir,'benchmark_summary.csv')
    with open(csvf,'w',newline='') as cf:
        w=csv.writer(cf)
        w.writerow(['System','Avg Ops','Jitter Tot','Jitter %','Rob Lock','Rob Cycle','ICache Avg','DCache Access Avg','DCache Miss Avg'])
        for it in summary:
            w.writerow([it['system'],f"{it['avg_ops']:.2f}",it['jitter_tot'],f"{it['jitter_pct']:.2f}",
                        f"{it['rob_lock']:.2f}",f"{it['rob_cycle']:.2f}",
                        f"{it['icache_avg']:.2f}",f"{it['daccess_avg']:.2f}",f"{it['dmiss_avg']:.2f}"])
    print(f"Analysis complete. Summary at {csvf}")

if __name__=='__main__':
    main()
