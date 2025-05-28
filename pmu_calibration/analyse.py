"""
MIT License

Copyright (c) 2024 Marco Milenkovic

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

import csv
import re
import statistics

# File names and their corresponding RTOS labels
files = {
    'freertos_pmu_calibaration.txt': 'FreeRTOS',
    'zephyr_pmu_calibaration.txt': 'Zephyr',
    'threadx_pmu_calibaration.txt': 'ThreadX'
}

# Regular expression to capture cycle counts
cycle_re = re.compile(r"Cycle Count:\s*(\d+)")

# Prepare output data
output_rows = []

for filename, rtos in files.items():
    with open(filename, 'r') as f:
        contents = f.read()
    
    # Extract all cycle counts
    counts = [int(m.group(1)) for m in cycle_re.finditer(contents)]
    
    # Compute statistics
    mean = statistics.mean(counts)
    stddev = statistics.pstdev(counts)
    
    # Store results
    output_rows.append({
        'RTOS': rtos,
        'Mean_Overhead_Cycles': f"{mean:.2f}",
        'StdDev_Overhead_Cycles': f"{stddev:.2f}"
    })

# Write to CSV
csv_filename = 'calibration_stats.csv'
with open(csv_filename, 'w', newline='') as csvfile:
    fieldnames = ['RTOS', 'Mean_Overhead_Cycles', 'StdDev_Overhead_Cycles']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

# Print summary
print(f"Calibration statistics written to {csv_filename}:")
for row in output_rows:
    print(f"{row['RTOS']}: Mean = {row['Mean_Overhead_Cycles']}, StdDev = {row['StdDev_Overhead_Cycles']}")
