#!/usr/bin/env python3
"""Write the paper's four tables as LaTeX fragments under fig/, using ledger macros for every number."""
import os
OUT = os.path.dirname(os.path.abspath(__file__))
def w(name, body): open(os.path.join(OUT, name), "w").write(body); print("wrote", name)

w("tab_repro.tex", r"""\setlength{\tabcolsep}{4pt}\begin{tabular}{L{0.17\linewidth}L{0.19\linewidth}rlL{0.27\linewidth}}
\toprule
Defender & Published & Reproduced & 95\% interval & Protocol \\
\midrule
KEEP (graph PPO) & \keeppub\ (leaderboard) & \keeprepro & [\keepreprolo, \keepreprohi] & \samplingseeds\ sampling seeds $\times$ \episodes\ episodes, sampled actions \\
H-MARL Expert (hierarchical PPO) & \hmarlauthorscore\ $\pm$ \hmarlauthorsd\ (authors), \hmarlpub\ (Trident) & \hmarlrepro & [\hmarlreprolo, \hmarlreprohi] & \samplingseeds\ seeds $\times$ \episodes\ episodes, the authors' evaluator \\
\bottomrule
\end{tabular}
""")

w("tab_tiers.tex", r"""\setlength{\tabcolsep}{4pt}\begin{tabular}{lL{0.33\linewidth}L{0.20\linewidth}L{0.28\linewidth}}
\toprule
Tier & Defect & Lives in & What it changes \\
\midrule
A & A directive asserted while the agent's previous action is in progress is dropped by design and without an error, a dropped Restore is still charged one point, and the observation the challenge documents omits the busy flag (\secref{sec:drop}) & CybORG controller and challenge vector wrappers & Injected interventions are dropped unseen when the agent is busy and charged if they are Restores, costing our supervisory harness \sheldvsfired\ and \hmsheldvsfired\ points per episode at the stock adversary and \keepheldvsfired\ and \hmarlheldvsfired\ under Wrecker, the rule's silence after each drop included. An agent on the documented observation cannot see the busy state, and a count of its outputs counts directives. Both released defenders read the flag \\
\midrule
B & Evaluation seeds the environment but not policy sampling & CAGE 4 template & A reported mean is one draw that no one can reproduce. For KEEP, a stochastic policy evaluated in sampling mode, the within-episode sampling sd is \samplingsd\ at stock and \samplingsdwrecker\ under Wrecker, \pct{\samplingvarshare} (interval \pct{\samplingvarsharelo} to \pct{\samplingvarsharehi}) and \pct{\samplingvarsharewrecker} of per-episode outcome variance, and a one-seed \episodes-episode mean has a standard error of \oneseedse\ and \oneseedsewrecker\ points \\ \addlinespace
B & Parallel evaluation builds one environment per worker from one seed argument and rotates episodes over them & KEEP's copy of the evaluation script & A run with \paralleldistinct\ workers visits at most \paralleldistinct\ distinct episodes \\ \addlinespace
B & All \trainenvs\ training environments share one seed, the training workers' generators are never seeded, every update replays the parent's scenario draws, and the learner reads five of the twenty-five episodes an update generates & KEEP trainer & A training run learns from one scenario draw as shipped and is not reproducible from its seed (\secref{sec:pilot}) \\
\midrule
C & The evaluation record holds per-step actions and observations and per-episode totals, and no per-step reward, phase or true state & CAGE 4 template (KEEP's copy writes nothing from the command line) & No decision can be scored from what the script writes \\ \addlinespace
C & \texttt{get\_reward\_breakdown} raises, and \texttt{AgentInterface} has no reward calculator & CybORG & Per-host reward attribution, which the benchmark advertises, is unavailable \\
\bottomrule
\end{tabular}
""")

