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
import glob
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# --- Custom Formatter: Use dots as thousand separators ---
def format_with_points(x, pos):
    """
    Format the number x as a string with a dot as the thousand separator.
    If x is nearly an integer, no decimals are shown; otherwise, three decimals are shown.
    Example: 20000000 becomes "20.000.000".
    """
    # If x is effectively an integer, format without decimals
    if abs(x - int(x)) < 1e-6:
        return "{:,.0f}".format(x).replace(",", ".")
    else:
        return "{:,.3f}".format(x).replace(",", ".")

def set_custom_formatter(ax):
    """Apply the custom formatter to both the x and y axes of the given axis."""
    formatter = FuncFormatter(format_with_points)
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)

# --- Helper Function to Parse a Test File ---
def parse_file(file_path):
    """
    Reads a test file and extracts the measurements.
    Returns a DataFrame with columns: time, sent, received, errors.
    """
    data = []
    with open(file_path, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        if "Multi Producer/Consumer Message Queue Test" in lines[i]:
            m_time = re.search(r"Time:\s*(\d+)\s*sec", lines[i])
            time_val = int(m_time.group(1)) if m_time else None

            i += 1
            m_sent = re.search(r"Messages Sent in Period:\s*(\d+)", lines[i])
            sent_val = int(m_sent.group(1)) if m_sent else None

            i += 1
            m_recv = re.search(r"Messages Received in Period:\s*(\d+)", lines[i])
            recv_val = int(m_recv.group(1)) if m_recv else None

            i += 1
            m_err = re.search(r"Integrity Errors:\s*(\d+)", lines[i])
            err_val = int(m_err.group(1)) if m_err else None

            data.append({
                'time': time_val,
                'sent': sent_val,
                'received': recv_val,
                'errors': err_val
            })
        i += 1

    return pd.DataFrame(data)

# --- Function to Output Summary Statistics as Text ---
def output_summary(summary_df):
    os.makedirs("plot", exist_ok=True)
    
    # Write summary as text file
    summary_txt_file = "plot/summary_statistics.txt"
    with open(summary_txt_file, "w") as f:
        f.write("Summary Statistics:\n")
        f.write(summary_df.to_string(index=False))
    print(f"Summary written to {summary_txt_file}")
    
    # Write summary as CSV file
    summary_csv_file = "plot/summary_statistics.csv"
    summary_df.to_csv(summary_csv_file, index=False)
    print(f"Summary written to {summary_csv_file}")


# --- Main Analysis and Plotting ---
def main():
    file_pattern = "*_multi_task_queue_test.txt"
    files = glob.glob(file_pattern)

    results = {}
    summary_list = []

    for file in files:
        base = os.path.basename(file)
        m = re.match(r"(\d+)_([a-zA-Z]+)_multi_task_queue_test\.txt", base)
        if not m:
            continue

        size = int(m.group(1))       # This number multiplied by 4 gives the byte count.
        rtos = m.group(2).lower()      # e.g. freertos, threadx, zephyr

        df = parse_file(file)
        results[(size, rtos)] = df

        avg_sent = df['sent'].mean()
        min_sent = df['sent'].min()
        max_sent = df['sent'].max()
        jitter = ((max_sent - min_sent) / avg_sent) * 100 if avg_sent != 0 else 0

        total_time = df['time'].sum()
        total_messages = df['sent'].sum()
        avg_time_us = (total_time / total_messages) * 1e6 if total_messages != 0 else np.nan

        diff_series = df['sent'] - df['received']
        avg_diff = diff_series.mean()
        min_diff = diff_series.min()
        max_diff = diff_series.max()

        summary_list.append({
            'message_size': size,
            'rtos': rtos,
            'avg_sent': avg_sent,
            'min_sent': min_sent,
            'max_sent': max_sent,
            'jitter_%': jitter,
            'avg_time_us': avg_time_us,
            'avg_diff': avg_diff,
            'min_diff': min_diff,
            'max_diff': max_diff
        })

    summary_df = pd.DataFrame(summary_list)
    summary_df = summary_df.sort_values(by='message_size').reset_index(drop=True)
    
    os.makedirs("plot", exist_ok=True)

    # Plot 1: Throughput vs. Time for Each Test File
    for (size, rtos), df in results.items():
        plt.figure(figsize=(10, 6))
        plt.plot(df['time'], df['sent'], marker='o', label='Messages Sent')
        plt.plot(df['time'], df['received'], marker='x', label='Messages Received')
        plt.xlabel("Time (sec)")
        plt.ylabel("Message Count")
        plt.title(f"{rtos.capitalize()} - {size*4} Bytes Queue Throughput Over Time")
        plt.legend()
        plt.grid(True)
        ax = plt.gca()
        set_custom_formatter(ax)
        plt.tight_layout()
        plt.savefig(f"plot/{size}_{rtos}_throughput_over_time.png", dpi=300)
        plt.close()

    # Plot 2: Comparison of Average Throughput Among RTOS for Each Message Size
    pivot_avg = summary_df.pivot(index='message_size', columns='rtos', values='avg_sent').sort_index()
    ax = pivot_avg.plot(kind='bar', figsize=(10, 6))
    # Check the pivot index to ensure it matches expectations
    print("Pivot index:", pivot_avg.index)
    # Set custom x-axis tick labels to 2, 4, 8, 16, 32
    ax.set_xticks(range(len(pivot_avg.index)))
    ax.set_xticklabels([2, 4, 8, 16, 32])
    ax.set_xlabel("Message Size (x4 Bytes)")
    ax.set_ylabel("Average Messages Sent&Recv in Period")
    ax.set_title("Average Throughput Comparison per Message Size Category")
    ax.grid(axis='y')
    plt.tight_layout()
    plt.savefig("plot/avg_throughput_comparison.png", dpi=300)
    plt.close()

    # Plot 3: Function Plot: Message Size vs. Throughput for Each RTOS
    plt.figure(figsize=(10, 6))
    rtos_list = summary_df['rtos'].unique()
    for rtos in rtos_list:
        df_rtos = summary_df[summary_df['rtos'] == rtos].sort_values('message_size')
        sizes_bytes = df_rtos['message_size'] * 4
        plt.plot(sizes_bytes, df_rtos['avg_sent'], marker='o', label=rtos.capitalize())
    plt.xlabel("Message Size (Bytes)")
    plt.ylabel("Average Messages Sent in Period")
    plt.title("Impact of Message Size on Throughput")
    plt.legend()
    plt.grid(True)
    ax = plt.gca()
    set_custom_formatter(ax)
    plt.tight_layout()
    plt.savefig("plot/message_size_vs_throughput.png", dpi=300)
    plt.close()

    # Plot 4: Jitter vs. Message Size for Each RTOS
    plt.figure(figsize=(10, 6))
    for rtos in rtos_list:
        df_rtos = summary_df[summary_df['rtos'] == rtos].sort_values('message_size')
        sizes_bytes = df_rtos['message_size'] * 4
        plt.plot(sizes_bytes, df_rtos['jitter_%'], marker='o', label=rtos.capitalize())
    plt.xlabel("Message Size (Bytes)")
    plt.ylabel("Jitter (%)")
    plt.title("Jitter of Throughput vs. Message Size")
    plt.legend()
    plt.grid(True)
    ax = plt.gca()
    set_custom_formatter(ax)
    plt.tight_layout()
    plt.savefig("plot/jitter_vs_message_size.png", dpi=300)
    plt.close()

    # Plot 5: Combined Difference (Sent - Received) vs. Time for Each Message Size (up to 300 sec)
    unique_sizes = sorted(set([key[0] for key in results.keys()]))
    for size in unique_sizes:
        plt.figure(figsize=(10, 6))
        for (s, rtos), df in results.items():
            if s == size:
                diff_series = df['sent'] - df['received']
                plt.plot(df['time'], diff_series, marker='o', label=rtos.capitalize())
        plt.xlabel("Time (sec)")
        plt.ylabel("Difference in Messages Send/Received")
        plt.title(f"{size*4} Bytes Queue: Difference in Send/Receive Over Time (All RTOS)")
        plt.xlim(0, 300)  # Limit x-axis to a maximum of 300 seconds
        plt.legend()
        plt.grid(True)
        ax = plt.gca()
        set_custom_formatter(ax)
        plt.tight_layout()
        plt.savefig(f"plot/{size}_diff_over_time_comparison.png", dpi=300)
        plt.close()

    output_summary(summary_df)
    print("Summary Statistics:")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    main()
