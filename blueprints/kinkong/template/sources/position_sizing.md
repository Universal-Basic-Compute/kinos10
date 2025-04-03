# KinKong Position Sizing Methodology

This document outlines KinKong's dynamic trade sizing methodology, which ensures optimal risk management across different market conditions.

## Core Position Sizing Formula

KinKong uses a sophisticated position sizing algorithm that accounts for multiple factors:

```
Position Size = (Account Risk % × Account Value) ÷ Trade Risk
```

Where:
- **Account Risk %** = Base risk % × Market condition multiplier × Strategy confidence multiplier
- **Trade Risk** = Entry price - Stop loss price (for long positions) or Stop loss price - Entry price (for short positions)

## Dynamic Risk Adjustment Factors

### 1. Market Condition Multiplier

Based on the Composite Sentiment Index (CSI) from the Market Sentiment Analysis:

| Market Condition | CSI Range | Multiplier |
|------------------|-----------|------------|
| Strongly Bullish | 75-100    | 1.2        |
| Bullish          | 60-75     | 1.0        |
| Neutral          | 45-60     | 0.8        |
| Bearish          | 30-45     | 0.6        |
| Strongly Bearish | 0-30      | 0.4        |

### 2. Strategy Confidence Multiplier

Based on the number of confirming signals and historical strategy performance:

| Confidence Level | Criteria                                      | Multiplier |
|------------------|-----------------------------------------------|------------|
| Very High        | 4+ confirmations, >65% win rate               | 1.25       |
| High             | 3 confirmations, >60% win rate                | 1.0        |
| Medium           | 2 confirmations, >55% win rate                | 0.75       |
| Low              | 1 confirmation, <55% win rate                 | 0.5        |
| Very Low         | Conflicting signals, <50% win rate            | 0.25       |

### 3. Volatility Adjustment

Position size is further adjusted based on current vs. historical volatility:

```
Volatility Adjustment = √(Historical ATR ÷ Current ATR)
```

This reduces position size during high volatility and increases it during low volatility periods.

## Position Sizing Examples

### Example 1: Standard Bullish Condition
- Account Value: 100,000 UBC
- Base Risk Percentage: 1%
- Market Condition: Bullish (Multiplier = 1.0)
- Strategy Confidence: High (Multiplier = 1.0)
- Entry Price: 1.00 SOL
- Stop Loss Price: 0.95 SOL
- Trade Risk: 0.05 SOL (5%)

```
Account Risk % = 1% × 1.0 × 1.0 = 1%
Position Size = (1% × 100,000 UBC) ÷ 5% = 20,000 UBC
```

### Example 2: High Confidence in Bearish Market
- Account Value: 100,000 UBC
- Base Risk Percentage: 1%
- Market Condition: Bearish (Multiplier = 0.6)
- Strategy Confidence: Very High (Multiplier = 1.25)
- Entry Price: 0.90 SOL
- Stop Loss Price: 0.945 SOL
- Trade Risk: 0.045 SOL (5%)

```
Account Risk % = 1% × 0.6 × 1.25 = 0.75%
Position Size = (0.75% × 100,000 UBC) ÷ 5% = 15,000 UBC
```

### Example 3: Low Confidence in Volatile Market
- Account Value: 100,000 UBC
- Base Risk Percentage: 1%
- Market Condition: Neutral (Multiplier = 0.8)
- Strategy Confidence: Low (Multiplier = 0.5)
- Historical ATR: 0.05 SOL
- Current ATR: 0.10 SOL (2x normal volatility)
- Entry Price: 1.10 SOL
- Stop Loss Price: 1.00 SOL
- Trade Risk: 0.10 SOL (9.09%)

```
Account Risk % = 1% × 0.8 × 0.5 = 0.4%
Volatility Adjustment = √(0.05 ÷ 0.10) = 0.707
Position Size = (0.4% × 100,000 UBC) ÷ 9.09% × 0.707 = 3,110 UBC
```

## Maximum Position Limits

To prevent overexposure to any single position, KinKong enforces maximum position limits:

1. **Single Position Limit:** No more than 5% of portfolio in any single trade
2. **Correlated Positions Limit:** No more than 15% in highly correlated assets
3. **Strategy Limit:** No more than 20% in any single strategy
4. **Sector Limit:** No more than 40% in any token sector

## Position Scaling Rules

KinKong uses a systematic approach to scaling in and out of positions:

### Scaling In
- Initial position: 40-60% of calculated position size
- Second entry: 20-30% on confirmation of trend
- Final entry: 10-20% on pullback to support/resistance

### Scaling Out
- First target: Exit 30-40% at 1:1 risk/reward
- Second target: Exit 30-40% at 2:1 risk/reward
- Final target: Exit remaining position at 3:1 risk/reward or trailing stop

## Trading Window Adjustments

Position sizes are further adjusted based on the 4x daily trading windows:

| Trading Window          | Liquidity | Adjustment |
|-------------------------|-----------|------------|
| US Session              | Highest   | 100%       |
| European Session        | High      | 90%        |
| Asian Session           | Moderate  | 80%        |
| Crossover Session       | Variable  | 70%        |

This comprehensive position sizing methodology ensures that KinKong maintains appropriate risk levels across all market conditions while maximizing return potential.