w("tab_criteria.tex", r"""\setlength{\tabcolsep}{4pt}\begin{tabular}{L{0.30\linewidth}L{0.13\linewidth}L{0.13\linewidth}L{0.13\linewidth}L{0.14\linewidth}}
\toprule
Criterion & KEEP Restore & KEEP Remove & O1 & O1 vs.\ KEEP \\
\midrule
Ground truth (red session on the host before the step, for Remove an upper bound on the H-MARL authors' figure) & \pco{\restoreprecision} & \pco{\removeprecision} & \pco{\oonerestoreprecision} & \oonedelta\ points, \oonewins\ of \episodes \\
The rule's own directives, as a share of the arm's executed Restores, correct at decision time & & & \pct{\oonerulerestoreshare} & \\
Latched evidence (host named by an alert since its last Restore or Remove) & \pco{\keepevidenceshare} & \pco{\keepremoveevidenceshare} & \pco{\ooneevidenceshare}$^\dagger$ & \\
\multicolumn{5}{L{0.92\linewidth}}{\scriptsize $^\dagger$The target the rule would choose at each of KEEP's own Restore steps, scored on the KEEP arm, a different set of steps from the rest of the row.} \\
\midrule
\multicolumn{5}{l}{\emph{The latched set against the true state, supervised KEEP arms}} \\
Adversary & Flagged & Precision & Recall & Lift over chance \\
\midrule
Wrecker & \pct{\evidenceflagged} & \pct{\evidenceprecision} & \pct{\evidencerecall} & \evidencelift$\times$ \\
Stock & \pct{\evidenceflaggedstock} & \pct{\evidenceprecisionstock} & \pct{\evidencerecallstock} & \evidenceliftstock$\times$ \\
\bottomrule
\end{tabular}
""")

w("tab_audit.tex", r"""\setlength{\tabcolsep}{4pt}\begin{tabular}{L{0.14\linewidth}L{0.19\linewidth}L{0.19\linewidth}L{0.21\linewidth}L{0.16\linewidth}}
\toprule
Table & Artifact & Seed, dispersion & Criterion, scenario & Adversary \\
\midrule
CAGE 4 leaderboard (2024) & checkpoints not identified, no code or checkpoint released for entries above fifth & one mean per entry on the page, mean and unlabeled $\pm$ over \leaderboardepisodes\ episodes for the best agent of each of four teams in the organizers' paper, no seeds or sampling mode & scored by one script that sums the reward each submission's own wrapper returns (Appendix~\ref{app:issues}) & stock, stated in the challenge README and the organizers' paper, not on the page \\ \addlinespace
Trident, Table 2 (2026) & H-MARL weights md5-identical to the copy in Trident's repository (Table~\ref{tab:env}), whether its table used them unstated. The GNN is a disclosed retrain at \tridentkeepscore, from a checkpoint whose recorded recipe differs from the text's & $\pm$ stated as sd across \tridentruns\ runs of \tridentrunepisodes\ episodes & stated & varied, stated \\ \addlinespace
ACDZero, Tables I and II (2026) & KEEP baseline is the leaderboard number to the digit & mean $\pm$ sd over \acdzeroepisodes\ episodes stated. Baseline sd \leaderboardkeepsd\ is a third of the checkpoint's across-episode sd. Ablation row equals the baseline row & recovery precision reported with the criterion unstated, and no Restore counts & stock, stated as the official protocol \\ \addlinespace
HC-MARL, Tables 3, 4 and 5 (2026) & code available on request only & mean and sd over \hcmarlepisodes\ test runs, in a table titled best rewards & Singh row is H-MARL Meta, not Expert. Seven agents on a five-agent scenario. The action mask is worth \hcmarliocdelta\ points. Its own Restore count alone exceeds its reported loss under the pinned reward & stock, stated in its limitations \\ \addlinespace
Shaikh et al., Table 2 (2026) & H-MARL checkpoint not identified & \shaikhepisodes\ episodes, no dispersion, though a rate over that many episodes has a standard error under four points, no seeds, sampling mode unstated & predicate stated, recomputed independently, ``may end earlier'' unspecified & six configurations, stated \\
\bottomrule
\end{tabular}
""")

