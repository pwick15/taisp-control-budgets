# dataset-glm53-tm-n500-strip: the partial first pass

**Do not analyse the `.partial.csv` files here.** The complete run of the same name lives in
`results/` and is the one to use.

The first pass returned 500 honest and 499 attack samples. The single missing sample, attack
id 430, failed with `RetryError(APIError)`: a transient provider error that exhausted its
retries.

A repair pass re-ran the same configuration with the same settings, including
`MONITOR_STREAM=1`, which this arm used. Inspect's monitor cache replayed the 999 samples
already scored and generated only the missing one, so the repair **billed $0.033** against a
cold cost of $14.62 for the configuration. The run is now 500/500.

This is also the clearest illustration of why the cost column needed separating into two
quantities: this execution was invoiced 3.3 cents, while running the configuration from
cold costs $14.62. Neither number is wrong, and they answer different questions.

The raw log of the partial pass is kept outside git at `logs-superseded/`.
