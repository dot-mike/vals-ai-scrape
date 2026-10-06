# vals-ai-scrape

Index model data and benchmark scores on [vals.ai](https://www.vals.ai) as CSV files.

## Files

`data/models.csv` has one row per model.

| Column | What it is |
|--------|------------|
| `id` | vals.ai model id, such as `alibaba/qwen3.8-27b`. `model` in `scores.csv` uses the same id. |
| `label`, `company`, `country`, `release_date` | As shown on the model page. |
| `open_source` | Open weights. |
| `documentation_url` | The link vals.ai gives. Often the Hugging Face repo, sometimes the vendor's docs. |
| `context_window`, `max_output_tokens` | In tokens. Empty when vals.ai lists none. |
| `reasoning`, `images`, `audio`, `videos`, `tools` | What the model supports in the API vals.ai tested. |
| `vals_index`, `vals_index_rank` | Score on the Vals Index and its rank. Empty when the model is not in the index. |
| `vals_url` | The model page. |

`data/scores.csv` has one row per model, benchmark and task.

| Column | What it is |
|--------|------------|
| `benchmark`, `benchmark_name` | Slug and name, such as `vals_index` and `Vals Index`. |
| `benchmark_updated` | When vals.ai last updated the benchmark. |
| `task`, `task_name` | `overall` is the headline score. Other tasks are parts of the benchmark. |
| `rank`, `ranked` | Rank by accuracy, out of `ranked` models with a score. Equal scores share a rank. |
| `accuracy`, `stderr` | Percent. |
| `cost_per_test`, `latency` | US dollars and seconds per test. |
| `reasoning_effort` | The setting used for the run. |

## Use

```
https://raw.githubusercontent.com/dot-mike/vals-ai-scrape/main/data/models.csv
https://raw.githubusercontent.com/dot-mike/vals-ai-scrape/main/data/scores.csv
```

## Run it locally

```
uv run test_scrape.py
uv run scrape.py
```

`scrape.py` stops with an error when the vals.ai page format changes, so a broken run never overwrites good data.

## Attribution

The data comes from [vals.ai](https://www.vals.ai). The benchmarks, scores and model data are the work of Vals AI. This repo copies the published numbers into CSV files. It is not affiliated with Vals AI. If you use the data, credit vals.ai.

Vals AI can ask for changes or removal by opening an issue.
