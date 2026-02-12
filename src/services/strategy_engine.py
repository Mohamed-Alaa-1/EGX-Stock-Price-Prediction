"""
Investment-assistant strategy engine.

Ensemble-weights ML forecast + technical indicators + VaR risk + ADF/Hurst
regime to produce a risk-first StrategyRecommendation with:
    Action (Buy/Sell/Hold), Entry Zone, Target Exit, Stop-Loss,
    Conviction Score, Evidence Panel, and Logic Summary.

Constitution mandates:
    - Risk-First: default HOLD on uncertainty.
    - Stop-Loss always included for BUY/SELL (based on 1-day VaR).
    - Conviction always included (0–100), reduced on signal disagreement.
    - Weights explicitly disclosed.
    - UI separates raw forecast from assistant recommendation.

References:
    specs/001-investment-assistant/spec.md  (FR-012 .. FR-021)
    specs/001-investment-assistant/data-model.md
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from core.config import Config
from core.indicators import calculate_ema, calculate_macd, calculate_rsi
from core.quant import calculate_hurst, calculate_var
from core.schemas import (
    EvidenceDirection,
    EvidenceSignal,
    EvidenceSource,
    ForecastResult,
    HurstRegime,
    PriceSeries,
    RiskMetricsSnapshot,
    StatisticalValidationResult,
    StrategyAction,
    StrategyRecommendation,
)
from core.series_utils import get_returns

# ---------------------------------------------------------------------------
# Default ensemble weights (FR-013)
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {
    "ml": 0.35,
    "technical": 0.30,
    "regime": 0.20,
    "risk": 0.15,
}

# Action thresholds (FR-016)
_BUY_THRESHOLD = 0.20
_SELL_THRESHOLD = -0.20
_MIN_CONVICTION = 30

# Risk-distance clamp bounds (FR-017)
_MIN_RISK_DISTANCE = 0.005  # 0.5 %
_MAX_RISK_DISTANCE = 0.10   # 10 %


class StrategyEngine:
    """
    Produces a :class:`StrategyRecommendation` for a given symbol by
    blending four evidence groups:

    1. **ML forecast** directional bias (weight 0.35)
    2. **Technical indicators** – RSI / MACD / EMA (weight 0.30)
    3. **Regime** – Hurst exponent classification (weight 0.20)
    4. **Quantitative risk** – VaR assessment (weight 0.15)

    The engine follows a *risk-first* philosophy: when required inputs are
    missing, incomplete, or strongly conflicting the default action is HOLD.
    """

    def __init__(
        self,
        weights: Optional[dict[str, float]] = None,
    ) -> None:
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_recommendation(
        self,
        series: PriceSeries,
        forecast: Optional[ForecastResult] = None,
        risk_snapshot: Optional[RiskMetricsSnapshot] = None,
        validation_result: Optional[StatisticalValidationResult] = None,
    ) -> StrategyRecommendation:
        """
        Compute a full strategy recommendation.

        Args:
            series: Historical OHLCV data (required).
            forecast: ML / baseline forecast result (optional).
            risk_snapshot: Pre-computed VaR + Sharpe (optional; computed
                internally when omitted).
            validation_result: Pre-computed ADF + Hurst (optional; computed
                internally when omitted).

        Returns:
            A :class:`StrategyRecommendation` with action, entry zone,
            stop-loss, target exit, conviction, evidence, and logic summary.
        """

        symbol = series.symbol.upper()
        current_price = series.get_latest_close()
        as_of = series.get_latest_bar().date

        # ---- Compute returns for risk / regime ----------------------------
        returns = get_returns(series, Config.DEFAULT_RETURN_TYPE)

        # ---- 1. ML signal --------------------------------------------------
        ml_score, ml_evidence = self._ml_signal(forecast, current_price)

        # ---- 2. Technical signal -------------------------------------------
        tech_score, tech_evidence = self._technical_signal(series, current_price)

        # ---- 3. Regime signal ----------------------------------------------
        regime_score, regime_label, regime_evidence = self._regime_signal(
            returns,
            validation_result,
        )

        # ---- 4. Risk signal ------------------------------------------------
        risk_score, risk_distance, risk_evidence = self._risk_signal(
            returns,
            current_price,
            risk_snapshot,
        )

        # ---- Blend (FR-014) ------------------------------------------------
        blended = (
            self.weights["ml"] * ml_score
            + self.weights["technical"] * tech_score
            + self.weights["regime"] * regime_score
            + self.weights["risk"] * risk_score
        )

        # ---- Conviction (FR-015) -------------------------------------------
        scores = [ml_score, tech_score, regime_score, risk_score]
        blended_sign = 1 if blended >= 0 else -1
        alignment = sum(
            1
            for s in scores
            if (s >= 0 and blended_sign >= 0) or (s < 0 and blended_sign < 0)
        ) / 4.0
        conviction = round(100 * min(1.0, abs(blended)) * alignment)
        conviction = max(0, min(100, conviction))

        # ---- Action (FR-016) -----------------------------------------------
        if blended >= _BUY_THRESHOLD and conviction >= _MIN_CONVICTION:
            action = StrategyAction.BUY
        elif blended <= _SELL_THRESHOLD and conviction >= _MIN_CONVICTION:
            action = StrategyAction.SELL
        else:
            action = StrategyAction.HOLD

        # ---- Entry / Target / Stop (FR-017 .. FR-020) ----------------------
        entry_lower: Optional[float] = None
        entry_upper: Optional[float] = None
        target_exit: Optional[float] = None
        stop_loss: Optional[float] = None
        risk_distance_pct: Optional[float] = None

        if action != StrategyAction.HOLD and risk_distance is not None:
            rd = risk_distance
            risk_distance_pct = round(rd * 100, 4)

            if action == StrategyAction.BUY:
                entry_lower = round(current_price * (1 - rd), 4)
                entry_upper = round(current_price * (1 + 0.25 * rd), 4)
                stop_loss = round(entry_lower * (1 - rd), 4)
            else:  # SELL
                entry_lower = round(current_price * (1 - 0.25 * rd), 4)
                entry_upper = round(current_price * (1 + rd), 4)
                stop_loss = round(entry_upper * (1 + rd), 4)

            target_exit = self._compute_target(
                action,
                current_price,
                rd,
                regime_label,
                forecast,
                series,
            )

        # ---- Evidence buckets ----------------------------------------------
        all_evidence = ml_evidence + tech_evidence + regime_evidence + risk_evidence
        bullish = [e for e in all_evidence if e.direction == EvidenceDirection.BULLISH]
        bearish = [e for e in all_evidence if e.direction == EvidenceDirection.BEARISH]
        neutral = [e for e in all_evidence if e.direction == EvidenceDirection.NEUTRAL]

        # ---- Logic summary (FR-021) ----------------------------------------
        logic = self._build_logic_summary(
            action, conviction, regime_label, bullish, bearish,
        )

        # ---- Raw inputs snapshot -------------------------------------------
        raw_inputs = self._raw_inputs_snapshot(
            ml_score, tech_score, regime_score, risk_score,
            blended, alignment, risk_distance, regime_label,
        )

        return StrategyRecommendation(
            symbol=symbol,
            as_of_date=as_of,
            action=action,
            conviction=conviction,
            regime=regime_label,
            entry_zone_lower=entry_lower,
            entry_zone_upper=entry_upper,
            target_exit=target_exit,
            stop_loss=stop_loss,
            risk_distance_pct=risk_distance_pct,
            evidence_bullish=bullish,
            evidence_bearish=bearish,
            evidence_neutral=neutral,
            logic_summary=logic,
            raw_inputs=raw_inputs,
        )

    # ------------------------------------------------------------------
    # Signal extractors (private)
    # ------------------------------------------------------------------

    def _ml_signal(
        self,
        forecast: Optional[ForecastResult],
        current_price: float,
    ) -> tuple[float, list[EvidenceSignal]]:
        """
        Extract directional score from ML forecast.

        Score = clamp((predicted_close / current_price - 1) * 10, -1, 1)
        """
        if forecast is None or current_price <= 0:
            return 0.0, [
                EvidenceSignal(
                    source=EvidenceSource.ML_FORECAST,
                    direction=EvidenceDirection.NEUTRAL,
                    weight=self.weights["ml"],
                    score=0.0,
                    summary="ML forecast unavailable – treated as neutral.",
                    raw_value=None,
                ),
            ]

        pct_move = (forecast.predicted_close / current_price) - 1.0
        score = float(np.clip(pct_move * 10.0, -1.0, 1.0))

        direction = (
            EvidenceDirection.BULLISH
            if score > 0.05
            else EvidenceDirection.BEARISH
            if score < -0.05
            else EvidenceDirection.NEUTRAL
        )

        return score, [
            EvidenceSignal(
                source=EvidenceSource.ML_FORECAST,
                direction=direction,
                weight=self.weights["ml"],
                score=round(score, 4),
                summary=(
                    f"ML predicts {forecast.predicted_close:.2f} "
                    f"({pct_move:+.2%} vs current {current_price:.2f})."
                ),
                raw_value={
                    "predicted_close": forecast.predicted_close,
                    "current_price": current_price,
                    "pct_move": round(pct_move, 6),
                },
            ),
        ]

    def _technical_signal(
        self,
        series: PriceSeries,
        current_price: float,
    ) -> tuple[float, list[EvidenceSignal]]:
        """
        Compute composite technical score from RSI, MACD, EMA.

        Each sub-indicator maps to [-1, +1]:
            RSI < 30 → +1 (oversold → bullish)
            RSI > 70 → -1 (overbought → bearish)
            else      linear interpolation
            MACD histogram > 0 → bullish (scaled)
            EMA: price > EMA(50) → bullish, < → bearish
        """
        evidence: list[EvidenceSignal] = []
        sub_scores: list[float] = []

        # --- RSI ---------------------------------------------------------
        try:
            rsi_series = calculate_rsi(series, period=14)
            rsi_val = float(rsi_series.dropna().iloc[-1])
            if rsi_val < 30:
                rsi_score = 1.0
            elif rsi_val > 70:
                rsi_score = -1.0
            else:
                rsi_score = float(np.interp(rsi_val, [30, 70], [1.0, -1.0]))
            sub_scores.append(rsi_score)
            direction = (
                EvidenceDirection.BULLISH
                if rsi_score > 0.1
                else EvidenceDirection.BEARISH
                if rsi_score < -0.1
                else EvidenceDirection.NEUTRAL
            )
            evidence.append(
                EvidenceSignal(
                    source=EvidenceSource.RSI,
                    direction=direction,
                    weight=self.weights["technical"],
                    score=round(rsi_score, 4),
                    summary=f"RSI({14}) = {rsi_val:.1f}.",
                    raw_value=round(rsi_val, 2),
                )
            )
        except Exception:
            pass

        # --- MACD --------------------------------------------------------
        try:
            macd_line, signal_line, histogram = calculate_macd(series)
            hist_val = float(histogram.dropna().iloc[-1])
            macd_val = float(macd_line.dropna().iloc[-1])
            # Normalize histogram relative to price (rough scale)
            norm = hist_val / current_price * 100 if current_price > 0 else 0
            macd_score = float(np.clip(norm, -1.0, 1.0))
            sub_scores.append(macd_score)
            direction = (
                EvidenceDirection.BULLISH
                if macd_score > 0.05
                else EvidenceDirection.BEARISH
                if macd_score < -0.05
                else EvidenceDirection.NEUTRAL
            )
            evidence.append(
                EvidenceSignal(
                    source=EvidenceSource.MACD,
                    direction=direction,
                    weight=self.weights["technical"],
                    score=round(macd_score, 4),
                    summary=f"MACD histogram = {hist_val:.4f}.",
                    raw_value={"macd": round(macd_val, 4), "histogram": round(hist_val, 4)},
                )
            )
        except Exception:
            pass

        # --- EMA(50) -----------------------------------------------------
        try:
            ema50 = calculate_ema(series, period=50)
            ema_val = float(ema50.dropna().iloc[-1])
            if current_price > 0 and ema_val > 0:
                ema_ratio = (current_price - ema_val) / ema_val
                ema_score = float(np.clip(ema_ratio * 10, -1.0, 1.0))
            else:
                ema_score = 0.0
            sub_scores.append(ema_score)
            direction = (
                EvidenceDirection.BULLISH
                if ema_score > 0.05
                else EvidenceDirection.BEARISH
                if ema_score < -0.05
                else EvidenceDirection.NEUTRAL
            )
            evidence.append(
                EvidenceSignal(
                    source=EvidenceSource.EMA,
                    direction=direction,
                    weight=self.weights["technical"],
                    score=round(ema_score, 4),
                    summary=(
                        f"Price {'above' if current_price > ema_val else 'below'} "
                        f"EMA(50) = {ema_val:.2f}."
                    ),
                    raw_value=round(ema_val, 4),
                )
            )
        except Exception:
            pass

        # Composite technical score (average of available sub-indicators)
        if sub_scores:
            composite = float(np.mean(sub_scores))
        else:
            composite = 0.0
            evidence.append(
                EvidenceSignal(
                    source=EvidenceSource.RSI,
                    direction=EvidenceDirection.NEUTRAL,
                    weight=self.weights["technical"],
                    score=0.0,
                    summary="Technical indicators unavailable – neutral.",
                )
            )

        return composite, evidence

    def _regime_signal(
        self,
        returns: pd.Series,
        validation: Optional[StatisticalValidationResult],
    ) -> tuple[float, Optional[HurstRegime], list[EvidenceSignal]]:
        """
        Derive regime classification from Hurst exponent.

        Trending  (H > 0.6) → +0.5  (trend-following is favorable)
        Mean-rev  (H < 0.4) → -0.3  (counter-trend caution)
        Random    otherwise  →  0.0
        """
        hurst_val: Optional[float] = None
        regime: Optional[HurstRegime] = None

        # Prefer pre-computed validation when provided
        if validation is not None and validation.hurst is not None:
            hurst_val = validation.hurst
            regime = validation.hurst_regime
        else:
            # Fall back to internal computation
            hurst_result = calculate_hurst(returns)
            hurst_val = hurst_result.get("hurst")
            regime = hurst_result.get("hurst_regime")

        if hurst_val is None or regime is None:
            return 0.0, None, [
                EvidenceSignal(
                    source=EvidenceSource.HURST,
                    direction=EvidenceDirection.NEUTRAL,
                    weight=self.weights["regime"],
                    score=0.0,
                    summary="Hurst exponent unavailable – regime unknown.",
                ),
            ]

        if regime == HurstRegime.TRENDING:
            score = 0.5
            direction = EvidenceDirection.BULLISH
            label = "trending"
        elif regime == HurstRegime.MEAN_REVERTING:
            score = -0.3
            direction = EvidenceDirection.BEARISH
            label = "mean-reverting"
        else:
            score = 0.0
            direction = EvidenceDirection.NEUTRAL
            label = "random-like"

        return score, regime, [
            EvidenceSignal(
                source=EvidenceSource.HURST,
                direction=direction,
                weight=self.weights["regime"],
                score=round(score, 4),
                summary=f"Hurst = {hurst_val:.3f} → {label} regime.",
                raw_value=round(hurst_val, 4),
            ),
        ]

    def _risk_signal(
        self,
        returns: pd.Series,
        current_price: float,
        risk_snapshot: Optional[RiskMetricsSnapshot],
    ) -> tuple[float, Optional[float], list[EvidenceSignal]]:
        """
        Assess risk via 1-day 95 % VaR.

        - VaR is a negative return; more negative = higher risk.
        - risk_distance = abs(VaR) clamped to [0.5 %, 10 %].
        - Risk score: low risk → +0.5, high risk → −1.0 (scaled).

        Returns (risk_score, risk_distance_fraction | None, evidence).
        """
        var_pct: Optional[float] = None

        if risk_snapshot is not None and risk_snapshot.var_95_pct is not None:
            var_pct = risk_snapshot.var_95_pct
        else:
            var_pct = calculate_var(returns, confidence=0.95)

        if var_pct is None:
            return 0.0, None, [
                EvidenceSignal(
                    source=EvidenceSource.VAR,
                    direction=EvidenceDirection.NEUTRAL,
                    weight=self.weights["risk"],
                    score=0.0,
                    summary="VaR unavailable – risk assessment neutral.",
                ),
            ]

        abs_var = abs(var_pct)  # VaR is negative for losses
        risk_distance = float(np.clip(abs_var, _MIN_RISK_DISTANCE, _MAX_RISK_DISTANCE))

        # Score: higher risk  → more negative score
        # Map abs_var [0, 0.10] → score [+0.5, -1.0]
        risk_score = float(np.interp(abs_var, [0.0, 0.05, 0.10], [0.5, 0.0, -1.0]))

        direction = (
            EvidenceDirection.BULLISH
            if risk_score > 0.1
            else EvidenceDirection.BEARISH
            if risk_score < -0.1
            else EvidenceDirection.NEUTRAL
        )

        return risk_score, risk_distance, [
            EvidenceSignal(
                source=EvidenceSource.VAR,
                direction=direction,
                weight=self.weights["risk"],
                score=round(risk_score, 4),
                summary=(
                    f"1-day 95 % VaR = {var_pct:+.2%}; "
                    f"risk distance = {risk_distance:.2%}."
                ),
                raw_value={
                    "var_95_pct": round(var_pct, 6),
                    "risk_distance": round(risk_distance, 6),
                },
            ),
        ]

    # ------------------------------------------------------------------
    # Target-exit formula (FR-020)
    # ------------------------------------------------------------------

    def _compute_target(
        self,
        action: StrategyAction,
        current_price: float,
        risk_distance: float,
        regime: Optional[HurstRegime],
        forecast: Optional[ForecastResult],
        series: PriceSeries,
    ) -> float:
        """
        Regime-consistent target exit.

        Trend-following → extends toward ML forecast (capped by 4×RD).
        Mean-reverting  → reverts toward EMA(50) (capped by 1.5×RD).
        """

        ml_price = forecast.predicted_close if forecast else None

        if regime == HurstRegime.TRENDING or regime is None:
            # Default to trend-following when regime unknown
            if action == StrategyAction.BUY:
                cap = current_price * (1 + 4 * risk_distance)
                target = min(ml_price, cap) if ml_price else cap
            else:  # SELL
                floor = current_price * (1 - 4 * risk_distance)
                target = max(ml_price, floor) if ml_price else floor
        else:
            # Mean-reverting
            try:
                ema50 = calculate_ema(series, period=50)
                ema_val = float(ema50.dropna().iloc[-1])
            except Exception:
                ema_val = current_price

            if action == StrategyAction.BUY:
                if ema_val > current_price:
                    target = ema_val
                else:
                    target = current_price * (1 + 1.5 * risk_distance)
            else:  # SELL
                if ema_val < current_price:
                    target = ema_val
                else:
                    target = current_price * (1 - 1.5 * risk_distance)

        return round(target, 4)

    # ------------------------------------------------------------------
    # Logic summary builder (FR-021)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_logic_summary(
        action: StrategyAction,
        conviction: int,
        regime: Optional[HurstRegime],
        bullish: list[EvidenceSignal],
        bearish: list[EvidenceSignal],
    ) -> str:
        """
        Human-readable explanation that mentions: action, conviction,
        regime, and top 2–4 contributing signals.
        """
        regime_label = regime.value.replace("_", "-") if regime else "unknown"

        parts: list[str] = [f"{action.value.upper()} (conviction {conviction}%)."]

        if regime:
            parts.append(f"Market regime: {regime_label}.")

        # Top bullish
        if bullish:
            top = sorted(bullish, key=lambda e: abs(e.score), reverse=True)[:2]
            labels = [e.summary for e in top]
            parts.append("Bullish: " + " ".join(labels))

        # Top bearish
        if bearish:
            top = sorted(bearish, key=lambda e: abs(e.score), reverse=True)[:2]
            labels = [e.summary for e in top]
            parts.append("Bearish: " + " ".join(labels))

        if action == StrategyAction.HOLD and not bullish and not bearish:
            parts.append("Insufficient or conflicting signals – defaulting to HOLD.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Raw-inputs snapshot (auditing)
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_inputs_snapshot(
        ml_score: float,
        tech_score: float,
        regime_score: float,
        risk_score: float,
        blended: float,
        alignment: float,
        risk_distance: Optional[float],
        regime: Optional[HurstRegime],
    ) -> dict:
        return {
            "scores": {
                "ml": round(ml_score, 4),
                "technical": round(tech_score, 4),
                "regime": round(regime_score, 4),
                "risk": round(risk_score, 4),
                "blended": round(blended, 4),
            },
            "alignment": round(alignment, 4),
            "risk_distance": round(risk_distance, 6) if risk_distance else None,
            "regime": regime.value if regime else None,
            "weights": dict(DEFAULT_WEIGHTS),
        }
