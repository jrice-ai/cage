#!/usr/bin/env python3
"""Recovery precision by the H-MARL authors' own counter, from the log of their evaluation_metrics.py."""
import re, sys
s = open(sys.argv[1]).read()
tp = float(re.search(r"True pos across subnets:\s*([\d.]+)", s).group(1))
fp = float(re.search(r"False pos across subnets:\s*([\d.]+)", s).group(1))
print(f"true_pos {tp}  false_pos {fp}  precision_pct {100 * tp / (tp + fp):.1f}  rounded {round(100 * tp / (tp + fp))}")
