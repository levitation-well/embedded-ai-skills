"""逻辑分析仪波形的读取和 LIN 解码（la.py 调用，也可单独 import）。
- load_vcd：dslab 输出的 VCD（只记翻转，通道名 = 硬件通道号）
- load_csv：ALL LOGIC export_csv 的 CSV（每样本一行，列名按已开通道从 D0 重新编号）
- decode_lin：Break（≥11 位低）→ Sync 0x55 量波特率 → 逐字节按位中心采样，校验 PID 和校验和
"""
import bisect, statistics


def load_vcd(path, rate):
    """返回 (通道名列表, 初始电平列表, 每通道翻转样本号列表, 样本数)。"""
    ids, names, init, edges, cur, t = {}, [], [], [], [], 0
    scale = 1e-9
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("$timescale"):
                scale = {"1ps": 1e-12, "1ns": 1e-9, "10ns": 1e-8, "1us": 1e-6}.get(s.split()[1], 1e-9)
            elif s.startswith("$var"):
                p = s.split()
                ids[p[3]] = len(names)
                names.append(p[4])
                init.append(None)
                edges.append([])
                cur.append(None)
            elif s[0] == "#":
                t = round(int(s[1:]) * scale * rate)
            elif s[0] in "01" and s[1:] in ids:
                c, v = ids[s[1:]], int(s[0])
                if init[c] is None:
                    init[c] = cur[c] = v
                elif v != cur[c]:
                    edges[c].append(t)
                    cur[c] = v
    return names, [v or 0 for v in init], edges, t + 1


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        head = f.readline().strip().split(",")
        nch = len(head) - 1
        init = [int(v) for v in f.readline().strip().split(",")[1:]]
        last, edges, n = init[:], [[] for _ in range(nch)], 1
        for line in f:
            p = line.rstrip().split(",")
            i = int(p[0])
            for c in range(nch):
                v = 1 if p[c + 1] == "1" else 0
                if v != last[c]:
                    edges[c].append(i)
                    last[c] = v
            n += 1
    return head[1:], init, edges, n


class Wave:
    """单通道波形：初始电平 + 翻转点（样本号）。"""

    def __init__(self, init, edges, rate):
        self.init, self.e, self.rate = init, edges, rate

    def level(self, s):
        return self.init ^ (bisect.bisect_right(self.e, s) & 1)

    def next_edge(self, s, falling=None):
        k = bisect.bisect_right(self.e, s)
        while k < len(self.e):
            lv = self.init ^ ((k + 1) & 1)          # 这次翻转之后的电平
            if falling is None or falling == (lv == 0):
                return self.e[k]
            k += 1
        return None

    def pulses(self, start, end):
        """窗口 [start, end) 内每段电平：(起点样本, 电平, 宽度样本)。首尾两段被窗口截断，不算完整脉冲。"""
        pts = [start] + [x for x in self.e if start < x < end] + [end]
        return [(a, self.level(a), b - a) for a, b in zip(pts, pts[1:])]


def pid_ok(pid):
    i = pid & 0x3F
    b = [(i >> n) & 1 for n in range(6)]
    p0 = b[0] ^ b[1] ^ b[2] ^ b[4]
    p1 = 1 ^ (b[1] ^ b[3] ^ b[4] ^ b[5])
    return pid == (i | p0 << 6 | p1 << 7)


def checksum(data, pid=None):
    s = pid if pid is not None else 0
    for d in data:
        s += d
        if s > 0xFF:
            s -= 0xFF
    return (~s) & 0xFF


