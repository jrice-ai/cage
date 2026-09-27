#!/bin/bash
# One arm of a rule defender through oracle.py (KEEP image), with or without a supervisor rule.
# usage: run_rd.sh <kind> <red> [sup] [gap] [budget]
#   kind    R1 | R1d | RT
#   red     FSRedAgentWrecker | FiniteStateRedAgent | FSRedAgentWreckerQ32 | ...
#   sup     supervisor rule on top (O1, O10, ...); default none
#   gap     --min-gap for the supervisor (default 0); budget --budget (default 99999)
# Environment: EPISODES (default 100), WORKERS (default 6), OUTPREFIX (e.g. pilot_),
#   WAIT=1 passes --wait-busy (directives wait for a free agent, rules sleep while busy) and
#   appends _wb to the output name.
# Output data/traces/<prefix>rd_<kind>_<w|s|red>_<sup>[_g<gap>][_wb], log data/<same>.log,
# exit line in data/ft_runs.log.
cd ~/cage || exit 1
k=$1; red=$2; sup=${3:-none}; gap=${4:-0}; budget=${5:-99999}
case $red in FSRedAgentWrecker) a=w;; FiniteStateRedAgent) a=s;; *) a=${red#FSRedAgent};; esac
rule=$k; [ "$sup" != none ] && rule="$k+$sup"
out=${OUTPREFIX:-}rd_${k}_${a}_$sup; [ "$gap" != 0 ] && out=${out}_g$gap
wb=""; [ -n "$WAIT" ] && { wb="--wait-busy"; out=${out}_wb; }
bin/run cage-keep:dev bash -c "cd /opt/cage/cage-4-submission && python3 -u /work/scripts/oracle.py --rule $rule --min-gap $gap --budget $budget --red $red --episodes ${EPISODES:-100} --workers ${WORKERS:-6} $wb --out /work/data/traces/$out" > data/$out.log 2>&1
echo "$out exit $? $(date)" >> data/ft_runs.log
