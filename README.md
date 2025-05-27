# RTOS Benchmark Analysis

This repository contains benchmark test results and Python scripts for analyzing and visualizing performance data from different RTOS synchronization primitives.

## Contents

- `results` — Raw benchmark data in their respectivly named folders.
- `plot/` — Generated plots and summaries.
- Python scripts for parsing, analyzing, and plotting benchmark results.
- RTOS configuration references.

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt` (e.g. `pandas`, `matplotlib`, `numpy`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage
Copy over the outputs of the respective results. Overwrite the existing results or create a copy of that folder.
In the respective foolder run the analyse and plot syript thi script is folder sensitiv so you need to execute it from its one folder.

- python3 analyse_and_plot.py

## Future Work
Automating the parsing by using makefiles 

## Licence
Copyright (c) Marco Milenkovic 2024 IBV - Echtzeit- und Embedded GmbH & Co. KG
SPDX-License-Identifier: Apache-2.0

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation the 
rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software 
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN 
AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.