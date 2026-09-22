#!/usr/bin/env python3
"""Print one or more blocks of the Foundry export dump in full.

Usage:  python other/scripts/dump_block.py t1_sex_continuous [more_blocks ...]
        python other/scripts/dump_block.py --list

Written 2026-09-17 while transcribing data_new.txt into main.tex. The dump is a
tab-separated multi-table file with wide tables; pandas truncates them on print,
so this sets display options wide enough to read every column.
"""
import io
import os
import re
import sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "foundry_exports",
                    "data_new_9172026", "data_new.txt")


def load_blocks(path=DATA):
    lines = open(path).read().split("\n")
    blocks, name, buf = {}, None, []
    name_re = re.compile(r"^[a-z][a-z0-9_]+$")

    def flush(nm, rows):
        rows = [r for r in rows if r.strip() != ""]
        if nm and rows:
            blocks[nm] = pd.read_csv(io.StringIO("\n".join(rows)), sep="\t")

    for ln in lines:
        if name_re.match(ln.strip()) and ln == ln.strip():
            flush(name, buf)
            name, buf = ln.strip(), []
        else:
            buf.append(ln)
    flush(name, buf)
    return blocks


if __name__ == "__main__":
    B = load_blocks()
    pd.set_option("display.max_rows", None, "display.max_columns", None,
                  "display.width", 250, "display.max_colwidth", 90)
    args = sys.argv[1:]
    if not args or args[0] == "--list":
        for k, v in B.items():
            print(f"{k:32s} {v.shape}")
    else:
        for a in args:
            print(f"\n===== {a} =====")
            print(B[a].to_string())
