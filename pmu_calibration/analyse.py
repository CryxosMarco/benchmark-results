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
