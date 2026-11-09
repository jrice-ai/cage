#!/bin/bash
# Level 1 of the paper's Appendix A. Reruns every distinct command in the ledger from this directory and checks that
# each row's stored value appears in its output. The ledger names the analysis layer at ~/papers, so HOME is pointed at
# a scratch directory that links papers/ there for the duration. Arguments pass through to recompute_check.py
# (for example --only key1,key2). Needs the trace archives unpacked under data/traces.
set -u
cd "$(dirname "$0")" || exit 2
[ -d data/traces ] || { echo "unpack the trace archives into data/traces first" >&2; exit 2; }
H=$(mktemp -d) && ln -s "$PWD/papers" "$H/papers" && ln -s "$PWD" "$H/cage" || exit 2
HOME="$H" CAGE="$PWD" python3 papers/recompute_check.py papers/paper1/ledger.csv "$@"
rc=$?
rm -rf "$H"
exit $rc
