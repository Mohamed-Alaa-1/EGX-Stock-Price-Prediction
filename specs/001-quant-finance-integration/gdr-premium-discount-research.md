# Research Notes: Local-first GDR Premium/Discount Series (Cross-listed Stocks)

**Goal**: compute a historical premium/discount series between a local listing (e.g., EGX) and an overseas GDR/ADR listing, **without paid market-data APIs**, in a way that works offline once data is cached / imported.

**Definition** (typical): if 1 GDR represents $k$ local shares, local currency is $\mathrm{LCY}$, GDR currency is $\mathrm{FCY}$.

- Local implied price in LCY: $P^{\mathrm{implied}}_t = \frac{P^{\mathrm{gdr}}_t \times \mathrm{FX}_{t}(\mathrm{FCY}\rightarrow\mathrm{LCY})}{k}$
- Premium/discount: $\Delta_t = \frac{P^{\mathrm{implied}}_t - P^{\mathrm{local}}_t}{P^{\mathrm{local}}_t}$

(Report as %: $100\times\Delta_t$.)

---

## Data sourcing options (free / local-first)

### 1) Manual CSV import (recommended “always works” fallback)
This repo already supports user CSVs via the `csv_import` provider (expects `date,open,high,low,close[,volume][,adjusted_close]`).

Local-first pattern:
- Users can import **three** separate series as CSV:
  - local listing prices (e.g., `COMI.csv`)
  - GDR listing prices (e.g., `COMI_GDR.csv`)
  - FX series (e.g., `USD_EGP.csv` or `GBP_EGP.csv`)

Why this matters:
- Cross-listed tickers are often **incomplete** in free automated sources.
- FX for some currencies (notably EGP) is not consistently available from “free-no-key” endpoints.

### 2) Stooq (free CSV endpoint; best-effort coverage)
Stooq exposes simple historical OHLCV CSV downloads without an API key.

- Example schema observed: header `Date,Open,High,Low,Close,Volume`.
- Daily series URL pattern:
  - `https://stooq.com/q/d/l/?s={symbol}&i=d`

Notes:
- Coverage is strongest for US equities and some international listings; it may or may not cover specific GDRs.
- If used, treat Stooq as a *fallback* provider for foreign listings where it works.

### 3) “Public endpoints” that are brittle or gated (use cautiously)
- Yahoo Finance’s direct “download CSV” endpoint commonly returns authorization errors (e.g., HTTP 401) unless you replicate its session/crumb flow; the `yfinance` library typically handles this but it can change over time.
- TradingView-style endpoints/scrapes can violate ToS or break frequently; this repo already treats TradingView as optional.

Pragmatic guidance:
- Prefer **libraries** that encapsulate the quirks (e.g., `yfinance`), and keep manual CSV import as the safety net.

### 4) Free-key providers (not paid, but require user API key)
If you allow “optional keys” (still free tier), you gain more reliable FX and global listings.

- Alpha Vantage:
  - Free API key available; daily FX and daily equity time series exist.
  - Limitations: rate limits, and “full history” for some endpoints may be premium.

Treat as an **opt-in** provider tier in the UI (user pastes key into settings).

---

## FX sourcing options (and reality for EGP)

### A) User-imported FX (most robust)
- Works offline.
- Users can source EGP FX from their broker/bank export, central bank PDF/CSV, or any authoritative source they trust.
- You can standardize on a single series definition (e.g., *mid* or *official*), and store provenance in metadata.

### B) ECB euro reference rates (free, wide majors; EUR base)
ECB publishes historical EUR reference rates as a CSV.

Important implementation detail discovered in practice:
- The ECB CSV lines can be extremely long; if your ingestion pipeline reads it as text, you may encounter **line folding / row wrapping** artifacts. A robust parser should treat lines that **do not start with a date** (`YYYY-MM-DD,`) as a continuation of the previous row.

Coverage caveat:
- ECB is great for majors (USD, GBP, JPY, etc.). It typically won’t solve EGP directly.

### C) Frankfurter (free; ECB-backed convenience API)
- Great for majors; supports `base` and `rates` query patterns.
- Practical caveat: it often does **not** include exotic currencies like EGP.

### D) FRED (free with API key; many macro/FX series)
- FRED has an API and a very broad catalog.
- Requires an API key.
- Coverage of a specific currency pair (e.g., USD/EGP) should be treated as “check availability,” not assumed.

---

## Caching & graceful degradation (local app concerns)

This repo already caches `PriceSeries` to `data/cache/{SYMBOL}.parquet` with provider metadata.

Recommended approach for GDR premium series:

1) Cache **raw inputs** separately (local, GDR, FX)
- Cache each input series by its own symbol key (`COMI`, `COMI_GDR`, `USD_EGP`).
- Keep provenance per series (`provider`, `fetched_at`, `range_start/end`).

