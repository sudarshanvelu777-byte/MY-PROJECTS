"""
AI-Based Self-Healing Software - BEFORE vs AFTER Dashboard
--------------------------------------------------------------
Run directly in Python IDLE (press F5). Uses ONLY tkinter - no pip installs.

Two tabs, same Grafana-style gauges/charts as the reference image:

  TAB 1 - BEFORE (Existing System):
      Fixed rules / health probes only (slides 5-6 of the PPT).
      When a fault occurs the metric stays stuck high until a HUMAN
      clicks "Fix Manually" - there is no automatic diagnosis or repair.

  TAB 2 - AFTER (Proposed AI Self-Healing System):
      Runs the full Monitor -> Detect -> Diagnose -> Repair loop on its
      own (slides 2, 10, 11) with no human action needed.

A shared "Inject Fault" button fires the SAME fault into both tabs at the
same moment, and a comparison panel at the bottom tracks downtime /
recovery time for each side, so you can see the difference the AI layer
makes - this is the "Performance Evaluation" objective from slide 3.
"""

import tkinter as tk
from tkinter import ttk
import random
import time
from collections import deque

# ---------------------------------------------------------------- config --
HISTORY = 60
TICK_MS = 500

BG = "#15171c"
PANEL = "#1d2026"
GRID = "#2a2e37"
TEXT = "#d8dbe2"
MUTED = "#8b8f99"
GREEN = "#3fb950"
YELLOW = "#d29922"
RED = "#f85149"
BLUE = "#58a6ff"
PURPLE = "#bc8cff"

METRICS = ["CPU", "Memory", "Disk", "Network"]
METRIC_COLORS = {"CPU": GREEN, "Memory": YELLOW, "Disk": BLUE, "Network": PURPLE}


def arc_color(value):
    if value < 60:
        return GREEN
    if value < 85:
        return YELLOW
    return RED


# --------------------------------------------------------------- widgets --
class Gauge(tk.Canvas):
    def __init__(self, master, label, size=130, **kw):
        super().__init__(master, width=size, height=size, bg=PANEL,
                          highlightthickness=0, **kw)
        self.size, self.label, self.value, self.pad = size, label, 0.0, 12
        self._draw()

    def set_value(self, value):
        self.value = max(0.0, min(100.0, value))
        self._draw()

    def _draw(self):
        self.delete("all")
        s, p = self.size, self.pad
        self.create_arc(p, p, s - p, s - p, start=225, extent=-270,
                         style="arc", outline=GRID, width=11)
        extent = -270 * (self.value / 100.0)
        self.create_arc(p, p, s - p, s - p, start=225, extent=extent,
                         style="arc", outline=arc_color(self.value), width=11)
        self.create_text(s / 2, s / 2 - 5, text=f"{self.value:0.1f}%",
                          fill=TEXT, font=("Segoe UI", 13, "bold"))
        self.create_text(s / 2, s / 2 + 20, text=self.label,
                          fill=MUTED, font=("Segoe UI", 8))


class LineChart(tk.Canvas):
    def __init__(self, master, title, series_names, height=150, **kw):
        super().__init__(master, bg=PANEL, height=height,
                          highlightthickness=0, **kw)
        self.title = title
        self.series = {n: deque([0] * HISTORY, maxlen=HISTORY) for n in series_names}
        self.bind("<Configure>", lambda e: self._draw())

    def push(self, values: dict):
        for name, v in values.items():
            self.series[name].append(v)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 380
        h = self.winfo_height() or 150
        top, bottom, left, right = 24, h - 8, 8, w - 8
        for frac in (0, 0.25, 0.5, 0.75, 1.0):
            y = bottom - frac * (bottom - top)
            self.create_line(left, y, right, y, fill=GRID)
        self.create_text(left, 9, anchor="w", fill=TEXT,
                          font=("Segoe UI", 9, "bold"), text=self.title)
        n = HISTORY
        for i, (name, dq) in enumerate(self.series.items()):
            color = METRIC_COLORS.get(name, BLUE)
            pts = []
            for idx, val in enumerate(dq):
                x = left + (right - left) * idx / (n - 1)
                y = bottom - (bottom - top) * (max(0, min(100, val)) / 100.0)
                pts += [x, y]
            if len(pts) >= 4:
                self.create_line(*pts, fill=color, width=2, smooth=True)
            self.create_text(right - 65 * (len(self.series) - i), 9, anchor="w",
                              fill=color, font=("Segoe UI", 8), text=name)


