# dataset500-sonnet55-um-effortlow-strip is superseded by dataset500-sonnet55-um-effortlow-v2-strip

**Do not analyse this run.** It is kept only as a record of the failure.

## What happened

The run was launched for 500 honest and 500 attack samples and delivered **480 honest and
463 attack**. All 57 missing samples failed with the same provider error:

    BadRequestError 400 invalid_request_error:
    "Your credit balance is too low to access the Anthropic API"

The Anthropic credit ran out partway through, so the losses are a **contiguous tail of the
dataset**, not a random subset: attack lost dataset positions 462 and 464-499, honest lost
480-499. The two arms lost unequal counts and the loss is nested (every lost honest sample
is also a lost attack sample, McNemar exact p = 1.5e-5).

## Why that mattered

Losing attack samples at a higher rate than honest ones moves measured recall. The lost 37
attacks were *more* suspicious than average (mean 0.635 against 0.580 over the arm), so this
run **understates** its own recall: 0.8315 here against 0.8380 on the complete run, at audit
budgets from 1% to 10%.

## What replaces it

dataset500-sonnet55-um-effortlow-v2-strip re-ran the same configuration and reached 500/500. It is the repaired run, not a second
opinion: 942 of its 1000 rows were replayed from Inspect's monitor cache and carry suspicion
scores **identical to this run's on all 942 shared rows**, and only 58 were generated fresh,
precisely the 57 failures above plus honest sample 184.

**The pair therefore shares almost every row by construction. Never treat them as two
independent runs, and never compute run-to-run variance or reproducibility from them.**
