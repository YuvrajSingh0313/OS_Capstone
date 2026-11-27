#!/usr/bin/env python3
"""OS Resource-Management Simulator - integrated Python + Bash capstone.

Usage:  python main.py            interactive menu
        python main.py --demo     run every module on the sample data
"""
import os
import platform
import shutil
import sys

from modules import analysis, deadlock, memory, scheduler, storage
from modules import reporting as rpt
from modules.utils import (BASE, DATA_DIR, LOG_FILE, ValidationError, int_list,
                           load_json, load_kv, logger, run_bash, to_int)

DEMO = "--demo" in sys.argv
P = lambda *a: print(*a)
HR = "=" * 72


def header(title):
    P(f"\n{HR}\n  {title}\n{HR}")


def ask(prompt, default=None):
    if DEMO:
        return default
    val = input(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
    return val if val else default


def pause():
    if not DEMO:
        input("\nPress Enter to continue...")


def use_sample(what):
    return (ask(f"Use sample {what}? (y/n)", "y") or "y").lower().startswith("y")


# ------------------------------------------------------------------ 1
def get_processes():
    if use_sample("process data"):
        return scheduler.load_processes(os.path.join(DATA_DIR, "processes.csv"))
    P("Enter processes as: pid arrival burst priority   (blank line to finish)")
    procs = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        try:
            f = line.split()
            procs.append(scheduler.make_process(*f[:4]))
        except (ValidationError, TypeError) as exc:
            P(f"  ! {exc}")
    return scheduler.validate_processes(procs)


def menu_scheduling():
    header("MODULE 1 - PROCESS SCHEDULING")
    procs = get_processes()
    q = to_int(ask("Time quantum for Round Robin", 3), "time quantum", 1)
    P("\nInput processes:")
    P(rpt.table(["PID", "Arrival", "Burst", "Priority"], [[p.pid, p.arrival, p.burst, p.priority] for p in procs]))
    for res in scheduler.run_all(procs, q):
        P(f"\n--- {res['name']} ---")
        P(rpt.gantt_text(res["gantt"]))
        P(rpt.table(["PID", "AT", "BT", "CT", "TAT", "WT", "RT"],
                    [[r["pid"], r["arrival"], r["burst"], r["completion"], r["tat"], r["wt"], r["rt"]]
                     for r in res["rows"]]))
        P(f"Avg WT={res['avg_wt']:.2f}  Avg TAT={res['avg_tat']:.2f}  Avg RT={res['avg_rt']:.2f}  "
          f"CPU util={res['cpu_util']:.1f}%  Throughput={res['throughput']:.3f}/unit")


# ------------------------------------------------------------------ 2
def get_memory_data():
    if use_sample("memory data"):
        d = load_kv(os.path.join(DATA_DIR, "memory.txt"))
        return (int_list(d["reference"], "reference", 0), to_int(d["frames"], "frames", 1),
                int_list(d["blocks"], "blocks", 1), int_list(d["requests"], "requests", 1))
    ref = int_list(input("Page reference string (e.g. 7 0 1 2 0 3): "), "reference", 0)
    frames = to_int(input("Number of frames: "), "frames", 1, 64)
    blocks = int_list(input("Memory block sizes (e.g. 100 500 200): "), "blocks", 1)
    reqs = int_list(input("Process memory requests (e.g. 212 417): "), "requests", 1)
    return ref, frames, blocks, reqs


def menu_memory():
    header("MODULE 2 - MEMORY MANAGEMENT")
    ref, frames, blocks, reqs = get_memory_data()
    P(f"Reference string: {ref}\nFrames: {frames}")
    for res in memory.compare_page_algorithms(ref, frames):
        P(f"\n--- {res['name']} ---")
        P(rpt.table(["Step", "Page", "Frames", "Result"],
                    [[i + 1, pg, " ".join(map(str, fr)), st] for i, (pg, fr, st) in enumerate(res["trace"])]))
        P(f"Faults={res['faults']}  Hits={res['hits']}  Hit ratio={100 * res['hit_ratio']:.1f}%")
    P(f"\nContiguous allocation  blocks={blocks}  requests={reqs}")
    rows = []
    for s in ("first", "best", "worst"):
        a = memory.allocate(blocks, reqs, s)
        place = ", ".join(f"{r}->{'B' + str(b + 1) if b is not None else 'WAIT'}" for r, b in a["placed"])
        rows.append([a["name"], place, a["internal_fragmentation"], len(a["unplaced"])])
    P(rpt.table(["Strategy", "Placement", "Internal frag.", "Unplaced"], rows))


# ------------------------------------------------------------------ 3
def get_banker():
    if use_sample("Banker's data"):
        return load_json(os.path.join(DATA_DIR, "banker.json"))
    n = to_int(input("Number of processes: "), "processes", 1, 20)
    m = to_int(input("Number of resource types: "), "resources", 1, 10)
    avail = int_list(input(f"Available ({m} values): "), "available", 0)
    mx = [int_list(input(f"Max for P{i}: "), "max", 0) for i in range(n)]
    al = [int_list(input(f"Allocation for P{i}: "), "allocation", 0) for i in range(n)]
    return {"available": avail, "max": mx, "allocation": al, "request": None, "wait_for": {}}


def menu_deadlock():
    header("MODULE 3 - DEADLOCK HANDLING (Banker's Algorithm)")
    d = get_banker()
    av, mx, al = d["available"], d["max"], d["allocation"]
    need = deadlock.need_matrix(mx, al)
    n = len(mx)
    P(rpt.table(["Proc", "Max", "Alloc", "Need"], [[f"P{i}", mx[i], al[i], need[i]] for i in range(n)]))
    P(f"Available: {av}")
    safe, seq, steps = deadlock.is_safe(av, mx, al)
    for s in steps:
        P("  " + s)
    P(f"=> System is {'SAFE' if safe else 'UNSAFE'}" + (f"; safe sequence: {' -> '.join(seq)}" if safe else ""))
    req = d.get("request")
    if req:
        granted, msg, _ = deadlock.request_resources(req["pid"], req["amount"], av, mx, al)
        P(f"\nRequest P{req['pid']} {req['amount']}: {msg}")
    bad = deadlock.request_resources(0, [0, 2, 0] if len(av) == 3 else [99] * len(av), av, mx, al)
    P(f"Test request P0 [0, 2, 0]: {bad[1]}")
    wf = d.get("wait_for")
    if wf:
        cyc = deadlock.detect_cycle(wf)
        P(f"\nWait-for graph {wf}\n=> " + (f"DEADLOCK cycle: {' -> '.join(cyc)}" if cyc else "no deadlock"))


# ------------------------------------------------------------------ 4
def menu_storage():
    header("MODULE 4 - STORAGE MANAGEMENT (Disk Scheduling)")
    if use_sample("disk data"):
        d = load_kv(os.path.join(DATA_DIR, "disk.txt"))
        head, mc = to_int(d["head"], "head", 0), to_int(d["max_cylinder"], "max cylinder", 1)
        reqs, direction = int_list(d["requests"], "requests", 0), d["direction"]
    else:
        mc = to_int(input("Max cylinder (e.g. 199): "), "max cylinder", 1)
        head = to_int(input("Initial head position: "), "head", 0, mc)
        reqs = int_list(input("Request queue: "), "requests", 0, mc)
        direction = input("Direction (up/down): ").strip().lower()
    P(f"Head={head}  Requests={reqs}  Cylinders=0..{mc}  Direction={direction}")
    results = storage.run_all(head, reqs, mc, direction)
    for r in results:
        P(f"\n{r['name']:7s} path: {' -> '.join(map(str, r['path']))}")
        P(f"        total movement = {r['total']}   avg seek = {r['avg_seek']:.2f}")


# ------------------------------------------------------------------ 5
def menu_analysis():
    header("MODULE 5 - ANALYSIS & COMPARISON (tables, CSV, charts)")
    procs = scheduler.load_processes(os.path.join(DATA_DIR, "processes.csv"))
    _, h, rows, obs = analysis.scheduling_analysis(procs, 3)
    P("CPU scheduling comparison:"); P(rpt.table(h, rows)); [P(" *", o) for o in obs]
    m = load_kv(os.path.join(DATA_DIR, "memory.txt"))
    _, sweep, h, rows, obs = analysis.memory_analysis(int_list(m["reference"], "reference", 0), to_int(m["frames"], "frames", 1))
    P("\nPage replacement comparison:"); P(rpt.table(h, rows)); [P(" *", o) for o in obs]
    P("Belady sweep (frames 3,4,5):", sweep)
    d = load_kv(os.path.join(DATA_DIR, "disk.txt"))
    _, h, rows, obs = analysis.disk_analysis(to_int(d["head"], "head", 0), int_list(d["requests"], "requests", 0),
                                             to_int(d["max_cylinder"], "max", 1), d["direction"])
    P("\nDisk scheduling comparison:"); P(rpt.table(h, rows)); [P(" *", o) for o in obs]
    P(f"\nCharts saved in {os.path.join('outputs', 'charts')}/  |  CSV files in outputs/csv/")


# ------------------------------------------------------------------ 6-8 (Bash)
def python_sysinfo():
    P(f"Host: {platform.node()}\nOS: {platform.system()} {platform.release()}\nCPU cores: {os.cpu_count()}")
    t, u, f = shutil.disk_usage(BASE)
    P(f"Disk: total {t // 2**30} GB, free {f // 2**30} GB")


def menu_sysinfo():
    header("MODULE 6 - SYSTEM INFORMATION (Bash integration: bash/sysinfo.sh)")
    res = run_bash("sysinfo.sh")
    if res and res[0] == 0:
        P(res[1])
    else:
        P("[Bash unavailable - Python fallback]"); python_sysinfo()


def menu_logs():
    header("MODULE 7 - ACTIVITY LOG SUMMARY (Bash integration: bash/log_summary.sh)")
    res = run_bash("log_summary.sh", LOG_FILE)
    if res and res[0] == 0:
        P(res[1])
    elif os.path.isfile(LOG_FILE):
        P("[Bash unavailable - Python fallback]")
        P(f"Entries: {sum(1 for _ in open(LOG_FILE, encoding='utf-8'))}")
    else:
        P("No log entries yet.")


def menu_tests():
    header("MODULE 8 - TEST SUITE (Bash integration: bash/run_tests.sh)")
    res = run_bash("run_tests.sh")
    if res:
        P(res[1] or res[2])
    else:
        os.system(f'"{sys.executable}" -m unittest discover -s tests -v')


MENU = {
    "1": ("Process scheduling (FCFS, SJF, SRTF, Priority, RR)", menu_scheduling),
    "2": ("Memory management (FIFO, LRU, Optimal, fit strategies)", menu_memory),
    "3": ("Deadlock handling (Banker's + wait-for graph)", menu_deadlock),
    "4": ("Storage management (disk scheduling)", menu_storage),
    "5": ("Analysis & comparison (tables, CSV, charts)", menu_analysis),
    "6": ("System information [Bash]", menu_sysinfo),
    "7": ("Activity log summary [Bash]", menu_logs),
    "8": ("Run test suite [Bash]", menu_tests),
    "9": ("Run FULL demo (all modules, sample data)", None),
    "0": ("Exit", None),
}


def safe_run(fn):
    try:
        fn()
    except ValidationError as exc:
        P(f"\n[INPUT ERROR] {exc}")
        logger.error("Validation error: %s", exc)
    except (EOFError, KeyboardInterrupt):
        P("\nInput cancelled.")
    except Exception as exc:                      # last-resort guard
        P(f"\n[UNEXPECTED ERROR] {type(exc).__name__}: {exc}")
        logger.exception("Unexpected error")


def full_demo():
    global DEMO
    old, DEMO = DEMO, True
    for k in "123456":
        safe_run(MENU[k][1])
    safe_run(menu_logs)
    DEMO = old


def main():
    logger.info("=== Simulator started (demo=%s) ===", DEMO)
    if DEMO:
        full_demo()
        logger.info("=== Simulator finished ===")
        return
    while True:
        header("OS RESOURCE-MANAGEMENT SIMULATOR")
        for k, (label, _) in MENU.items():
            P(f"  {k}. {label}")
        choice = input("\nChoose an option: ").strip()
        if choice == "0":
            P("Goodbye!")
            break
        if choice == "9":
            full_demo()
        elif choice in MENU:
            safe_run(MENU[choice][1])
            pause()
        else:
            P("[INPUT ERROR] Please choose a number from the menu (0-9).")
            logger.warning("Invalid menu choice: %r", choice)
    logger.info("=== Simulator finished ===")


if __name__ == "__main__":
    main()
