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
import statistics

def parse_time_period_totals(file_path):
    """Parse 'Time Period Total' values from a given file."""
    totals = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("Time Period Total:"):
                parts = line.split(":")
                if len(parts) > 1:
                    total_str = parts[1].strip()
                    try:
                        total_val = int(total_str)
                        totals.append(total_val)
                    except ValueError:
                        pass
    return totals

def collect_test_results(base_dir, rtos_name, test_type_filter=None):
    """Collect test results from the specified RTOS folder."""
    results = []
    rtos_dir = os.path.join(base_dir, rtos_name, "default_30sec")
    if not os.path.exists(rtos_dir):
        return results  # empty list if not found

    for filename in os.listdir(rtos_dir):
        # Filter by test type if needed
        if test_type_filter and test_type_filter not in filename:
            continue
        
        file_path = os.path.join(rtos_dir, filename)
        if os.path.isfile(file_path) and file_path.endswith(".txt"):
            totals = parse_time_period_totals(file_path)
            results.extend(totals)
    return results

def compute_statistics(results_dict):
    """Compute average, jitter as a percentage of average, count, and percentage comparison."""
    stats = {}
    for rtos, vals in results_dict.items():
        count = len(vals)
        if count == 0:
            stats[rtos] = {
                'count': 0,
                'average': 0,
                'min': 0,
                'max': 0,
                'jitter': 0,  # Now represents jitter percentage
                'percentage': 0
            }
        else:
            avg = statistics.mean(vals)
            val_min = min(vals)
            val_max = max(vals)
            jitter_raw = val_max - val_min
            jitter_percentage = (jitter_raw / avg) * 100 if avg != 0 else 0
            stats[rtos] = {
                'count': count,
                'average': avg,
                'min': val_min,
                'max': val_max,
                'jitter': jitter_percentage,  # Store jitter as percentage
                'percentage': None
            }

    valid_averages = [info['average'] for info in stats.values() if info['average'] is not None]
    if len(valid_averages) == 0:
        # no data
        return stats

    # higher is better
    best_average = max(valid_averages)
    for rtos, info in stats.items():
        if info['average'] != 0:
            percentage = (info['average'] / best_average) * 100
            info['percentage'] = percentage
        else:
            info['percentage'] = 0

    # round all numeric values
    for rtos, info in stats.items():
        if info['average'] is not None:
            info['average'] = round(info['average'], 2)
        if info['min'] is not None:
            info['min'] = round(info['min'], 2)
        if info['max'] is not None:
            info['max'] = round(info['max'], 2)
        if info['jitter'] is not None:
            info['jitter'] = round(info['jitter'], 6) 
        if info['percentage'] is not None:
            info['percentage'] = round(info['percentage'], 2)

    return stats

if __name__ == "__main__":
    # Base directory
    base_dir = r"E:\IBV\PROJEKTE\MASTER_ARBEIT\WORKSPACE\Testergebnisse"

    # List of all tests
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

    # RTOS List
    rtos_list = ["freeRTOS", "threadX", "zephyr"]

    # Open output file
    output_file = os.path.join(base_dir, "Test_Results.txt")
    with open(output_file, "w", encoding="utf-8") as out:
        # Write CSV header
        out.write("test_type,rtos,count,average,min,max,jitter,percentage\n")

        for test_type in test_type_list:
            # Collect results
            rtos_results = {}
            for rtos in rtos_list:
                rtos_data = collect_test_results(base_dir, rtos, test_type_filter=test_type)
                rtos_results[rtos] = rtos_data

            # Compute stats
            stats = compute_statistics(rtos_results)

            # Print out on console
            print("------------------------------------------------------------")
            print(f"Results for Test Type: {test_type}")
            print("------------------------------------------------------------")
            for rtos, info in stats.items():
                print(f"RTOS: {rtos}")
                print(f"  Number of Measurements: {info['count']}")
                print(f"  Average: {info['average']}")
                print(f"  Min: {info['min']}")
                print(f"  Max: {info['max']}")
                print(f"  Jitter: {info['jitter']}")
                print(f"  Percentage (relative to best): {info['percentage']}")
                print()

                # Write results to file
                # Convert None to empty string for CSV
                def val_or_empty(v):
                    return str(v) if v is not None else ""

                out.write(f"{test_type},{rtos},{val_or_empty(info['count'])},{val_or_empty(info['average'])},{val_or_empty(info['min'])},{val_or_empty(info['max'])},{val_or_empty(info['jitter'])},{val_or_empty(info['percentage'])}\n")
    
    print(f"All results have been written to {output_file}")
