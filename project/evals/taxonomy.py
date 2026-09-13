"""Why a case failed, by source rather than by symptom.

Knowing an answer was wrong tells you how often you fail. Knowing the failure
came from ingestion tells you what to build next, and those are different
questions with different answers.
"""

DATA = "data"                 # the source was wrong or missing before we touched it
INPUT = "input"               # parsing lost or mangled it on the way in
PREDICTION = "prediction"     # the model or rule produced the wrong value
OUTPUT = "output"             # right value, wrong shape or place
SYSTEM = "system"             # timeout, crash, resource exhaustion
INTEGRATION = "integration"   # the boundary between two parts of this

SOURCES = [DATA, INPUT, PREDICTION, OUTPUT, SYSTEM, INTEGRATION]


def classify(expected, actual, context=None):
    """Best-effort attribution. Deliberately conservative: an unattributed
    failure is more useful than a confidently mis-attributed one."""
    context = context or {}
    if context.get("exception"):
        return SYSTEM
    if context.get("parse_losses"):
        return INPUT
    if actual in (None, ""):
        return DATA if context.get("source_missing") else PREDICTION
    if type(actual) is not type(expected):
        return OUTPUT
    return PREDICTION
