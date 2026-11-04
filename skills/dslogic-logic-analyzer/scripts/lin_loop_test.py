"""LIN 收发闭环测试：逻辑分析仪触发采集 → 图莫斯 USB2XXX 当主机发一批帧 → 解码 → 和发送清单逐帧比对。
用法: python -I lin_loop_test.py [--la-ch 1] [--lin-ch 0] [--rate 1M] [--dur 3s] [--buffer] [--repeat 5]
图莫斯 SDK 目录（含 USB2XXX.dll、libusb-1.0.dll）：环境变量 TOOMOSS_SDK，或 la_config.json 的 "toomoss_sdk"。
发帧前确认总线上从机不会响应这些 ID（看工程的 LDF），需要时用 --ids 换。
"""
import argparse, json, os, re, subprocess, sys, time
from ctypes import byref, c_ubyte, c_uint, windll

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import la_lin  # noqa: E402

# (ID, 数据, 校验类型 1=增强 0=经典)；数据为 None 表示只发帧头（主机读，没有从机应答）
PLAN = [
    (0x2A, [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88], 1),
    (0x2B, [0x00], 1),
    (0x2C, [0xFF, 0x00], 1),
    (0x10, [0x55, 0xAA, 0x0F, 0xF0], 1),
    (0x11, [0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03, 0x04], 0),
    (0x30, [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01], 1),
    (0x2D, None, 1),
]


def sdk_dir():
    d = os.environ.get("TOOMOSS_SDK")
    p = os.path.join(HERE, "la_config.json")
    if not d and os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            d = json.load(f).get("toomoss_sdk")
    d = os.path.expandvars(d or "")
    if not os.path.exists(os.path.join(d, "USB2XXX.dll")):
        sys.exit(f"RESULT: FAIL 找不到 USB2XXX.dll（{d}）：设 TOOMOSS_SDK 或 la_config.json 的 toomoss_sdk")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--la-ch", type=int, default=1, help="逻辑分析仪接 LIN 的通道")
    ap.add_argument("--lin-ch", type=int, default=0, help="图莫斯 LIN 通道")
    ap.add_argument("--rate", default="1M")
    ap.add_argument("--dur", default="3s")
    ap.add_argument("--buffer", action="store_true")
    ap.add_argument("--vth", type=float, default=2.0)
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--ids", help="逗号分隔的十六进制 ID，依次替换 PLAN 里的 7 个 ID")
    a = ap.parse_args()
    plan = PLAN
    if a.ids:
        ids = [int(x, 16) for x in a.ids.split(",")]
        plan = [(ids[i] if i < len(ids) else fid, d, ck) for i, (fid, d, ck) in enumerate(PLAN)]

    sdk = sdk_dir()
    os.add_dll_directory(sdk)
    windll.LoadLibrary(os.path.join(sdk, "libusb-1.0.dll"))
    lib = windll.LoadLibrary(os.path.join(sdk, "USB2XXX.dll"))

    # 先启动采集（硬件触发：LIN 通道下降沿 = 第一帧 Break 的起点），dslab 打开设备约 1.5 s，之后再发帧
    cmd = [sys.executable, "-I", os.path.join(HERE, "la.py"), "capture", "--ch", str(a.la_ch),
           "--rate", a.rate, "--dur", a.dur, "--vth", str(a.vth), "--trig", f"D{a.la_ch}=F", "--label", "linloop"]
    if a.buffer:
        cmd.append("--buffer")
    cap = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(2.0)

    h = (c_uint * 20)()
    if lib.USB_ScanDevice(byref(h)) <= 0:
        cap.kill()
        sys.exit("RESULT: FAIL 没有找到图莫斯")
    dev = h[0]
    lib.USB_OpenDevice(dev)
    sent = []
    try:
        if lib.LIN_EX_Init(dev, a.lin_ch, 19200, 1) != 0:
            sys.exit("RESULT: FAIL LIN_EX_Init 失败")
        for _ in range(a.repeat):
            for fid, data, ck in plan:
                if data is None:
                    r = lib.LIN_EX_MasterRead(dev, a.lin_ch, fid, (c_ubyte * 8)())
                else:
                    r = lib.LIN_EX_MasterWrite(dev, a.lin_ch, fid, (c_ubyte * 8)(*data), len(data), ck)
                sent.append((fid, data, ck, r))
                time.sleep(0.01)
    finally:
        lib.USB_CloseDevice(dev)
    out = cap.communicate(timeout=120)[0]
    print(out.strip())
    m = re.search(r"运行目录: (.+)", out)
    if cap.returncode != 0 or not m:
        sys.exit("RESULT: FAIL 采集失败")
    run = m.group(1).strip()

    with open(os.path.join(run, "meta.json"), encoding="utf-8") as f:
        rate = json.load(f)["sample_rate"]
    names, init, edges, _ = la_lin.load_vcd(os.path.join(run, "capture.vcd"), rate)
    c = names.index(str(a.la_ch))
    frames = la_lin.decode_lin(la_lin.Wave(init[c], edges[c], rate), rate)
    la_lin.write_tsv(frames, os.path.join(run, f"lin_D{a.la_ch}.tsv"))

    print(f"\n发送 {len(sent)} 帧，解码 {len(frames)} 帧")
    ok, rows = 0, []
    for i, (fid, data, ck, r) in enumerate(sent):
        fr = frames[i] if i < len(frames) else None
        if fr is None:
            v = "丢失（采集窗口太短？加大 --dur）"
        elif fr["id"] != fid:
            v = f"ID 不符（收到 0x{fr['id']:02X}）"
        elif data is None:
            v = "OK" if not fr["data"] and fr["chk"] is None else "帧头后有多余字节（总线上有从机应答？）"
        elif fr["data"] != data:
            v = "数据不符"
        elif fr["chk_type"] != ("enh" if ck else "cls"):
            v = f"校验和不符（{fr['chk_type']}）"
        else:
            v = "OK"
        ok += v == "OK"
        rows.append(f"{i}\t0x{fid:02X}\t{' '.join('%02X' % d for d in data) if data else '(header)'}\t"
                    f"{'enh' if ck else 'cls'}\t{r}\t{v}")
        if v != "OK":
            print(f"  #{i} ID 0x{fid:02X}：{v}  发送返回 {r}")
    for fr in frames[:len(plan)]:
        print(la_lin.fmt(fr))
    print("\n".join(la_lin.summary(frames, 19200)))
    with open(os.path.join(run, "loop_compare.tsv"), "w", encoding="utf-8") as f:
        f.write("n\tsent_id\tsent_data\tsent_chk\tsend_ret\tverdict\n" + "\n".join(rows) + "\n")
    print(f"比对：{ok}/{len(sent)} 帧一致，结果在 {run}")
    print("RESULT: OK" if ok == len(sent) else "RESULT: FAIL 有帧不一致")


if __name__ == "__main__":
    main()