# ------------------------------------------------------------ one system --
class SystemPanel(tk.Frame):
    """One monitored system. mode='manual' needs a human click to recover;
    mode='auto' runs the full AI Monitor-Detect-Diagnose-Repair loop itself."""

    STAGE_COLORS = {"MONITOR": GREEN, "DETECT": YELLOW, "DIAGNOSE": BLUE,
                     "REPAIR": PURPLE, "STUCK": RED}

    def __init__(self, master, mode, subtitle):
        super().__init__(master, bg=BG)
        self.mode = mode
        self.metric_value = {m: random.uniform(15, 35) for m in METRICS}
        self.baseline = dict(self.metric_value)
        self.fault = None
        self.stage = "MONITOR"
        self.stage_started_at = time.time()
        self.stats = {"faults": 0, "recoveries": [], "false_actions": 0,
                      "detection_delays": []}
        self._build_ui(subtitle)

    def _build_ui(self, subtitle):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", pady=(6, 4))
        tk.Label(head, text=subtitle, bg=BG, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        self.stage_label = tk.Label(head, text="MONITOR", bg=GREEN, fg="#0b0f14",
                                     font=("Segoe UI", 10, "bold"), padx=10, pady=3)
        self.stage_label.pack(side="right")

        if self.mode == "manual":
            self.fix_btn = tk.Button(head, text="Fix Manually", bg="#2d333b",
                                      fg=TEXT, relief="flat", padx=8, pady=3,
                                      state="disabled", command=self._manual_fix)
            self.fix_btn.pack(side="right", padx=8)

        gauge_row = tk.Frame(self, bg=BG)
        gauge_row.pack(fill="x")
        self.gauges = {}
        for name in METRICS:
            g = Gauge(gauge_row, name)
            g.pack(side="left", padx=6, pady=4)
            self.gauges[name] = g

        chart_row = tk.Frame(self, bg=BG)
        chart_row.pack(fill="both", expand=True, pady=6)
        c1 = LineChart(chart_row, "CPU / Network", ["CPU", "Network"])
        c1.pack(side="left", fill="both", expand=True, padx=(0, 4))
        c2 = LineChart(chart_row, "Memory / Disk", ["Memory", "Disk"])
        c2.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.charts = [c1, c2]

        bottom = tk.Frame(self, bg=PANEL)
        bottom.pack(fill="x", pady=(0, 6))
        self.stats_label = tk.Label(bottom, text="", justify="left", bg=PANEL,
                                     fg=MUTED, font=("Consolas", 9), padx=10, pady=6)
        self.stats_label.pack(anchor="w")

        log_frame = tk.Frame(self, bg=PANEL)
        log_frame.pack(fill="both", expand=False)
        self.log_box = tk.Text(log_frame, height=6, bg="#0f1115", fg=TEXT,
                                insertbackground=TEXT, relief="flat",
                                font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True, padx=8, pady=6)
        self.log_box.configure(state="disabled")
        self._refresh_stats()

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _refresh_stats(self):
        s = self.stats
        avg_rec = sum(s["recoveries"]) / len(s["recoveries"]) if s["recoveries"] else 0
        avg_delay = sum(s["detection_delays"]) / len(s["detection_delays"]) if s["detection_delays"] else 0
        extra = f"Detection delay avg : {avg_delay:0.1f}s\n" if self.mode == "auto" else \
                "Detection delay avg : n/a (no detector)\n"
        self.stats_label.configure(text=(
            f"Faults seen         : {s['faults']}\n"
            f"{extra}"
            f"Avg recovery time   : {avg_rec:0.1f}s\n"
            f"False actions       : {s['false_actions']}"
        ))

    # ---- fault lifecycle -------------------------------------------------
    def inject_fault(self, metric, severity):
        if self.fault:
            return  # already mid-incident
        self.fault = {"metric": metric, "severity": severity, "started": time.time(),
                      "detected_at": None}
        self.stats["faults"] += 1
        self.stage_started_at = time.time()
        if self.mode == "manual":
            self.stage = "STUCK"
            self._log(f"FAULT on {metric} - no automatic detector. "
                      f"System will stay degraded until a human intervenes.")
            self.fix_btn.configure(state="normal")
        else:
            self.stage = "MONITOR"
            self._log(f"FAULT on {metric} - AI monitor watching for anomaly.")
        self._set_stage(self.stage)

    def _manual_fix(self):
        if not self.fault:
            return
        downtime = time.time() - self.fault["started"]
        self.stats["recoveries"].append(downtime)
        self._log(f"OPERATOR manually restarted the {self.fault['metric']} component "
                  f"(system was degraded for {downtime:0.1f}s).")
        self.fault = None
        self.fix_btn.configure(state="disabled")
        self._set_stage("MONITOR")
        self._refresh_stats()

    def _set_stage(self, stage):
        self.stage = stage
        self.stage_label.configure(text=stage, bg=self.STAGE_COLORS[stage])

    # ---- per-tick updates --------------------------------------------------
    def tick(self):
        self._update_metrics()
        if self.mode == "auto":
            self._run_auto_cycle()
        for name, val in self.metric_value.items():
            self.gauges[name].set_value(val)
        self.charts[0].push({"CPU": self.metric_value["CPU"], "Network": self.metric_value["Network"]})
        self.charts[1].push({"Memory": self.metric_value["Memory"], "Disk": self.metric_value["Disk"]})
        self._refresh_stats()

    def _update_metrics(self):
        for name in METRICS:
            base = self.baseline[name]
            current = self.metric_value[name]
            healing = self.mode == "auto" and self.fault and self.fault["metric"] == name and self.stage == "REPAIR"
            if self.fault and self.fault["metric"] == name and not healing:
                target = base + self.fault["severity"]     # stuck high (manual) or not-yet-repaired (auto)
            else:
                target = base
            drift = random.uniform(-2, 2)
            current += (target - current) * 0.25 + drift
            self.metric_value[name] = max(1.0, min(99.0, current))

    def _run_auto_cycle(self):
        if not self.fault:
            self._set_stage("MONITOR")
            return
        elapsed = time.time() - self.stage_started_at
        metric = self.fault["metric"]
        value = self.metric_value[metric]

        if self.stage == "MONITOR":
            if value > self.baseline[metric] + 20:
                self.fault["detected_at"] = time.time()
                delay = self.fault["detected_at"] - self.fault["started"]
                self.stats["detection_delays"].append(delay)
                self._log(f"ANOMALY DETECTED on {metric} (delay {delay:0.1f}s).")
                self._set_stage("DETECT")

        elif self.stage == "DETECT" and elapsed > 1.0:
            if random.random() < 0.12:
                self.stats["false_actions"] += 1
                self._log("Diagnosis uncertain - re-checking evidence.")
                self.stage_started_at = time.time()
                return
            self._log(f"ROOT CAUSE found for {metric}; validated fix queued.")
            self._set_stage("DIAGNOSE")

        elif self.stage == "DIAGNOSE" and elapsed > 1.0:
            self._log(f"Repair tested in sandbox, rolling out to {metric}.")
            self._set_stage("REPAIR")

        elif self.stage == "REPAIR":
            if abs(value - self.baseline[metric]) < 4:
                recovery = time.time() - self.fault["started"]
                self.stats["recoveries"].append(recovery)
                self._log(f"RECOVERED automatically in {recovery:0.1f}s, no human action.")
                self.fault = None
                self._set_stage("MONITOR")


# --------------------------------------------------------------- app ------
class BeforeAfterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Self-Healing Software - Before vs After AI")
        self.configure(bg=BG)
        self.geometry("1200x780")

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(top, text="Machine Learning-Based Self-Healing Software - Before vs After",
                 bg=BG, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Button(top, text="Inject Fault Into Both", bg="#2d333b", fg=TEXT,
                  relief="flat", padx=10, pady=4,
                  command=self._inject_both).pack(side="right")

        notebook = ttk.Notebook(self)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(14, 6))
        style.map("TNotebook.Tab", background=[("selected", "#2d333b")])
        notebook.pack(fill="both", expand=True, padx=12, pady=8)

        self.before = SystemPanel(notebook, "manual",
                                   "BEFORE: Existing System (fixed rules + manual restart)")
        self.after_panel = SystemPanel(notebook, "auto",
                                        "AFTER: Proposed AI Self-Healing System")
        notebook.add(self.before, text="BEFORE  (Manual Recovery)")
        notebook.add(self.after_panel, text="AFTER  (AI Self-Healing)")

        compare = tk.Frame(self, bg=PANEL)
        compare.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(compare, text="Comparison", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.compare_label = tk.Label(compare, text="", bg=PANEL, fg=MUTED,
                                       font=("Consolas", 9), justify="left", padx=10, pady=6)
        self.compare_label.pack(anchor="w")

        self.after(TICK_MS, self._tick)

    def _inject_both(self):
        metric = random.choice(METRICS)
        severity = random.uniform(40, 65)
        self.before.inject_fault(metric, severity)
        self.after_panel.inject_fault(metric, severity)

    def _tick(self):
        self.before.tick()
        self.after_panel.tick()

        # random spontaneous faults, same event hits both sides for a fair comparison
        if not self.before.fault and not self.after_panel.fault and random.random() < 0.04:
            self._inject_both()

        b_avg = (sum(self.before.stats["recoveries"]) / len(self.before.stats["recoveries"])
                 if self.before.stats["recoveries"] else 0)
        a_avg = (sum(self.after_panel.stats["recoveries"]) / len(self.after_panel.stats["recoveries"])
                 if self.after_panel.stats["recoveries"] else 0)
        self.compare_label.configure(text=(
            f"BEFORE (manual) avg recovery time : {b_avg:0.1f}s   |   "
            f"AFTER (AI self-healing) avg recovery time : {a_avg:0.1f}s   |   "
            f"Recovery still pending in BEFORE tab until you click 'Fix Manually'."
        ))
        self.after(TICK_MS, self._tick)


if __name__ == "__main__":
    app = BeforeAfterApp()
    app.mainloop()