2) Derive premium series on demand (don’t treat it as a primary cached truth)
- Compute premium/discount as a *derived view* from cached primitives.
- Optionally cache the derived result for speed, but always be able to recompute.

3) Missing-data policy (graceful degradation)
- **Date alignment**: default to “intersection of available dates.” This avoids misleading calculations.
- **FX gaps**:
  - If FX is missing for a date, optionally use last-known FX within a small max gap (e.g., 3–5 business days) and mark the point as *imputed*.
  - If the gap exceeds max gap, skip the premium for that date.
- **Market holiday mismatch**: local and foreign markets have different holidays; expect missing on one side.

4) Staleness / offline behavior
- If refresh fails (no internet, provider down), return cached data and surface a status:
  - `fresh` (recent fetch)
  - `stale` (older than TTL)
  - `offline` (fetch failed, using cache)

Implementation note:
- Today, `CacheStore.load()` returns cached series without TTL checks. For GDR workflows, consider adding a staleness check at the service layer (don’t break existing behavior; just annotate “stale” in UI/logging).

---

## Structuring providers & mappings in a local-first app

### Provider separation
Keep “what is being fetched” separate from “how it is used.”

Recommended minimal interfaces:
- `PriceProvider` (already exists as `BaseProvider` returning `PriceSeries`)
- `FxProvider` (new; returns a time series of rates, could reuse `PriceSeries` or introduce `FxRateSeries`)

Then build a “premium calculator” service that depends only on:
- `PriceService.get_series(local_symbol)`
- `PriceService.get_series(gdr_symbol)`
- `FxService.get_series(pair_symbol)`

### Cross-listing mapping registry
Add a local mapping file under `data/metadata/` (JSON or YAML) to define cross-list relationships.

Suggested schema (conceptual):
- `local_symbol`: `COMI`
- `local_exchange`: `EGX`
- `local_currency`: `EGP`
- `gdr_symbol`: `CIBGDR.L` (example)
- `gdr_exchange`: `LSE`
- `gdr_currency`: `USD` or `GBP`
- `ratio_local_per_gdr`: integer or float `k`
- `fx_pair`: `USD_EGP` (or `GBP_EGP`)
- `preferred_price_providers`: ordered list (e.g., `tradingview`, `yfinance`, `stooq`, `csv_import`)
- `preferred_fx_providers`: ordered list (e.g., `ecb`, `frankfurter`, `alphavantage`, `csv_import`)
- optional `notes` / `source_links`

Why local registry:
- The **ratio** (local shares per GDR) is essential and usually not discoverable reliably from free quote endpoints.
- Tickering conventions differ per provider; you need a stable, user-editable mapping layer.

### Symbol naming
Use clear, non-colliding symbols for cached series:
- local: `COMI`
- gdr: `COMI_GDR` (internal) OR use provider-specific ticker but wrap it with mapping metadata
- fx: `USD_EGP` (or `FX:USD/EGP`)

The simplest approach in this repo (given `CacheStore.get_cache_path(symbol)`): treat each series as a unique `symbol` string that maps to a cache file.

---

## Decision / Rationale / Alternatives

### Decision
Adopt a **local-first, mapping-driven** approach:
1) Raw series acquisition uses a **provider registry with fallback**.
2) The app always supports **manual CSV import** for local, GDR, and FX series.
3) Automated free providers are “best-effort”:
   - Prices: `yfinance` (existing), TradingView (existing optional), add Stooq where it helps.
   - FX: user-import first; optionally ECB/Frankfurter for major currencies; optional free-key provider (Alpha Vantage or FRED) for broader coverage.
4) Premium/discount is computed as a **derived series** from cached primitives with explicit missing-data rules.

### Rationale
- **Reliability**: CSV import guarantees functionality for any cross-listed pair even when free endpoints are incomplete.
- **Local-first**: once cached/imported, the app works offline.
- **Maintainability**: providers can come and go; the mapping registry + fallback chain isolates provider quirks.
- **Correctness**: cross-list ratios and FX definitions are explicit and user-auditable.

### Alternatives (considered, not chosen)
- **Single-provider dependency** (e.g., only `yfinance`): simpler, but fails unpredictably for EGX/GDR coverage gaps.
- **Scraping-first approach** (web scraping for prices/FX): high fragility and ToS risk; not a good default for a desktop app.
- **Paid market data API**: solves coverage and corporate actions but violates the “no paid APIs” constraint.
- **Compute premium from only spot FX** (latest FX applied to history): fast but incorrect for time series analysis.

---

## Practical pitfalls to call out in implementation

- **Time zone / close alignment**: EGX close and LSE/NYSE close differ; “same calendar date” can mix different information sets. For a first iteration, intersection-of-dates is acceptable; later, align by “as-of local close time.”
- **Corporate actions / ratio changes**: GDR ratios can change. Start with a static ratio in metadata; document that historical discontinuities may occur if ratio changes aren’t modeled.
- **Bid/ask vs close**: premium depends on the chosen price definition; default to close and label it.
