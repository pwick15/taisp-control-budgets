# Superseded runs

A run in this folder is an **incomplete execution that a later, complete execution of the
same configuration replaces.** It is kept because the failure itself is part of the record:
the error rate, the cause and the sample ids that were lost are all worth being able to look
up later. It is kept *here*, rather than in `results/`, because every analysis script in this
repo discovers runs by globbing `results/*-samples.csv`. Moving a superseded run one level
down removes it from all of them at once, so no consumer has to remember a filter and none
can silently include it.

**Nothing in this folder may be analysed, plotted, averaged or compared.** It is not a
replicate of its successor and it is not an independent sample. Read `SUPERSEDED.md` beside
each file for what went wrong and which run replaces it.

## The rule this folder exists to enforce

A run labelled `n500` must deliver **500 honest and 500 attack samples, all scored**. A run
that delivers fewer is not a smaller run, it is a broken one: the samples that go missing
are not a random subset. In the case that prompted this folder, the losses were a strict
tail of the dataset caused by an API credit exhaustion partway through, and they fell
unevenly across the two arms (20 honest against 37 attack), which moved the measured recall.

When a configuration has to be executed more than once to reach 500, that is fine and
expected. The later execution reuses the earlier scores through Inspect's monitor cache, so
it costs only the samples that were actually missing. What matters is that exactly one
execution, the complete one, is treated as the run.
