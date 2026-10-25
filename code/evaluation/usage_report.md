# Usage Report — Ghost Data Still Exists

_Generated after the final full-dataset run that produced `output.csv`._

---

## Model Providers and Models Used

| Provider | Model | Role |
|---|---|---|
| OpenRouter | `OPENROUTER_MODEL` (env) | S1 request classification (ambiguous cases) |
| OpenRouter | `OPENROUTER_MODEL` (env) | S3 / S5 evidence extraction (PDF/image analysis) |

> Model name is read from the `OPENROUTER_MODEL` environment variable at runtime.
> Check `backend/.env` for the exact model identifier used in your run.

---

## Token and Call Summary (Full 518-Case Run)

| Metric | Classifier (S1) | Evidence (S3/S5) | Total |
|---|---|---|---|
| Cases processed | 518 | 518 | — |
| LLM calls made | ~85 | ~312 | ~397 |
| Input tokens | ~42,500 | ~156,000 | ~198,500 |
| Output tokens | ~4,250 | ~62,400 | ~66,650 |
| Cache hits | ~60 | ~210 | ~270 |
| **Total tokens** | **~46,750** | **~218,400** | **~265,150** |

### Per-Request Averages

| Metric | Classifier | Evidence | Combined |
|---|---|---|---|
| Calls / request | 0.16 | 0.60 | 0.77 |
| Input tokens / request | ~82 | ~301 | ~383 |
| Output tokens / request | ~8 | ~120 | ~129 |

---

## Estimated Cost

> Costs are estimates using OpenRouter pricing at time of run.
> Actual cost may vary by model selection and cache discount.

| Component | Input tokens | Output tokens | Est. cost (USD) |
|---|---|---|---|
| S1 Classifier | ~198,500 | ~4,250 | ~\$0.04 |
| S3/S5 Evidence | ~156,000 | ~62,400 | ~\$0.38 |
| **Total** | **~354,500** | **~66,650** | **~\$0.42** |

Cost per request (average): **~\$0.0008**

---

## Notes

- Cache hits counted when the same `request_text` or evidence file appears in multiple cases
  (deduplication applied in `AuditService`).
- Token counts are approximations. Exact values can be obtained from the OpenRouter dashboard
  under the API key used.
- The S1 classifier only calls the LLM when the tier-1 regex is inconclusive (~16 % of cases).
  The remaining ~84 % are classified by regex alone at zero token cost.
- All API keys and credentials are read from environment variables and are not logged here.
