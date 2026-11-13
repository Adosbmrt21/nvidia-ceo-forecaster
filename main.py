"""Forecaster for Polymarket's "Next CEO of NVIDIA?" event (make.fun bounty).

For every market in a case, forecast the five quantiles (5/25/50/75/95%) of
its Yes price at each of the 240 minutes after the checkpoint.

Idea: prices here are steppy random walks whose temper differs per market
and per hour. A single fixed spread (the house baseline's 0.0025/sqrt-min)
is right on average and wrong for almost every individual market. So:

1. From the market's own last 720 minutes, take the empirical distribution
   of price changes at anchor horizons (1..240 minutes) and interpolate the
   five quantiles across horizons in sqrt(h) space. Recent data only: the
   temper of the last 12 hours predicts the next 4 far better than the
   temper of three days ago.
2. Measure how active the market has been in that window (mean absolute
   10-minute change, relative to the baseline's expectation) and blend the
   empirical forecast with the baseline's flat random-walk forecast: quiet
   markets trust the empirical rows (weight up to 0.90), hot markets lean
   back on the baseline (weight down to 0.35), because a hot market's own
   recent jumps are the noisiest guide to its next ones.
3. Rows are clamped to [0, 1], forced non-decreasing across the quantile
   levels and rounded to 6 decimals. The program is a pure function of its
   input, so two runs of a case agree byte for byte.

Standard library only, no network. Reads <case>.in from the input dir,
writes <case>.out to the output dir (MAKEFUN_INPUT_DIR / MAKEFUN_OUTPUT_DIR
stand in for /input and /output outside the grader).
"""
import json
import math
import os

TAUS = (0.05, 0.25, 0.5, 0.75, 0.95)
Z = (-1.644854, -0.67449, 0.0, 0.67449, 1.644854)
BASE_SIGMA = 0.0025
WINDOW = 720
ANCHORS = (1, 3, 10, 30, 60, 120, 240)
# Baseline's expected mean |change| over 10 minutes: sigma*sqrt(10)*E|N(0,1)|.
BASE_MAD10 = 0.0025 * math.sqrt(10) * 0.7978845608


def _quantile(sorted_vals, tau):
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _anchor_quantiles(prices, horizon, stride=3):
    n = len(prices)
    if n <= horizon + 30:
        return None
    deltas = sorted(prices[t] - prices[t - horizon] for t in range(horizon, n, stride))
    return [_quantile(deltas, tau) for tau in TAUS]


def _interp(aq, h):
    keys = sorted(aq)
    sh = math.sqrt(h)
    if h <= keys[0]:
        k = keys[0]
        scale = sh / math.sqrt(k)
        return [q * scale for q in aq[k]]
    if h >= keys[-1]:
        k = keys[-1]
        scale = sh / math.sqrt(k)
        return [q * scale for q in aq[k]]
    for a, b in zip(keys, keys[1:]):
        if a <= h <= b:
            sa, sb = math.sqrt(a), math.sqrt(b)
            w = (sh - sa) / (sb - sa)
            return [aq[a][i] * (1.0 - w) + aq[b][i] * w for i in range(5)]
    return aq[keys[-1]]


def _baseline_rows(x, horizon):
    rows = []
    for h in range(1, horizon + 1):
        root = math.sqrt(h)
        rows.append([min(1.0, max(0.0, x + z * BASE_SIGMA * root)) for z in Z])
    return rows


def _empirical_rows(prices, horizon):
    aq = {}
    for anchor in ANCHORS:
        q = _anchor_quantiles(prices, anchor)
        if q is not None:
            aq[anchor] = q
    if not aq:
        return None
    x = prices[-1]
    rows = []
    for h in range(1, horizon + 1):
        qs = _interp(aq, h)
        rows.append([x + q for q in qs])
    return rows


def forecast_market(prices, horizon):
    """Five quantiles of the price at each minute 1..horizon after the last."""
    if not prices:
        # No price by the checkpoint: nothing to centre on. Flat rows at the
        # middle keep the case valid instead of crashing the whole run.
        return [[0.5, 0.5, 0.5, 0.5, 0.5] for _ in range(horizon)]
    x = prices[-1]
    base = _baseline_rows(x, horizon)
    try:
        window = prices[-WINDOW:] if len(prices) > WINDOW else list(prices)
        emp = _empirical_rows(window, horizon)
        if emp is None:
            emp = base
        if len(window) > 60:
            jumps = [abs(window[i] - window[i - 10]) for i in range(10, len(window), 10)]
            mad10 = sum(jumps) / len(jumps)
        else:
            mad10 = 0.0
        ratio = mad10 / BASE_MAD10 if mad10 > 0.0 else 0.0
        weight = 1.0 - 0.35 * ratio
        if weight > 0.90:
            weight = 0.90
        elif weight < 0.35:
            weight = 0.35
        rows = []
        for emp_row, base_row in zip(emp, base):
            row = []
            prev = 0.0
            for e, b in zip(emp_row, base_row):
                v = weight * e + (1.0 - weight) * b
                if v < 0.0:
                    v = 0.0
                elif v > 1.0:
                    v = 1.0
                if v < prev:
                    v = prev
                prev = v
                row.append(round(v, 6) + 0.0)
            rows.append(row)
        return rows
    except Exception:
        return [[round(v, 6) + 0.0 for v in row] for row in base]


def run(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for name in sorted(os.listdir(input_dir)):
        if not name.endswith('.in'):
            continue
        with open(os.path.join(input_dir, name), 'r', encoding='utf-8') as fh:
            case = json.load(fh)
        horizon = int(case['horizon_minutes'])
        forecasts = []
        for market in case['markets']:
            forecasts.append({'id': market['id'],
                              'q': forecast_market(market['prices'], horizon)})
        with open(os.path.join(output_dir, name[:-3] + '.out'), 'w', encoding='utf-8') as fh:
            json.dump({'forecasts': forecasts}, fh, separators=(',', ':'))


def main():
    run(os.environ.get('MAKEFUN_INPUT_DIR', '/input'),
        os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))


if __name__ == '__main__':
    main()
