# Acceptance

Offline evaluation says the system matches its examples. This protocol says whether the people who live with the output accept it. Run it before production traffic, with the client in the room.

## Protocol

1. **Who judges**: the named evaluation owner (the client_readiness gate holds their name), plus at least one person who does the work today. Not the builder.
2. **Sample**: fresh items from live data -- never the golden set (the system has seen those 19 in CI). Size to match the golden set or 30, whichever is larger.
3. **Blind pass**: the judges label the sample before seeing the system's output; disagreement between judges is recorded, not resolved by the loudest voice.
4. **Compare**: system output against the blind labels, scored by the same metrics the harness runs. The baseline's error rate is the number to beat -- beating zero was never the bar.
5. **Sign-off**: recorded with names and the score. A meeting that went well is not a sign-off.

## Refusals worth respecting

If nobody can be found to judge, that is the client_readiness gate failing late -- stop and escalate rather than accepting on their behalf.
