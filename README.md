# OS Resource-Management Simulator (Python + Bash)

**Capstone:** integrated simulator of major operating-system resource-management functions with analytical results.
**Student:** Akshita Kumari (2401010209)

One application, one menu. Python implements the algorithms; Bash scripts are called from the menu for
system information, log analysis and test execution.

## Modules
| # | Module | Algorithms / features |
|---|--------|-----------------------|
| 1 | Process scheduling | FCFS, SJF, SRTF, Priority, Round Robin; Gantt, CT/TAT/WT/RT, CPU util, throughput |
| 2 | Memory management | FIFO, LRU, Optimal page replacement (step trace); First/Best/Worst-fit allocation |
| 3 | Deadlock handling | Banker's safety + resource-request algorithm; wait-for-graph cycle detection |
| 4 | Storage management | FCFS, SSTF, SCAN, C-SCAN, LOOK disk scheduling |
| 5 | Reporting / analysis | Comparison tables, CSV export, labelled charts (incl. Belady's anomaly), observations |
| 6-8 | Bash integration | `sysinfo.sh`, `log_summary.sh`, `run_tests.sh` (+ `cleanup.sh`, `run.sh`) |

## Requirements
Python 3.8+, `matplotlib` (`pip install -r requirements.txt`). Bash: Linux/macOS, or **Git Bash / WSL on Windows**.
If Bash is missing the program prints a warning and uses a Python fallback, so it never crashes.

## How to run
```bash
pip install -r requirements.txt
./run.sh              # interactive menu  (Windows without Bash: python main.py)
./run.sh --demo       # runs every module on the sample data, non-interactive
python main.py --demo > outputs/sample_run_trace.txt   # regenerate the output trace
bash bash/run_tests.sh                                  # 47 unit tests
```
Menu: choose 1-9. For modules 1-4 answer `y` to use the sample file or `n` to type your own data.

## Project structure
```
main.py                 menu + orchestration, error handling
modules/scheduler.py    module 1        modules/memory.py     module 2
modules/deadlock.py     module 3        modules/storage.py    module 4
modules/reporting.py    tables/CSV/charts   modules/analysis.py   comparisons
modules/utils.py        validation, logging, file loaders, Bash bridge
bash/*.sh               sysinfo, log_summary, run_tests, cleanup;  run.sh launcher
data/                   processes.csv  memory.txt  banker.json  disk.txt   (sample inputs)
tests/test_all.py       47 test cases (valid / invalid / boundary)
outputs/                sample_run_trace.txt, invalid_input_trace.txt, test_results.txt, charts/, csv/
logs/activity.log       activity log (every run, error and warning)
screenshots/            terminal screenshots
```

## Sample input formats
- `processes.csv`: `pid,arrival,burst,priority` (lower priority number = higher priority)
- `memory.txt`: `frames=3`, `reference=7,0,1,...`, `blocks=...`, `requests=...`
- `banker.json`: `available`, `max`, `allocation`, optional `request` and `wait_for`
- `disk.txt`: `head=53`, `max_cylinder=199`, `direction=up`, `requests=98,183,...`

## Validation, errors, logging
Every input is validated (`ValidationError`): negative/zero values, non-numbers, duplicates, empty lists,
out-of-range cylinders, bad matrix shapes, allocation > max, missing files. Errors are shown to the user and written
to `logs/activity.log` with a timestamp and level; the menu keeps running after any error.

## Key results on the sample data
| Area | Result |
|------|--------|
| Scheduling (avg waiting) | SRTF 6.60 < SJF 8.20 < Priority 10.60 < FCFS 11.40 < RR(q=3) 14.60 |
| Page faults (3 frames) | FIFO 15, LRU 12, Optimal 9 |
| Belady's anomaly | FIFO 9 faults (3 frames) -> 10 faults (4 frames) |
| Banker's | SAFE, sequence P1-P3-P4-P0-P2 |
| Disk head movement | SSTF 236 < LOOK 299 < SCAN 331 < C-SCAN 382 < FCFS 640 |
