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

# --------------------------------
# Parsing function for synchronization benchmark files
# --------------------------------
def parse_sync_file(filename):
    """
    Parse a synchronization benchmark file.
    Looks for lines with "Relative Time:" and "Time Period Total:".
    Returns two lists:
      - relative_times: the relative time markers (e.g., 30, 60, 90, ...)
      - time_totals: the corresponding "Time Period Total" values (as integers)
    """
    relative_times = []
    time_totals = []
    current_rel = None
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            # Check if the line indicates the relative time.
            if "Relative Time:" in line:
                m = re.search(r'Relative Time:\s*(\d+)', line)
                if m:
                    current_rel = int(m.group(1))
            # When the time period is given, pair it with the last found relative time.
            if "Time Period Total:" in line:
                m = re.search(r'Time Period Total:\s*(\d+)', line)
                if m and current_rel is not None:
                    relative_times.append(current_rel)
                    time_totals.append(int(m.group(1)))
                    current_rel = None  # reset for next block
    return relative_times, time_totals

# --------------------------------
# Utility functions for metrics
# --------------------------------
def compute_stats(values):
    """Return the average, minimum, and maximum of a list of numbers."""
    if not values:
        return 0, 0, 0
    avg = np.mean(values)
    return avg, min(values), max(values)

# --------------------------------
# Plotting functions
# --------------------------------
def plot_sync_comparison(rtos, rel_times, opti_vals, ref_vals):
    """
    Plot the synchronization test data for one RTOS:
      - A line plot overlaying the specific and reference measurements.
      - A second subplot showing the difference (reference - specific).
    If the number of measurements differs between files, the arrays are truncated to the minimum length.
    Saves the plot as "plot/<rtos>_sync_comparison.png".
    """
    # If arrays differ in length, use the shortest one.
    n = min(len(rel_times), len(opti_vals), len(ref_vals))
    if n < len(rel_times) or n < len(opti_vals) or n < len(ref_vals):
        print(f"Truncating data for {rtos} to {n} measurements to match array lengths.")
    rel_times = rel_times[:n]
    opti_vals = opti_vals[:n]
    ref_vals = ref_vals[:n]
    
    # Compute the difference per measurement.
    differences = [r - o for o, r in zip(opti_vals, ref_vals)]
    
    plt.figure(figsize=(10, 8))
    
    # First subplot: overlayed curves.
    plt.subplot(2, 1, 1)
    plt.plot(rel_times, opti_vals, 'bo-', label='Specific Sync. Mechnisms')
    plt.plot(rel_times, ref_vals, 'ro-', label='Reference (via. Semaphores)')
    plt.xlabel("Relative Time")
    plt.ylabel("Time Period Total")
    plt.title(f"{rtos.capitalize()} - RTOS specific Sync. Mechanisms Evaluation")
    plt.legend()
    plt.grid(True)
    
    # Second subplot: difference curve.
    plt.subplot(2, 1, 2)
    plt.plot(rel_times, differences, 'ko-', label='Difference (Reference - Specific)')
    plt.xlabel("Relative Time")
    plt.ylabel("Difference (Reference - Specific)")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    filename = os.path.join(plot_dir, f"{rtos}_sync_comparison.png")
    plt.savefig(filename)
    plt.close()

def plot_average_comparison(summary):
    """
    Generate a bar chart comparing the average 'Time Period Total' for the RTOS-specific
    and reference tests across all RTOSes. For each RTOS, the left bar (steelblue)
    represents the specific sync mechanism, while the right bar (darkorange) represents
    the reference test (via semaphores).
    """
    rtoses = [item['rtos'] for item in summary]
    avg_opti = [item['avg_opti'] for item in summary]
    avg_ref  = [item['avg_ref'] for item in summary]
    
    x = np.arange(len(rtoses))
    bar_width = 0.35
    
    plt.figure(figsize=(8, 6))
    plt.bar(x - bar_width/2, avg_opti, width=bar_width, color='indianred',
            label="Specific Sync. Mechanisms")
    plt.bar(x + bar_width/2, avg_ref, width=bar_width, color='yellowgreen',
            label="Reference (via Semaphores)")
    plt.xticks(x, rtoses)
    plt.xlabel("RTOS")
    plt.ylabel("Average Time Period Total")
    plt.title("Average Synchronization Processing Time Comparison")
    plt.legend()
    plt.grid(True, axis='y')
    
    plot_dir = "plot"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "average_sync_comparison.png"))
    plt.close()


# --------------------------------
# Main analysis function
# --------------------------------
def main():
    # List of RTOS names (as used in file names)
    rtoses = ['freertos', 'threadx', 'zephyr']
    summary = []  # to store computed metrics for each RTOS
    
    for rtos in rtoses:
        # File names are assumed to be:
        #  - <rtos>_opti_sync_mechanisms.txt  (optimized sync mechanisms)
        #  - <rtos>_reference.txt             (standard semaphore reference)
        opti_file = f"{rtos}_opti_sync_mechanisms.txt"
        ref_file  = f"{rtos}_reference.txt"
        
        if not os.path.exists(opti_file) or not os.path.exists(ref_file):
            print(f"Missing files for {rtos}, skipping...")
            continue
        
        # Parse the files.
        rel_times_opti, opti_vals = parse_sync_file(opti_file)
        rel_times_ref, ref_vals   = parse_sync_file(ref_file)
        
        if rel_times_opti != rel_times_ref:
            print(f"Warning: Relative time markers differ for {rtos}")
        # Use the optimized file's markers by default.
        rel_times = rel_times_opti
        
        # Compute statistics for each.
        avg_opti, min_opti, max_opti = compute_stats(opti_vals)
        avg_ref,  min_ref,  max_ref  = compute_stats(ref_vals)
        
        # Save these values in summary.
        summary.append({
            'rtos': rtos.capitalize(),
            'avg_opti': avg_opti,
            'min_opti': min_opti,
            'max_opti': max_opti,
            'avg_ref': avg_ref,
            'min_ref': min_ref,
            'max_ref': max_ref
        })
        
        # Generate the line and difference plots for this RTOS.
        plot_sync_comparison(rtos, rel_times, opti_vals, ref_vals)
        print(f"{rtos.capitalize()}: Processed {len(opti_vals)} measurements.")
    
    # Generate a combined average comparison plot.
    plot_average_comparison(summary)
    import csv
    # Write a summary CSV file.
    output_csv = "summary_sync.csv"
    with open(output_csv, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # Write the header row
        header = [
            "RTOS",
            "Specific Sync Mechanism Avg",
            "Specific Sync Mechanism Min",
            "Specific Sync Mechanism Max",
            "Reference Avg",
            "Reference Min",
            "Reference Max"
        ]
        csvwriter.writerow(header)
        
        # Write each summary item as a row
        for item in summary:
            row = [
                item["rtos"],
                f"{item['avg_opti']:.2f}",
                item["min_opti"],
                item["max_opti"],
                f"{item['avg_ref']:.2f}",
                item["min_ref"],
                item["max_ref"]
            ]
            csvwriter.writerow(row)
    print("Synchronization analysis complete. Summary written to summary_sync.txt and plots saved in the 'plot' directory.")

if __name__ == "__main__":
    main()
