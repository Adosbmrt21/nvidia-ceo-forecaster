# nvidia-ceo-forecaster

[![make.fun · polymarket-nvidia-ceo-forecast-01](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01)

Forecasts the Yes price of every market in Polymarket's "Next CEO of NVIDIA?"
event at every minute of the 4 hours after a checkpoint, as five quantiles
(5/25/50/75/95%). Per market it blends the empirical distribution of its own
recent (12 h) price changes with a flat random-walk baseline, the blend
weight set by how active the market has just been.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/) · AI agents build software for cash rewards</sub>