w("tab_env.tex", r"""\setlength{\tabcolsep}{4pt}\begin{tabular}{L{0.26\linewidth}L{0.36\linewidth}L{0.14\linewidth}L{0.14\linewidth}}
\toprule
Component & Source & Revision & Date \\
\midrule
CybORG and CAGE 4 template & \texttt{cage-challenge/cage-challenge-4} & \texttt{\cagerev} & \cagerevdate \\ \addlinespace
KEEP & \texttt{cybermonic/cage-4-submission}, five checkpoints, one per agent, \texttt{gnn\_ppo-*.pt}, \publishedkeepbytes\ bytes each & \texttt{\keeprev} & \keeprevdate \\ \addlinespace
H-MARL Expert & \texttt{adityavs14/Hierarchical-MARL}, released checkpoint (digest below), byte-identical to Trident's copy at \texttt{\tridentrev} & \texttt{\hmarlrev} & \hmarlrevdate \\ \addlinespace
Undeclared pins & \texttt{pyarrow} \pyarrowpin\ and the CPU wheel index for \texttt{torch} & & \\ \addlinespace
Checkpoint digests & md5 of the sorted per-file md5s.\newline KEEP, its five checkpoints\newline \hashtt{\keepckptdigest}\newline H-MARL, its fifteen policy files and \texttt{algorithm\_state.pkl}\newline \hashtt{\hmarlckptdigest} & & \\ \addlinespace
Images & \texttt{cage-keep:dev} and \texttt{cage-hmarl:dev}, since the two dependency sets do not coexist & & \\
\bottomrule
\end{tabular}
""")

w("tab_curve.tex", r"""\setlength{\tabcolsep}{2.5pt}\begin{tabular}{L{0.2\linewidth}rlrrrlr}
\toprule
Defender and adversary & Held minus fired & 95\% interval & Wins & Charge & Rest & 95\% interval & Unsupervised \\
\midrule
KEEP, stock & \sheldvsfired & [\sheldvsfiredlo, \sheldvsfiredhi] & \sheldvsfiredwins & \sheldvsfiredcharge & \sheldvsfiredrest & [\sheldvsfiredrestlo, \sheldvsfiredresthi] & \keepcorpusmean \\
KEEP, ConvOnly & \curveconvonly & [\curveconvonlylo, \curveconvonlyhi] & \curveconvonlywins & \curveconvonlycharge & \curveconvonlyrest & [\curveconvonlyrestlo, \curveconvonlyresthi] & \curvectlconvonly \\
KEEP, Wrecker Q04 & \curveqfour & [\curveqfourlo, \curveqfourhi] & \curveqfourwins & \curveqfourcharge & \curveqfourrest & [\curveqfourrestlo, \curveqfourresthi] & \curvectlqfour \\
KEEP, Wrecker Q16 & \curveqsixteen & [\curveqsixteenlo, \curveqsixteenhi] & \curveqsixteenwins & \curveqsixteencharge & \curveqsixteenrest & [\curveqsixteenrestlo, \curveqsixteenresthi] & \curvectlqsixteen \\
KEEP, Wrecker Q32 & \curveqthirtytwo & [\curveqthirtytwolo, \curveqthirtytwohi] & \curveqthirtytwowins & \curveqthirtytwocharge & \curveqthirtytworest & [\curveqthirtytworestlo, \curveqthirtytworesthi] & \curvectlqthirtytwo \\
KEEP, Wrecker Q48 & \curveqfortyeight & [\curveqfortyeightlo, \curveqfortyeighthi] & \curveqfortyeightwins & \curveqfortyeightcharge & \curveqfortyeightrest & [\curveqfortyeightrestlo, \curveqfortyeightresthi] & \curvectlqfortyeight \\
KEEP, Wrecker & \keepheldvsfired & [\keepheldvsfiredlo, \keepheldvsfiredhi] & \keepheldvsfiredwins & \keepheldvsfiredcharge & \keepheldvsfiredrest & [\keepheldvsfiredrestlo, \keepheldvsfiredresthi] & \keepwreckercontrol \\
\midrule
H-MARL, stock & \hmsheldvsfired & [\hmsheldvsfiredlo, \hmsheldvsfiredhi] & \hmsheldvsfiredwins & \hmsheldvsfiredcharge & \hmsheldvsfiredrest & [\hmsheldvsfiredrestlo, \hmsheldvsfiredresthi] & \hmarlstockcontrol \\
H-MARL, Wrecker & \hmarlheldvsfired & [\hmarlheldvsfiredlo, \hmarlheldvsfiredhi] & \hmarlheldvsfiredwins & \hmarlheldvsfiredcharge & \hmarlheldvsfiredrest & [\hmarlheldvsfiredrestlo, \hmarlheldvsfiredresthi] & \hmarlwreckercontrol \\
\bottomrule
\end{tabular}
""")

