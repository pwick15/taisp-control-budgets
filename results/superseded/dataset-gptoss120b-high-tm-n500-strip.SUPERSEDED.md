# dataset-gptoss120b-high-tm-n500-strip: the partial first pass

**Do not analyse the `.partial.csv` files here.** The complete run of the same name lives in
`results/` and is the one to use.

The first pass returned 499 honest and 500 attack samples. The single missing sample, honest
id 804, failed with `RetryError(APIError)`: a transient provider error that exhausted its
retries after 2,351 seconds.

A repair pass re-ran the same configuration. Inspect's monitor cache replayed the 999
samples already scored and generated only the missing one, so the repair **billed $0.000**
with 999 of 1000 samples served from cache. The run is now 500/500 and sample 804 is
present.

The raw log of the partial pass is kept outside git at `logs-superseded/`.
