#!/usr/bin/env python3
# Copyright (c) 2024 Marco Milenkovic IBV - Echtzeit- und Embedded GmbH & Co. KG
#
# This file is part of the Performance Evaluation of 
# Synchronization and Context Switching in RTOS.
#
# Performance Evaluation of 
# Synchronization and Context Switching in RTOS
# is free software: you can redistribute it and/or modify
# it under the terms of the MIT License as published by
# the Massachusetts Institute of Technology.
#
# Performance Evaluation of 
# Synchronization and Context Switching in RTOS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the MIT License along with this file.
# If not, see <https://opensource.org/licenses/MIT>.

import os
import sys
import re
import statistics

DEBUG_LOG = "debug_log.txt"

def log_debug(message):
    """Append a debug message to the debug log file and print to console."""
    with open(DEBUG_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")
    print(message)

def parse_time_period_totals(file_path):
    """
    Parse 'Time Period Total' values from a given file using regex.
    Matches lines such as:
       "Time Period Total: 123"
       "time period total: 123.45"
    """
    totals = []
    pattern = re.compile(r"Time\s*Period\s*Total\s*:\s*([\d\.]+)", re.IGNORECASE)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                match = pattern.search(line)
                if match:
                    num_str = match.group(1)
                    try:
                        total_val = float(num_str)
                        totals.append(total_val)
                        log_debug(f"Matched in {file_path}: {total_val}")
                    except ValueError:
                        log_debug(f"Conversion error in {file_path} for '{num_str}'")
    except Exception as e:
        log_debug(f"Error reading {file_path}: {e}")
    return totals

def collect_test_results(folder_path, test_type_filter=None):
    """
    Recursively collect test results from .txt files in the specified folder.
    If test_type_filter is given, only files whose name contains that substring are processed.
    """
    results = []
    if not os.path.exists(folder_path):
        log_debug(f"Warning: Folder '{folder_path}' does not exist. Skipping.")
        return results

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if not filename.lower().endswith(".txt"):
                continue
            if test_type_filter and test_type_filter not in filename:
                continue
            file_path = os.path.join(root, filename)
            file_totals = parse_time_period_totals(file_path)
            if not file_totals:
                log_debug(f"DEBUG: No matches found in {file_path}")
            results.extend(file_totals)
    return results

def compute_statistics(results_dict):
    """
    Compute statistics for each key in results_dict.
    Each value in results_dict is a list of numbers.
    Returns a dictionary with the same keys mapping to a stats dictionary:
      - count, average, min, max, jitter, percentage
    The 'percentage' value is left as None (to be set later).
    """
    stats = {}
    for key, vals in results_dict.items():
        count = len(vals)
        if count == 0:
            stats[key] = {
                'count': 0,
                'average': 0,
                'min': 0,
                'max': 0,
                'jitter': 0,
                'percentage': 0
            }
        else:
            avg = statistics.mean(vals)
            val_min = min(vals)
            val_max = max(vals)
            jitter_raw = val_max - val_min
            jitter_percentage = (jitter_raw / avg) * 100 if avg != 0 else 0
            stats[key] = {
                'count': count,
                'average': avg,
                'min': val_min,
                'max': val_max,
                'jitter': jitter_percentage,
                'percentage': None  # to be set later
            }
    return stats

if __name__ == "__main__":
    # Clear previous debug log if exists
    if os.path.exists(DEBUG_LOG):
        os.remove(DEBUG_LOG)
    
    # We expect exactly 3 command-line arguments, one for each RTOS folder.
    if len(sys.argv) != 4:
        print("Usage: python Data_Analyser.py <folder_for_freeRTOS> <folder_for_threadX> <folder_for_zephyr>")
        print("Example: python Data_Analyser.py .\\freeRTOS\\optimized_for_latency_30sec .\\threadX\\optimized_30sec .\\zephyr\\default_30sec")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Define the base directory for the test results.
    # (You can change this if needed; it will be prepended to the folder args if they are relative.)
    base_dir = r"E:\IBV\PROJEKTE\MASTER_ARBEIT\WORKSPACE\Testergebnisse"

    # Map the three RTOS to their provided folder paths.
    rtos_list = ["freeRTOS", "threadX", "zephyr"]
    rtos_folders = {
        "freeRTOS": os.path.abspath(os.path.normpath(sys.argv[1])),
        "threadX": os.path.abspath(os.path.normpath(sys.argv[2])),
        "zephyr": os.path.abspath(os.path.normpath(sys.argv[3]))
    }
    
    # Define the list of test types (these should appear in the file names).
    test_type_list = [
        "basic_single_thread_processing_test",
        "interrupt_preemption_test",
        "cooperative_scheduling_test",
        "interrupt_processing_test",
        "memory_allocation_test",
        "message_processing_test",
        "mutex_processing_test",
        "preemptive_scheduling_test",
        "synchronization_processing_test"
    ]
    
    # Prepare a list to store the results (one row per (test_type, rtos))
    final_results = []
    
    # Process each test type
    for test_type in test_type_list:
        # For each test type, collect data for each RTOS.
        # We'll build a temporary dict to compute statistics relative across RTOS.
        rtos_results = {}
        for rtos in rtos_list:
            # Build the full folder path for this RTOS.
            # The provided folder (e.g. optimized_for_latency_30sec) is expected to contain the test files.
            folder_path = rtos_folders[rtos]
            log_debug(f"Collecting for test '{test_type}' from {rtos} folder: {folder_path}")
            data = collect_test_results(folder_path, test_type_filter=test_type)
            rtos_results[rtos] = data
        
        # Compute stats for this test type across all RTOS.
        stats = compute_statistics(rtos_results)
        
        # Determine the best (highest) average among the three (if any)
        valid_avgs = [s['average'] for s in stats.values() if s['average'] != 0]
        best_average = max(valid_avgs) if valid_avgs else 0
        for rtos in rtos_list:
            info = stats[rtos]
            if info['average'] != 0 and best_average != 0:
                info['percentage'] = (info['average'] / best_average) * 100
            else:
                info['percentage'] = 0
            
            # Round numeric values
            info['average'] = round(info['average'], 2)
            info['min'] = round(info['min'], 2)
            info['max'] = round(info['max'], 2)
            info['jitter'] = round(info['jitter'], 6)
            info['percentage'] = round(info['percentage'], 2)
            
            # Append the row: test_type, rtos, count, average, min, max, jitter, percentage
            final_results.append((test_type, rtos, info['count'], info['average'], info['min'], info['max'], info['jitter'], info['percentage']))
    
    # Write the CSV file with the original structure expected by the plotting script.
    output_file = os.path.join(os.getcwd(), "Test_Results.txt")
    try:
        with open(output_file, "w", encoding="utf-8") as out:
            out.write("test_type,rtos,count,average,min,max,jitter,percentage\n")
            for row in final_results:
                test_type, rtos, count, avg, min_val, max_val, jitter, perc = row
                out.write(f"{test_type},{rtos},{count},{avg},{min_val},{max_val},{jitter},{perc}\n")
    except Exception as e:
        log_debug(f"Error writing to output file: {e}")

    # Print summary to debug log
    log_debug("------------------------------------------------------------")
    log_debug("Comparison Results:")
    log_debug("------------------------------------------------------------")
    for row in final_results:
        test_type, rtos, count, avg, min_val, max_val, jitter, perc = row
        log_debug(f"Test Type: {test_type} (RTOS: {rtos})")
        log_debug(f"  Count: {count}, Average: {avg}, Min: {min_val}, Max: {max_val}, Jitter: {jitter}%, Percentage: {perc}%")
    log_debug(f"All results have been written to {output_file}")
    
    input("Press Enter to exit...")
