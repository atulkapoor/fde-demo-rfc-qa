"""The one contract every step shares: forbidden input is refused.

Raise RefusedInput for input the pipeline must not act on -- a
missing field, a type violation, an empty document. The adversarial
layer of the eval harness treats RefusedInput as the CORRECT answer
to a forbidden probe, and anything else -- a crash, or worse, a
confident output -- as the failure it is. Accepting forbidden input
is how a system invents an answer nobody can trace.
"""


class RefusedInput(ValueError):
    """This input is forbidden by the contract, and saying so is
    the correct behaviour."""
