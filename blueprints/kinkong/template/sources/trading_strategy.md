# KinKong Trading Strategy

This document outlines KinKong's core trading approach for Solana AI tokens, particularly UBC and COMPUTE.

## Trading Philosophy

KinKong's trading philosophy is built on four core principles:

1. **Data-Driven Decisions**
   - Analyze millions of data points per second
   - Remove emotional bias from trading decisions
   - Identify patterns invisible to human traders

2. **24/7 Market Coverage**
   - Continuous monitoring while humans sleep
   - Instant reaction to market developments
   - Never miss a trading opportunity
   - 4x daily trading windows for optimal execution

3. **Risk Management First**
   - Position sizing based on volatility metrics
   - Strict stop-loss discipline
   - Portfolio diversification across strategies
   - Dynamic position sizing based on market conditions

4. **Ecosystem Support**
   - Focus on UBC and COMPUTE tokens
   - Support ecosystem liquidity
   - Long-term value creation alongside short-term profits
   - Token discovery for emerging opportunities

## 4x Daily Trading Windows

KinKong operates on a structured 4x daily trading schedule to optimize execution during periods of maximum liquidity and price discovery:

### 1. Asian Session (00:00-04:00 UTC)
- **Focus:** Early trend identification, overnight developments
- **Strategies:** Breakout plays, news reaction
- **Volume Profile:** Moderate, building
- **Volatility:** Often lower, building momentum
- **Best For:** Setting up positions ahead of European session

### 2. European Session (08:00-12:00 UTC)
- **Focus:** Trend continuation, liquidity testing
- **Strategies:** Momentum following, support/resistance plays
- **Volume Profile:** Strong, consistent
- **Volatility:** Moderate to high
- **Best For:** High-probability trend trades

### 3. US Session (14:00-18:00 UTC)
- **Focus:** Maximum liquidity, major moves
- **Strategies:** All strategies, highest execution quality
- **Volume Profile:** Highest of the day
- **Volatility:** Typically highest
- **Best For:** Largest position entries, best execution

### 4. Crossover Session (20:00-00:00 UTC)
- **Focus:** Late US/Early Asia, position unwinding
- **Strategies:** Mean reversion, overnight positioning
- **Volume Profile:** Declining but still significant
- **Volatility:** Often declining but can spike on news
- **Best For:** Scaling out of intraday positions, setting up overnight trades

## Core Trading Strategies

### 1. Momentum Trading

**Signal Generation:**
- Price breakouts above key resistance levels
- Volume confirmation (>150% of 20-period average)
- RSI divergence confirmation
- MACD crossover validation

**Entry Criteria:**
- Price breaks above 20-period high
- Volume increases by >50%
- At least 2 technical confirmations
- Preferably during US or European trading windows

**Exit Criteria:**
- Take profit at predetermined levels (typically 1.5-3x risk)
- Stop loss at recent swing low or below key support
- Trailing stop after 1.5x risk achieved
- Consider partial exits at session boundaries

**Risk Management:**
- Position size: 1-3% of portfolio per trade
- Risk per trade: 0.5-1% maximum portfolio risk
- Scaling: Add to winning positions at key levels
- Adjust size based on trading window liquidity

### 2. Mean Reversion

**Signal Generation:**
- Oversold conditions (RSI <30)
- Price at key support levels
- Bullish divergence on oscillators
- Volume decline during selloff

**Entry Criteria:**
- Price tests support with RSI <30
- Candlestick reversal patterns
- Volume profile showing accumulation

**Exit Criteria:**
- Take profit at mean (typically 20-period moving average)
- Stop loss below recent swing low
- Time-based exit if no reversal within 3 periods

**Risk Management:**
- Position size: 1-2% of portfolio per trade
- Risk per trade: 0.5% maximum portfolio risk
- Scaling: Initial 60% position, add 40% on confirmation

### 3. Trend Following

**Signal Generation:**
- Price above/below key moving averages (50/200 EMA)
- ADX >25 indicating strong trend
- Higher highs and higher lows (uptrend)
- Lower highs and lower lows (downtrend)

**Entry Criteria:**
- Price pullback to dynamic support/resistance
- Bullish/bearish continuation patterns
- Volume confirmation on resumption

**Exit Criteria:**
- Trend exhaustion signals
- Break of key trend line
- Reversal candlestick patterns
- ADX falling below 20

**Risk Management:**
- Position size: 2-4% of portfolio per trade
- Risk per trade: 1% maximum portfolio risk
- Trailing stop: 2 ATR from recent swing high/low

### 4. Volatility Breakout

**Signal Generation:**
- Bollinger Band squeeze (narrowing bands)
- Low historical volatility (HV <30%)
- Decreasing volume before breakout
- Key level consolidation