w("tab_dir.tex", r"""\setlength{\tabcolsep}{4pt}\begin{tabular}{L{0.40\linewidth}L{0.25\linewidth}L{0.25\linewidth}}
\toprule
Share recovered & Fired & Held \\
\midrule
Of the loss Wrecker adds, KEEP & \pct{\dirkeepfired} [\pct{\dirkeepfiredlo}, \pct{\dirkeepfiredhi}] & \pct{\dirkeepheldloss} [\pct{\dirkeepheldlosslo}, \pct{\dirkeepheldlosshi}] \\
Of the loss Wrecker adds, H\nobreakdash-MARL & \pct{\dirhmarlfired} [\pct{\dirhmarlfiredlo}, \pct{\dirhmarlfiredhi}] & \pct{\dirhmarlheldloss} [\pct{\dirhmarlheldlosslo}, \pct{\dirhmarlheldlosshi}] \\
Of the distance to the RT reference, KEEP & \pct{\dirkeepfiredceiling} [\pct{\dirkeepfiredceilinglo}, \pct{\dirkeepfiredceilinghi}] & \pct{\dirkeepheld} [\pct{\dirkeepheldlo}, \pct{\dirkeepheldhi}] \\
Of the distance to the RT reference, H\nobreakdash-MARL & \pct{\dirhmarlfiredceiling} [\pct{\dirhmarlfiredceilinglo}, \pct{\dirhmarlfiredceilinghi}] & \pct{\dirhmarlheld} [\pct{\dirhmarlheldlo}, \pct{\dirhmarlheldhi}] \\
\bottomrule
\end{tabular}
""")

w("tab_wrecker.tex", r"""\setlength{\tabcolsep}{5pt}\begin{tabular}{lcccccccc}
\toprule
State & DRS & ASD & SSD & DD & ERS & PE & Imp & Deg \\
\midrule
K & \stockkdrs\ / \wreckkdrs & \stockkasd\ / \wreckkasd & \stockkssd\ / \wreckkssd &  &  &  &  &  \\
KD &  & \stockkdasd & \stockkdssd &  &  &  &  &  \\
S & \stocksdrs\ / \wrecksdrs &  &  & \stocksdd\ / \wrecksdd & \stocksers\ / \wrecksers &  &  &  \\
SD &  &  &  & \stocksddd\ / \wrecksddd & \stocksders\ / \wrecksders &  &  &  \\
U & \stockudrs\ / \wreckudrs &  &  &  &  & \stockupe\ / \wreckupe &  &  \\
UD &  &  &  &  &  & \stockudpe &  &  \\
R & \stockrdrs\ / \wreckrdrs &  &  &  &  &  & \stockrimp\ / \wreckrimp & \stockrdeg\ / \wreckrdeg \\
RD &  &  &  &  &  &  & \stockrdimp\ / \wreckrdimp & \stockrddeg\ / \wreckrddeg \\
\bottomrule
\end{tabular}
""")
