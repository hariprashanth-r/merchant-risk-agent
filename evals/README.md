# Evaluation

How this project is evaluated, mapped to the production "test pyramid."

## What runs where

| Layer | What it checks | How to run | Needs API key? |
|------|----------------|------------|----------------|
| 1 · Tool unit tests | Tools return correct data | `pytest` | No |
| 1/5 · Deterministic guardrails | Sanctioned names are flagged; no false positives | `pytest` | No |
| 3 · Golden-set outcome | Full agent verdict vs. labeled truth | `make eval` | Yes |
| 5 · Agent guardrails | A sanctions hit is never "approve" | `make eval` | Yes |

## The golden set

`golden_merchants.json` is a small labeled dataset — each merchant has an
`expected_recommendation` (the human ground truth) and a `hard_stop` flag for
cases that must never be approved. Grow this file as you find cases the agent
gets wrong; that is how the dataset becomes valuable over time.

## Running it

```bash
# deterministic layer only (no key needed) — also runs in CI:
pytest

# full evaluation over the golden set (needs GOOGLE_API_KEY in .env):
make eval        # or: python -m evals.run_eval
```

`run_eval.py` prints a confusion matrix, accuracy, recall on the "decline"
class, and a **cost-weighted score**. The cost table is deliberately
asymmetric: a false *approval* of a risky merchant is penalised far more than a
false *decline* of a good one, because that mirrors real risk economics. The
process exits non-zero if any guardrail fails, so it can gate a deploy.

## What's intentionally NOT here yet (good next exercises)

- **LLM-as-judge (Layer 4):** grade the free-text `summary` and flag `evidence`
  for faithfulness and hallucinations. ADK provides this via rubric metrics
  (`RUBRIC_BASED_FINAL_RESPONSE_QUALITY_V1`, `HallucinationsCriterion`).
- **Trajectory eval (Layer 2):** check the gatherer calls the expected tools
  using ADK's `TOOL_TRAJECTORY_AVG_SCORE` and an ADK eval set captured from
  `adk web`.
- **Online monitoring:** override rate, drift, and downstream fraud feedback —
  these only exist once the agent is live.
```
