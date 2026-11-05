"""Drive the CANoe LIN Slave Conformance Tester through COM (CANoe 12).

Usage:
  python -I ct_com.py list
  python -I ct_com.py disable "PT-CT 24" "PT-CT 44" ...   (enables all others)
  python -I ct_com.py run <timeout_s>
"""
import sys
import time

import win32com.client as w
from win32com.client import gencache


def tester():
    app = gencache.EnsureDispatch("CANoe.Application")
    env = w.CastTo(app.Configuration.TestSetup.TestEnvironments.Item(1), "ITestEnvironment2")
    mods = w.CastTo(env.TestModules, "ITestModules2")
    return app, w.CastTo(mods.LinSlaveConformanceTesters.Item(1), "ILinSlaveConformanceTester3")


def cases(t):
    seq = t.Sequence
    for gi in range(1, seq.Count + 1):
        group = w.CastTo(seq.Item(gi), "ITestGroup")
        sub = group.Sequence
        for ci in range(1, sub.Count + 1):
            yield group, w.CastTo(sub.Item(ci), "ITestCase")


def cmd_list(t):
    on, off = [], []
    for group, case in cases(t):
        (on if case.Enabled and group.Enabled else off).append(case.Ident)
    print(f"enabled {len(on)}: {' '.join(on)}")
    print(f"disabled {len(off)}: {' '.join(off)}")


def cmd_disable(t, idents):
    wanted = set(idents)
    found = set()
    seq = t.Sequence
    for gi in range(1, seq.Count + 1):
        w.CastTo(seq.Item(gi), "ITestGroup").Enabled = True
    for _, case in cases(t):
        case.Enabled = case.Ident not in wanted
        if case.Ident in wanted:
            found.add(case.Ident)
    missing = wanted - found
    if missing:
        print("not found:", sorted(missing))
    cmd_list(t)


def cmd_run(app, t, timeout_s, disabled):
    if not app.Measurement.Running:
        app.Measurement.Start()
        for _ in range(100):
            if app.Measurement.Running:
                break
            time.sleep(0.2)
    print("measurement running:", app.Measurement.Running)
    time.sleep(2)
    if disabled:
        cmd_disable(t, disabled)
    t.Start()
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        time.sleep(10)
        done = sum(1 for _, c in cases(t) if c.Enabled and c.Verdict not in (0,))
        if done != last:
            print(f"{time.time() - t0:6.0f}s  cases with verdict: {done}  module verdict: {t.Verdict}", flush=True)
            last = done
        if not app.Measurement.Running:
            break
        try:
            if t.Verdict != 0 and done >= sum(1 for _, c in cases(t) if c.Enabled):
                break
        except Exception:
            pass
    print("finished; module verdict:", t.Verdict)


if __name__ == "__main__":
    app, t = tester()
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list(t)
    elif cmd == "disable":
        cmd_disable(t, sys.argv[2:])
    elif cmd == "run":
        cmd_run(app, t, float(sys.argv[2]), sys.argv[3:])