def decode_lin(w, rate, nominal_baud=19200):
    """返回帧列表；时间单位 us。帧头之后没有字节的是只有帧头（主机读、从机没应答）。"""
    us, nom_bit, frames, s = 1e6 / rate, rate / nominal_baud, [], 0
    while True:
        f = w.next_edge(s, falling=True)
        r = w.next_edge(f, falling=False) if f is not None else None
        if r is None:
            break
        if r - f < 11 * nom_bit:                     # 不够 Break 长度，跳过
            s = r
            continue
        f0 = w.next_edge(r, falling=True)
        if f0 is None:
            break
        fe, t = [f0], f0
        for _ in range(4):                           # Sync 0x55：起始位下降沿到第 5 个下降沿 = 8 位
            t = w.next_edge(t, falling=True)
            if t is None:
                break
            fe.append(t)
        if len(fe) < 5:
            break
        bit = (fe[4] - fe[0]) / 8
        bytes_, starts, t = [], [], f0
        while t is not None:
            if w.level(t + bit / 2) != 0:
                break
            v = 0
            for k in range(8):
                v |= w.level(t + bit * (1.5 + k)) << k
            bytes_.append((v, w.level(t + bit * 9.5)))
            starts.append(t)
            nxt = w.next_edge(t + bit * 9.5, falling=True)
            if nxt is None or nxt - (t + 10 * bit) > 20 * bit:   # 空闲超过 2 字节，帧结束
                break
            rr = w.next_edge(nxt, falling=False)
            if rr is not None and rr - nxt >= 11 * nom_bit:      # 下一个是 Break
                break
            t = nxt
        end = starts[-1] + 10 * bit
        pid = bytes_[1][0] if len(bytes_) > 1 else None
        payload = [b for b, _ in bytes_[2:]]
        fr = dict(t_us=f * us, break_us=(r - f) * us, break_bits=(r - f) / bit, delim_us=(f0 - r) * us,
                  baud=rate / bit, sync=bytes_[0][0], pid=pid, data=payload[:-1],
                  chk=payload[-1] if payload else None,
                  stop_err=sum(1 for _, st in bytes_ if st != 1), dur_us=(end - f) * us)
        fr["id"] = pid & 0x3F if pid is not None else None
        fr["pid_ok"] = pid is not None and pid_ok(pid)
        if fr["chk"] is None:
            fr["chk_type"] = "-"
        elif checksum(fr["data"], pid) == fr["chk"]:
            fr["chk_type"] = "enh"
        elif checksum(fr["data"]) == fr["chk"]:
            fr["chk_type"] = "cls"
        else:
            fr["chk_type"] = "BAD"
        frames.append(fr)
        s = end
    return frames


def bad(fr):
    return not fr["pid_ok"] or fr["chk_type"] == "BAD" or fr["stop_err"] or fr["sync"] != 0x55


def fmt(fr):
    pid = "--" if fr["pid"] is None else f"{fr['pid']:02X}"
    fid = "--" if fr["id"] is None else f"{fr['id']:02X}"
    chk = "--" if fr["chk"] is None else f"{fr['chk']:02X}"
    return (f"t={fr['t_us'] / 1e3:10.3f} ms  ID 0x{fid} (PID 0x{pid} {'ok' if fr['pid_ok'] else 'BAD'})  "
            f"data=[{' '.join('%02X' % d for d in fr['data'])}]  chk=0x{chk}({fr['chk_type']})  "
            f"break={fr['break_bits']:.2f}bit  baud={fr['baud']:.0f}  帧长={fr['dur_us'] / 1e3:.3f}ms"
            f"{'  <<错误' if bad(fr) else ''}")


def summary(frames, baud):
    if not frames:
        return ["没有解出 LIN 帧：确认通道、阈值（总线上 12 V 电平用 2 V 左右）、总线上是否有帧"]
    bauds = [f["baud"] for f in frames]
    brks = [f["break_bits"] for f in frames]
    gaps = [b["t_us"] - a["t_us"] for a, b in zip(frames, frames[1:])]
    ids = {}
    for f in frames:
        ids[f["id"]] = ids.get(f["id"], 0) + 1
    out = [f"共 {len(frames)} 帧，错误帧 {sum(map(bad, frames))}（PID 校验错 / 校验和错 / 停止位错 / Sync 不是 0x55）",
           f"波特率  均值 {statistics.mean(bauds):.1f}  最小 {min(bauds):.1f}  最大 {max(bauds):.1f}"
           f"（相对 {baud} 偏差 {100 * (statistics.mean(bauds) / baud - 1):+.3f}%）",
           f"Break   均值 {statistics.mean(brks):.2f} 位  最小 {min(brks):.2f}  最大 {max(brks):.2f}",
           f"分隔符  均值 {statistics.mean(f['delim_us'] for f in frames):.1f} us",
           "各 ID 帧数: " + ", ".join(f"0x{k:02X}={v}" if k is not None else f"无PID={v}" for k, v in ids.items())]
    if gaps:
        out.append(f"帧间隔  均值 {statistics.mean(gaps) / 1e3:.3f} ms  最小 {min(gaps) / 1e3:.3f}  最大 {max(gaps) / 1e3:.3f}")
    return out


def write_tsv(frames, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("t_ms\tid\tpid\tpid_ok\tdata\tchk\tchk_type\tbreak_us\tbreak_bits\tdelim_us\tbaud\tdur_ms\tstop_err\n")
        for fr in frames:
            f.write("\t".join([f"{fr['t_us'] / 1e3:.3f}",
                               "" if fr["id"] is None else f"0x{fr['id']:02X}",
                               "" if fr["pid"] is None else f"0x{fr['pid']:02X}", str(int(fr["pid_ok"])),
                               " ".join("%02X" % d for d in fr["data"]),
                               "" if fr["chk"] is None else f"0x{fr['chk']:02X}", fr["chk_type"],
                               f"{fr['break_us']:.2f}", f"{fr['break_bits']:.3f}", f"{fr['delim_us']:.2f}",
                               f"{fr['baud']:.2f}", f"{fr['dur_us'] / 1e3:.4f}", str(fr["stop_err"])]) + "\n")