**Entry Criteria:**
- Price breaks outside Bollinger Bands
- Volume surge (>200% of 10-period average)
- Breakout in direction of larger trend

**Exit Criteria:**
- Take profit at 1.5-2x the Bollinger Band width
- Stop loss at opposite Bollinger Band
- Partial profit at first target (50% position)

**Risk Management:**
- Position size: 1-2% of portfolio per trade
- Risk per trade: 0.75% maximum portfolio risk
- No adding to position after initial entry

## Token-Specific Adjustments

### UBC Trading Parameters

- **Volatility Factor:** 1.2x (20% more volatile than baseline)
- **Position Sizing:** 0.8x standard size (reduced due to higher volatility)
- **Stop Placement:** 1.2x standard distance (wider due to volatility)
- **Take Profit Levels:** 1.5x, 2.5x, 3.5x risk (aggressive targets)
- **Key Technical Levels:** Updated weekly based on market structure

### COMPUTE Trading Parameters

- **Volatility Factor:** 1.4x (40% more volatile than baseline)
- **Position Sizing:** 0.7x standard size (reduced due to higher volatility)
- **Stop Placement:** 1.3x standard distance (wider due to volatility)
- **Take Profit Levels:** 1.5x, 3x, 5x risk (very aggressive targets)
- **Key Technical Levels:** Updated daily based on market structure

## Token Discovery Strategy

KinKong employs a systematic approach to discover emerging Solana AI tokens with high potential:

### Discovery Criteria
- **Ecosystem Relevance:** Connection to AI/ML infrastructure
- **Team Background:** Developer experience and track record
- **Tokenomics:** Supply distribution, emission schedule, utility
- **Liquidity:** Minimum viable trading volume
- **Community:** Engagement metrics and growth rate
- **Technical Innovation:** Unique technology or use case

### Evaluation Process
1. **Initial Screening:** Filter tokens meeting basic criteria
2. **Fundamental Analysis:** Evaluate team, technology, and tokenomics
3. **Technical Analysis:** Assess market structure and liquidity
4. **Risk Assessment:** Evaluate potential downside and volatility
5. **Opportunity Sizing:** Determine appropriate allocation

### Integration Timeline
1. **Monitoring Phase:** Track token without position (1-2 weeks)
2. **Pilot Position:** Small allocation to test liquidity (0.5% portfolio)
3. **Evaluation Phase:** Assess trading characteristics (1-2 weeks)
4. **Full Integration:** Add to regular trading rotation if criteria met

## Performance Metrics

KinKong's trading performance is measured by:

1. **Absolute Return**
   - Weekly profit percentage
   - Monthly compounded return
   - Quarterly performance review
   - Trading window performance breakdown

2. **Risk-Adjusted Metrics**
   - Sharpe Ratio (target >2.0)
   - Maximum Drawdown (target <15%)
   - Win/Loss Ratio (target >1.5)
   - Profit Factor (target >2.0)
   - Calmar Ratio (target >3.0)

3. **Operational Efficiency**
   - Execution slippage (<0.2%)
   - Trading costs (<0.5% per round trip)
   - Strategy correlation (<0.3 between strategies)
   - Trading window capture rate (>80%)

## Profit Distribution

- 75% of trading profits distributed to Pro investors weekly
- 50% of trading profits distributed to Standard investors weekly
- Profits distributed in the same token as invested (UBC→UBC, COMPUTE→COMPUTE)
- Distributions processed every Friday
- Performance fee: 25% for Pro accounts, 50% for Standard accounts

## Risk Management Framework

### Portfolio-Level Controls

- Maximum allocation to single strategy: 30%
- Maximum correlation between strategies: 0.3
- Minimum cash reserve: 15% of portfolio
- Maximum drawdown trigger: 15% (reduce position sizes by 50%)
- Emergency stop: 25% drawdown (cease trading, review strategies)

### Trade-Level Controls

- Pre-trade checklist verification
- Multiple confirmation requirement
- Scaling in/out methodology
- Automated stop-loss enforcement
- Maximum open risk exposure limit

## Continuous Improvement

KinKong's trading strategies undergo:

1. **Daily Optimization**
   - Parameter tuning based on recent performance
   - Volatility adjustment for position sizing

2. **Weekly Review**
   - Strategy performance evaluation
   - Market regime assessment
   - Correlation analysis

3. **Monthly Deep Learning**
   - Pattern recognition enhancement
   - New strategy testing
   - Historical performance analysis

4. **Quarterly Framework Update**
   - Major strategy revisions
   - Risk management review
   - Performance attribution analysis
