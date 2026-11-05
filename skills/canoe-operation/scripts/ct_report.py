"""Export CANoe LIN conformance reports to XML and summarize verdicts.

Usage: python -I ct_report.py <out_dir> <report.vtestreport> [...]
Set CANOE_REPORT_EXPORTER if the Test Report Viewer is installed elsewhere.
"""
import collections
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

EXPORTER = os.environ.get(
    "CANOE_REPORT_EXPORTER",
    r"C:\Program Files (x86)\Vector CANoe Test Report Viewer 12.0\TestReportXmlExporter.exe",
)


def export(report: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    copy = out_dir / report.name
    shutil.copy2(report, copy)
    xml_path = out_dir / (report.stem + ".xml")
    subprocess.run([EXPORTER, f"-r={copy}", f"-e={xml_path}"], check=True, capture_output=True, timeout=600)
    return xml_path


def summarize(xml_path: Path) -> None:
    root = ET.parse(xml_path).getroot()
    counts = collections.Counter()
    lines = []

    def walk(node, group):
        for child in node:
            if child.tag == "testgroup":
                walk(child, child.findtext("title"))
            elif child.tag in ("testcase", "skipped"):
                verdict = child.find("verdict")
                result = verdict.get("result") if verdict is not None else "skipped"
                counts[result] += 1
                lines.append((group, child.findtext("ident"), child.findtext("title"), result))

    walk(root, None)
    print(f"## {xml_path.name}  start={root.get('starttime')}  state={root.get('reportrunstate')}  {dict(counts)}")
    executed = [l for l in lines if l[3] != "skipped"]
    if len(executed) <= 20:
        for l in executed:
            print(f"  [{l[0]}] {l[1]} | {l[2]} | {l[3]}")
    else:
        for l in executed:
            if l[3] != "pass":
                print(f"  [{l[0]}] {l[1]} | {l[2]} | {l[3]}")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    for r in sys.argv[2:]:
        summarize(export(Path(r), out))
