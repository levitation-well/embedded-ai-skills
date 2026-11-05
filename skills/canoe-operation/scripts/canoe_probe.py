"""Read-only probe of a running CANoe instance: version, configuration, test environments and modules.

Usage: python -I canoe_probe.py
Does not open a configuration and does not start the measurement.
"""
import win32com.client as w
from win32com.client import gencache


def main():
    app = gencache.EnsureDispatch("CANoe.Application")
    print("CANoe version:", app.Version.major, app.Version.minor, app.Version.Build)
    print("configuration:", app.Configuration.FullName)
    print("measurement running:", app.Measurement.Running)
    envs = app.Configuration.TestSetup.TestEnvironments
    for i in range(1, envs.Count + 1):
        env = w.CastTo(envs.Item(i), "ITestEnvironment2")
        print(f"test environment [{i}]: {env.Name}")
        mods = w.CastTo(env.TestModules, "ITestModules2")
        for j in range(1, mods.Count + 1):
            print("  test module:", mods.Item(j).Name)
        testers = mods.LinSlaveConformanceTesters
        for k in range(1, testers.Count + 1):
            t = w.CastTo(testers.Item(k), "ILinSlaveConformanceTester3")
            print("  LIN slave conformance tester:", t.Name, "| spec:", t.FullName)
            s = t.IUTSettings
            print("    IUTSettings:", {p: getattr(s, p) for p in type(s)._prop_map_get_ if p not in ("Application", "Parent")})
            i_s = t.IUTInitializationSettings
            print("    IUTInitializationSettings:", {p: getattr(i_s, p) for p in type(i_s)._prop_map_get_ if p not in ("Application", "Parent")})


if __name__ == "__main__":
    main()
