"""Root-state priority plus both damage actions.

Hand-specified from the Trident planner schema (arXiv 2608.04317):
host_state_priority mass on R and RD, state_action_probs weighted toward
Impact and DegradeServices in those rows. No search, no LLM.

None of the twelve shipped heuristics combines both levers. Degrader biases
DegradeServices, Impacter biases Impact in operational zones only, and neither
reweights host-state priority toward root. Base R row is
[0.5, ..., 0.25, 0.25, 0.0], so half of all root-state actions are spent on
rediscovery rather than damage.
"""
from CybORG.Agents.SimpleAgents.FiniteStateRedAgent import FiniteStateRedAgent


class FSRedAgentWrecker(FiniteStateRedAgent):

    def set_host_state_priority_list(self):
        return {'K': 2, 'KD': 2, 'S': 5, 'SD': 5,
                'U': 11, 'UD': 11, 'R': 32, 'RD': 32}

    def state_transitions_probability(self):
        return {
            'K':  [0.30, 0.50, 0.20, None, None, None, None, None, None],
            'KD': [None, 0.50, 0.50, None, None, None, None, None, None],
            'S':  [0.10, None, None, 0.10, 0.80, None, None, None, None],
            'SD': [None, None, None, 0.20, 0.80, None, None, None, None],
            'U':  [0.10, None, None, None, None, 0.90, None, None, 0.0],
            'UD': [None, None, None, None, None, 1.00, None, None, 0.0],
            'R':  [0.05, None, None, None, None, None, 0.55, 0.40, 0.0],
            'RD': [None, None, None, None, None, None, 0.55, 0.45, 0.0],
        }
