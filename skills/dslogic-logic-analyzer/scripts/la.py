"""DSLogic 逻辑分析仪命令行（无界面）：采集走 logic-agent 自带的 dslab.exe，分析在本地做。
  python -I la.py devices
  python -I la.py capture --ch 1 [--ch 3] --rate 1M --dur 2s [--trig D1=F] [--vth 2.0] [--buffer] [--label x]
  python -I la.py lin    <运行目录|vcd> --ch 1 [--baud 19200] [--show 10]
  python -I la.py pulses <运行目录|vcd> --ch 1 [--at 5ms] [--span 2ms] [--max 40]
  python -I la.py decode <运行目录|vcd> -P "uart:rx=D1:baudrate=115200" [-A uart=rx-data]
每次最后一行是 RESULT: OK / RESULT: FAIL <原因>。运行目录默认在 captures 下，按时间命名。

路径配置（优先级从高到低）：环境变量 LOGIC_AGENT_RUNTIME / LA_CAPTURES，本目录的 la_config.json
（{"runtime": "...", "captures": "..."}，参考 la_config.example.json），默认值（captures = 当前目录下的 captures）。
runtime 是 logic-agent npm 包解压后的 package\\runtime 目录，里面有 bin\\dslab.exe 和 bin\\sigrok-cli.exe。
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import la_lin  # noqa: E402


def _config():
    cfg = {}
    p = os.path.join(HERE, "la_config.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
    runtime = os.environ.get("LOGIC_AGENT_RUNTIME") or cfg.get("runtime") or ""
    captures = os.environ.get("LA_CAPTURES") or cfg.get("captures") or os.path.join(os.getcwd(), "captures")
    return os.path.expandvars(runtime), os.path.expandvars(captures)


RUNTIME, CAPTURES = _config()
DSLAB = os.path.join(RUNTIME, "bin", "dslab.exe")
SIGROK = os.path.join(RUNTIME, "bin", "sigrok-cli.exe")
HOLDERS = ("DSView", "AllLogic")          # 会独占分析仪 USB 的程序


def fail(msg):
    print(f"RESULT: FAIL {msg}")
    sys.exit(1)


def num(s, unit_table):
    m = re.fullmatch(r"([\d.]+)\s*([a-zA-Z]*)", str(s).strip())
    if not m:
        fail(f"看不懂数值 {s}")
    k = m.group(2).lower().rstrip("hz") if unit_table is RATE else m.group(2).lower()
    if k not in unit_table:
        fail(f"看不懂单位 {s}")
    return float(m.group(1)) * unit_table[k]


RATE = {"": 1, "k": 1e3, "m": 1e6}
TIME = {"": 1, "s": 1, "ms": 1e-3, "us": 1e-6}


def env():
    return dict(os.environ, DSLAB_RES_DIR=os.path.join(RUNTIME, "bin", "res"),
                SIGROKDECODE_DIR=os.path.join(RUNTIME, "decoders"))


def check_holders():
    out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True).stdout
    busy = [h for h in HOLDERS if f'"{h}.exe"' in out]
    if busy:
        fail(f"{', '.join(busy)} 正开着并占着分析仪，先关掉（USB 同一时间只能给一个程序）")


def dslab(args, timeout=120):
    if not os.path.exists(DSLAB):
        fail(f"找不到 dslab.exe（{DSLAB}）：设环境变量 LOGIC_AGENT_RUNTIME 或写 la_config.json，见 tools.md 的安装一节")
    p = subprocess.run([DSLAB] + args, capture_output=True, text=True, env=env(), timeout=timeout)
    try:
        return json.loads(p.stdout), p
    except ValueError:
        fail(f"dslab 退出码 {p.returncode}: {(p.stdout + p.stderr).strip()[-600:]}")


def open_run(path):
    """接受运行目录或 vcd 路径，返回 (vcd, 采样率, 运行目录)。"""
    run = path if os.path.isdir(path) else os.path.dirname(path)
    vcd = os.path.join(path, "capture.vcd") if os.path.isdir(path) else path
    if not os.path.exists(vcd):
        fail(f"找不到 {vcd}")
    meta = os.path.join(run, "meta.json")
    rate = None
    if os.path.exists(meta):
        with open(meta, encoding="utf-8") as f:
            rate = json.load(f).get("sample_rate")
    return vcd, rate, run


def wave(vcd, rate, ch):
    names, init, edges, n = la_lin.load_vcd(vcd, rate)
    if str(ch) not in names:
        fail(f"VCD 里没有通道 {ch}，只有 {names}")
    c = names.index(str(ch))
    return la_lin.Wave(init[c], edges[c], rate), n


def cmd_devices(a):
    check_holders()
    d, _ = dslab(["devices", "--json"])
    for x in d.get("devices", []):
        print(f"[{x['index']}] {x['name']}")
    caps, _ = dslab(["capabilities", "--json"])
    print(f"通道 {caps.get('total_channels')}，采样率 {[int(r) for r in caps.get('samplerates', [])]}（当前模式），"
          f"默认阈值 {caps.get('vth')} V")
    print("RESULT: OK" if d.get("devices") else "RESULT: FAIL 没有找到 DSLogic（看 USB 线、驱动，DSView 能不能认）")


def cmd_capture(a):
    check_holders()
    rate = num(a.rate, RATE)
    samples = int(rate * num(a.dur, TIME))
    chs = sorted(set(a.ch))
    run = os.path.join(a.out or CAPTURES, time.strftime("%Y%m%d-%H%M%S") + (f"-{a.label}" if a.label else ""))
    args = ["capture", "once", "--channels", ",".join(f"D{c}" for c in chs), "--rate", str(int(rate)),
            "--samples", str(samples), "--vth", str(a.vth), "--out", run, "--json",
            "--timeout", str(int(a.timeout * 1000))]
    if not a.buffer:
        args.append("--stream")
    if a.trig:
        args += ["--trigger", a.trig, "--trigger-pos", str(a.trig_pos)]
    t = time.perf_counter()
    d, p = dslab(args, timeout=a.timeout + 30)
    dt = time.perf_counter() - t
    if not d.get("ok"):
        fail(f"dslab: {json.dumps(d, ensure_ascii=False)[:500]}")
    with open(os.path.join(run, "la_args.json"), "w", encoding="utf-8") as f:
        json.dump(dict(vars(a), func=None, dslab_args=args), f, ensure_ascii=False, indent=1)
    print(f"运行目录: {run}")
    print(f"采到 {d['sample_count']} 样本 @ {rate / 1e6:g} MHz（{d['sample_count'] / rate:.3f} s），"
          f"{'缓存' if a.buffer else '流'}模式，阈值 {a.vth} V，"
          f"触发 {a.trig or '无'}（{'已触发' if d.get('triggered') else '未触发'}），溢出 {d.get('overflow')}，用时 {dt:.1f} s")
    for c in chs:
        w, n = wave(d["vcd_path"], rate, c)
        if not w.e:
            print(f"  D{c}: 无翻转，一直是 {w.init}")
            continue
        ps = [x for x in w.pulses(0, n)[1:-1]]
        lo = [x[2] for x in ps if x[1] == 0] or [0]
        hi = [x[2] for x in ps if x[1] == 1] or [0]
        us = 1e6 / rate
        print(f"  D{c}: {len(w.e)} 次翻转，首个 {w.e[0] * us / 1e3:.3f} ms，末个 {w.e[-1] * us / 1e3:.3f} ms；"
              f"低电平 {min(lo) * us:.2f}–{max(lo) * us:.1f} us，高电平 {min(hi) * us:.2f}–{max(hi) * us:.1f} us")
    if d.get("overflow"):
        print("[注意] 流模式溢出：USB 带宽不够，降采样率或减通道")
    print("RESULT: OK" if d.get("triggered", True) else "RESULT: FAIL 等到超时也没触发")


def cmd_lin(a):
    vcd, rate, run = open_run(a.path)
    rate = rate or (a.rate and num(a.rate, RATE)) or fail("没有 meta.json，用 --rate 给采样率")
    w, _ = wave(vcd, rate, a.ch)
    frames = la_lin.decode_lin(w, rate, a.baud)
    for fr in frames[:a.show]:
        print(la_lin.fmt(fr))
    errs = [fr for fr in frames[a.show:] if la_lin.bad(fr)]
    for fr in errs[:20]:
        print(la_lin.fmt(fr))
    if len(frames) > a.show:
        print(f"...（只显示前 {a.show} 帧和后面的错误帧，全部在 TSV 里）")
    print("\n".join(la_lin.summary(frames, a.baud)))
    tsv = os.path.join(run, f"lin_D{a.ch}.tsv")
    la_lin.write_tsv(frames, tsv)
    print(f"逐帧日志: {tsv}")
    print("RESULT: OK" if frames else "RESULT: FAIL 没有解出 LIN 帧")


def cmd_pulses(a):
    vcd, rate, _ = open_run(a.path)
    rate = rate or (a.rate and num(a.rate, RATE)) or fail("没有 meta.json，用 --rate 给采样率")
    w, n = wave(vcd, rate, a.ch)
    us = 1e6 / rate
    s = int(num(a.at, TIME) * rate) if a.at else 0
    e = min(n, s + int(num(a.span, TIME) * rate)) if a.span else n
    ps = w.pulses(s, e)
    print(f"D{a.ch} 窗口 {s * us / 1e3:.3f}–{e * us / 1e3:.3f} ms，{len(ps)} 段电平（首尾两段被窗口截断）")
    for st, lv, wd in ps[:a.max]:
        print(f"  {st * us / 1e3:10.4f} ms  {'高' if lv else '低'}  {wd * us:10.2f} us")
    if len(ps) > a.max:
        print(f"  ...（还有 {len(ps) - a.max} 段，用 --at/--span 缩小窗口）")
    full = ps[1:-1]
    for lv, name in ((0, "低"), (1, "高")):
        ws = sorted(x[2] * us for x in full if x[1] == lv)
        if ws:
            print(f"{name}电平宽度  最小 {ws[0]:.2f} us  中位 {ws[len(ws) // 2]:.2f}  最大 {ws[-1]:.2f}  共 {len(ws)} 段")
    rises = [x[0] for x in full if x[1] == 1]
    if len(rises) >= 3:
        per = [(b - a_) * us for a_, b in zip(rises, rises[1:])]
        hi = [x[2] * us for x in full if x[1] == 1][:len(per)]
        mp = sum(per) / len(per)
        print(f"按上升沿算周期  均值 {mp:.3f} us（{1e6 / mp:.3f} Hz）  最小 {min(per):.3f}  最大 {max(per):.3f}  "
              f"占空比均值 {100 * sum(hi) / sum(per):.2f}%（周期不稳时只作参考）")
    print("RESULT: OK")


def cmd_decode(a):
    vcd, rate, _ = open_run(a.path)
    rate = rate or (a.rate and num(a.rate, RATE)) or fail("没有 meta.json，用 --rate 给采样率")
    # sigrok 读 dslab 的 VCD 时通道名是 logic.<n>，时间刻度 1 ns；降采样回实际采样率，快好几倍
    proto = re.sub(r"=D(\d+)", r"=logic.\1", a.P)
    cmd = [SIGROK, "-I", f"vcd:downsample={max(1, int(1e9 / rate))}", "-i", vcd, "-P", proto]
    if a.A:
        cmd += ["-A", a.A]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env(), timeout=300)
    lines = [x for x in p.stdout.splitlines() if x.strip()]
    for x in lines[:a.max]:
        print(x)
    if len(lines) > a.max:
        print(f"...（共 {len(lines)} 行，只显示前 {a.max} 行，用 --max 调整）")
    err = [x for x in p.stderr.splitlines() if "change rate" not in x and "downsample" not in x]
    if err:
        print("\n".join(err[-5:]))
    print("RESULT: OK" if p.returncode == 0 and lines else f"RESULT: FAIL sigrok-cli 退出码 {p.returncode}，输出 {len(lines)} 行")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("devices").set_defaults(func=cmd_devices)
    c = sp.add_parser("capture")
    c.add_argument("--ch", type=int, action="append", required=True, help="硬件通道号，可重复")
    c.add_argument("--rate", default="1M")
    c.add_argument("--dur", default="1s")
    c.add_argument("--vth", type=float, default=2.0, help="阈值 V；默认 2.0 适合 3.3/5 V 逻辑和 12 V 的 LIN 总线")
    c.add_argument("--trig", help="例如 D1=F（下降沿）、D1=R、D1=0；不给就立即开始")
    c.add_argument("--trig-pos", type=int, default=1, help="触发点在窗口里的百分比位置")
    c.add_argument("--buffer", action="store_true", help="缓存模式：最高 100 MHz，窗口短；默认流模式")
    c.add_argument("--timeout", type=float, default=30, help="等触发加采集的总时限 s")
    c.add_argument("--label")
    c.add_argument("--out")
    c.set_defaults(func=cmd_capture)
    for name, fn in (("lin", cmd_lin), ("pulses", cmd_pulses), ("decode", cmd_decode)):
        x = sp.add_parser(name)
        x.add_argument("path")
        x.add_argument("--rate", help="没有 meta.json 时用")
        x.set_defaults(func=fn)
        if name != "decode":
            x.add_argument("--ch", type=int, required=True)
        if name == "lin":
            x.add_argument("--baud", type=int, default=19200)
            x.add_argument("--show", type=int, default=10)
        if name == "pulses":
            x.add_argument("--at")
            x.add_argument("--span")
            x.add_argument("--max", type=int, default=40)
        if name == "decode":
            x.add_argument("-P", required=True, help='sigrok 解码器串，通道写 D<n>，例如 "uart:rx=D1:baudrate=19200,lin"')
            x.add_argument("-A", help="只输出某类注释，例如 lin 或 uart=rx-data")
            x.add_argument("--max", type=int, default=200)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
