#!/usr/bin/env python3
"""Print the training recipe stored in a KEEP-family checkpoint's `agent` tuple, one field per line."""
import sys, torch
def sci(x):
    m, e = f"{x:e}".split("e"); return f"{float(m):g}e{int(e)}"
ck = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
args, kw = ck["agent"]
print(f"hidden1 {kw['a_kwargs']['hidden1']}"); print(f"hidden2 {kw['a_kwargs']['hidden2']}")
print(f"clip {kw['clip']}"); print(f"actor_lr {sci(kw['a_kwargs']['lr'])}"); print(f"critic_lr {sci(kw['c_kwargs']['lr'])}")
print(f"concat_edges {kw.get('concat_edges')}"); print(f"actor_params {sum(v.numel() for v in ck['actor'].values())}")
