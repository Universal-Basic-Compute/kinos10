# KinKong Market Sentiment Analysis Framework

This document outlines KinKong's approach to market sentiment analysis for Solana AI tokens, particularly UBC and COMPUTE.

## 4-Indicator Sentiment Model

KinKong uses a proprietary 4-indicator approach to determine market sentiment:

### 1. Technical Momentum (TM)

**Data Sources:**
- RSI across multiple timeframes (1H, 4H, 1D)
- MACD histogram slope and crossovers
- Bollinger Band position and width
- ADX strength and direction

**Calculation:**
```
TM = (RSI_Score * 0.3) + (MACD_Score * 0.3) + (BB_Score * 0.2) + (ADX_Score * 0.2)
```

**Interpretation:**
- TM > 70: Strong bullish momentum
- TM 55-70: Moderate bullish momentum
- TM 45-55: Neutral momentum
- TM 30-45: Moderate bearish momentum
- TM < 30: Strong bearish momentum

### 2. On-Chain Activity (OCA)

**Data Sources:**
- Transaction volume (24h, 7d)
- Active addresses (new and returning)
- Token velocity
- Whale wallet movements
- Staking/unstaking activity

**Calculation:**
```
OCA = (Volume_Score * 0.25) + (Address_Score * 0.25) + (Velocity_Score * 0.2) + (Whale_Score * 0.15) + (Staking_Score * 0.15)
```

**Interpretation:**
- OCA > 75: Extremely high activity
- OCA 60-75: High activity
- OCA 40-60: Normal activity
- OCA 25-40: Low activity
- OCA < 25: Extremely low activity

### 3. Social Sentiment (SS)

**Data Sources:**
- Twitter mention volume and sentiment
- Discord/Telegram activity
- Reddit post sentiment
- Trading view ideas
- Google search trends

**Calculation:**
```
SS = (Twitter_Score * 0.3) + (Discord_Score * 0.25) + (Reddit_Score * 0.2) + (TradingView_Score * 0.15) + (Google_Score * 0.1)
```

**Interpretation:**
- SS > 80: Extremely bullish (potential top signal)
- SS 65-80: Bullish
- SS 45-65: Neutral
- SS 30-45: Bearish
- SS < 30: Extremely bearish (potential bottom signal)

### 4. Liquidity Depth (LD)

**Data Sources:**
- Order book depth (bids vs asks)
- Liquidity pool reserves
- Bid-ask spread
- Slippage metrics
- Open interest in derivatives

**Calculation:**
```
LD = (OrderBook_Score * 0.3) + (Pool_Score * 0.3) + (Spread_Score * 0.2) + (Slippage_Score * 0.1) + (OI_Score * 0.1)
```

**Interpretation:**
- LD > 70: Deep liquidity
- LD 50-70: Adequate liquidity
- LD 30-50: Thin liquidity
- LD < 30: Very thin liquidity (high volatility risk)

## Composite Sentiment Index (CSI)

The four indicators are combined into a Composite Sentiment Index:

```
CSI = (TM * 0.35) + (OCA * 0.25) + (SS * 0.2) + (LD * 0.2)
```

**Market Sentiment Classification:**
- CSI > 75: Strongly Bullish
- CSI 60-75: Bullish
- CSI 45-60: Neutral
- CSI 30-45: Bearish
- CSI < 30: Strongly Bearish

## Portfolio Allocation Adjustments

KinKong automatically adjusts portfolio allocations based on the Composite Sentiment Index:

### Strongly Bullish (CSI > 75)
- Trading allocation: 70% of portfolio
- Liquidity providing: 20% of portfolio
- Cash reserve: 10% of portfolio
- Position sizing: 100-120% of baseline
- Stop loss: Standard (1 ATR)
- Take profit: Extended (3-5x risk)

### Bullish (CSI 60-75)
- Trading allocation: 60% of portfolio
- Liquidity providing: 30% of portfolio
- Cash reserve: 10% of portfolio
- Position sizing: 100% of baseline
- Stop loss: Standard (1 ATR)
- Take profit: Standard (2-3x risk)

### Neutral (CSI 45-60)
- Trading allocation: 40% of portfolio
- Liquidity providing: 40% of portfolio
- Cash reserve: 20% of portfolio
- Position sizing: 80% of baseline
- Stop loss: Standard (1 ATR)
- Take profit: Standard (2-3x risk)

### Bearish (CSI 30-45)
- Trading allocation: 30% of portfolio
- Liquidity providing: 30% of portfolio
- Cash reserve: 40% of portfolio
- Position sizing: 60% of baseline
- Stop loss: Tight (0.75 ATR)
- Take profit: Conservative (1.5-2x risk)

### Strongly Bearish (CSI < 30)
- Trading allocation: 20% of portfolio
- Liquidity providing: 20% of portfolio
- Cash reserve: 60% of portfolio
- Position sizing: 40% of baseline
- Stop loss: Very tight (0.5 ATR)
- Take profit: Conservative (1.5x risk)

## Sentiment Divergence Signals

KinKong monitors for divergences between the four sentiment indicators, which often precede major market moves:

### Bullish Divergences
- Technical Momentum bearish BUT Social Sentiment improving
- On-Chain Activity increasing BUT Technical Momentum bearish
- Liquidity Depth improving BUT Technical Momentum bearish

### Bearish Divergences
- Technical Momentum bullish BUT Social Sentiment deteriorating
- On-Chain Activity decreasing BUT Technical Momentum bullish
- Liquidity Depth deteriorating BUT Technical Momentum bullish

Divergences trigger special alerts in KinKong's trading system and may override the standard portfolio allocation model.
